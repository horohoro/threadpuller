import requests
import time
import os
from lxml import etree
from dotenv import load_dotenv

import argparse
from config import DEFAULT_GAME_ID, DEFAULT_OUTPUT_FOLDER

load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--output_folder", default=DEFAULT_OUTPUT_FOLDER)
parser.add_argument("--game_id", default=DEFAULT_GAME_ID)
parser.add_argument("--auto_folder", action="store_true", help="Generate output folder based on game name")
args, _ = parser.parse_known_args()

# --- Configuration ---
GAME_ID = args.game_id

import re

BEARER_TOKEN = os.environ.get("BGG_BEARER_TOKEN")
if not BEARER_TOKEN:
    print("Error: BGG_BEARER_TOKEN environment variable is not set. Please set it in a .env file.")
    exit(1)
BASE_URL = "https://boardgamegeek.com/xmlapi2"

headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}"
}


def fetch_game_name(game_id):
    url = f"{BASE_URL}/thing?id={game_id}&type=boardgame"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        root = etree.fromstring(response.content)
        name_nodes = root.xpath('//name[@type="primary"]/@value')
        if name_nodes:
            return name_nodes[0]
        raise ValueError(f"Could not find game name for ID {game_id}.")
    raise ValueError(f"Could not fetch game name for ID {game_id}.")

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '', filename).strip()

if args.auto_folder:
    game_name = fetch_game_name(GAME_ID)
    sanitized_name = sanitize_filename(game_name)
    folder_name = f"{sanitized_name} ({GAME_ID})"
    OUTPUT_FOLDER = os.path.join(args.output_folder, folder_name)
else:
    OUTPUT_FOLDER = args.output_folder

print(f"Output folder: {OUTPUT_FOLDER}")

# Ensure output directory exists
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

def fetch_rules_forum_details(game_id):
    """Finds the 'Rules' forum ID and expected thread count."""
    url = f"{BASE_URL}/forumlist?id={game_id}&type=thing"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        root = etree.fromstring(response.content)
        # XPath to find the forum with title "Rules"
        forum_node = root.xpath('//forum[@title="Rules"]')
        
        if forum_node:
            f_id = forum_node[0].get('id')
            num_threads = int(forum_node[0].get('numthreads'))
            print(f"Found 'Rules' Forum (ID: {f_id}) with {num_threads} threads.")
            return f_id, num_threads
    
    print("Could not find a 'Rules' forum for this ID.")
    return None, 0

def collect_threads_with_counts(forum_id, target_count):
    """Returns a dictionary: {thread_id: num_articles}"""
    thread_data = {}
    page = 1
    while len(thread_data) < target_count:
        print(f"Scanning forum page {page}...")
        url = f"{BASE_URL}/forum?id={forum_id}&page={page}"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Could not get page {page}.")
            break
            
        root = etree.fromstring(response.content)
        threads = root.xpath('//thread')
        if not threads: 
            print(f"Ended suddenly with {len(thread_data)} threads.")
            break
            
        for t in threads:
            t_id = t.get('id')
            t_articles = int(t.get('numarticles'))
            thread_data[t_id] = t_articles
            
        page += 1
    return thread_data

def get_local_article_count(file_path):
    """Reads an existing XML file to find its reported article count."""
    try:
        tree = etree.parse(file_path)
        # BGG thread XML stores count in the root <thread> attribute
        count = tree.xpath('/thread/@numarticles')
        return int(count[0]) if count else 0
    except Exception:
        return -1 # File is corrupt or unreadable

def download_threads(thread_map):
    for t_id, remote_count in thread_map.items():
        file_path = os.path.join(OUTPUT_FOLDER, f"{t_id}.xml")
        
        # Check if we should skip
        if os.path.exists(file_path):
            local_count = get_local_article_count(file_path)
            # Warning: Only checks if count is same. If there are edits with the same number of posts, they will be ignored.
            if local_count == remote_count:
                print(f"Skipping Thread {t_id} (Already up to date: {local_count} posts)")
                continue
            else:
                print(f"Updating Thread {t_id} (Local: {local_count}, Remote: {remote_count})")
        else:
            print(f"Downloading new Thread {t_id}...")

        # Perform the download
        url = f"{BASE_URL}/thread?id={t_id}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(response.content)
            time.sleep(2) # Respect BGG rate limits
        else:
            print(f"Failed to fetch {t_id}: Status {response.status_code}")

def main():
    f_id, total_expected = fetch_rules_forum_details(GAME_ID)
    if f_id:
        print(f"Rules Forum ID: {f_id} | Total Threads: {total_expected}")
        thread_map = collect_threads_with_counts(f_id, total_expected)
        download_threads(thread_map)
        print("\nSync complete.")

if __name__ == "__main__":
    main()