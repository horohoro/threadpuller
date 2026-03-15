import os
import glob
import html
import shutil
from lxml import etree
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

import argparse
from config import DEFAULT_OUTPUT_FOLDER, DEFAULT_CREDENTIALS_PATH

parser = argparse.ArgumentParser()
parser.add_argument("--input_folder", default=DEFAULT_OUTPUT_FOLDER)
parser.add_argument("--credentials_path", default=DEFAULT_CREDENTIALS_PATH)
parser.add_argument("--game_id", default=None, help="If provided, input_folder is treated as a base folder and the script will search for a subfolder ending with ({game_id})")
args, _ = parser.parse_known_args()

# Folder containing the XML files to upload. Its foldername is used for the title of the Google Docs.
INPUT_FOLDER = args.input_folder

if args.game_id:
    base_folder = args.input_folder
    found_folder = None
    if os.path.exists(base_folder):
        for entry in os.listdir(base_folder):
            full_path = os.path.join(base_folder, entry)
            if os.path.isdir(full_path) and entry.endswith(f"({args.game_id})"):
                found_folder = full_path
                break
    if found_folder:
        INPUT_FOLDER = found_folder
    else:
        print(f"Error: Could not find a folder for game ID {args.game_id} in {base_folder}")
        exit(1)

CREDENTIALS_PATH = args.credentials_path
MAX_CHARS_PER_DOC = 900_000  # Google Docs limit is 1.02M characters

def get_drive_service():
    """Authenticates the user and returns the Google Drive service."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)

def upload_html_to_gdocs(drive_service, html_filename, doc_title):
    """Uploads an HTML file to Google Drive and converts it into a Google Doc."""
    print(f"Uploading '{html_filename}' to Google Docs as '{doc_title}'...")
    file_metadata = {
        'name': doc_title,
        'mimeType': 'application/vnd.google-apps.document' # Triggers the HTML -> GDoc conversion
    }
    media = MediaFileUpload(html_filename, mimetype='text/html', resumable=True)
    
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"Success! Document ID: {file.get('id')}")
    return file.get('id')

def unescape_body_html(xml_body):
    """Unescapes the BGG saved HTML (e.g. &lt;b&gt; becomes <b>)."""
    if not xml_body:
        return ""
    # BGG body nodes contain HTML entities for actual formatting tags.
    # We decode them here so that when uploaded as text/html, Google Docs parses them.
    return html.unescape(xml_body)

def process_xml_files():
    folder_name = os.path.basename(os.path.normpath(INPUT_FOLDER))
    if args.game_id and folder_name.endswith(f"({args.game_id})"):
        folder_name = folder_name[:-len(f"({args.game_id})")].strip()
    if not folder_name:
        folder_name = "BGG Threads"

    xml_files = glob.glob(os.path.join(INPUT_FOLDER, "*.xml"))
    if not xml_files:
        print(f"No XML files found in {INPUT_FOLDER}")
        return

    print(f"Found {len(xml_files)} XML files. Processing...")
    
    current_doc_index = 1
    current_html_content = []
    current_char_count = 0
    
    temp_folder = "temp_htmls"
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)
        
    html_files_to_upload = []

    def save_and_queue_html():
        nonlocal current_doc_index, current_html_content, current_char_count
        if not current_html_content:
            return
            
        final_html = "<html><body>\n" + "\n".join(current_html_content) + "\n</body></html>"
        temp_file = os.path.join(temp_folder, f"upload_part_{current_doc_index}.html")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(final_html)
            
        html_files_to_upload.append((temp_file, f"{folder_name} BGG Threads - Part {current_doc_index}"))
        
        current_doc_index += 1
        current_html_content = []
        current_char_count = 0

    for xml_file in xml_files:
        try:
            tree = etree.parse(xml_file)
            root = tree.getroot()
        except Exception as e:
            print(f"Failed to parse {xml_file}: {e}")
            continue
            
        # Extract thread subject
        subject_nodes = root.xpath('/thread/subject')
        subject = subject_nodes[0].text if subject_nodes and subject_nodes[0].text else "Unknown Subject"
        
        thread_html = []
        # Insert a page break before the new thread (unless it's the very first item in the document)
        if current_html_content:
            thread_html.append('<hr class="pb" style="page-break-after:always;display:none;"/>')
        thread_html.append(f"<h1>{html.escape(subject)}</h1>")
        thread_html.append("<hr>")
        
        # Extract articles
        articles = root.xpath('.//article')
        for article in articles:
            username = article.get('username', 'Unknown')
            postdate = article.get('postdate', '')
            editdate = article.get('editdate', '')
            date_str = editdate if editdate else postdate
            
            body_node = article.find('body')
            body_text = body_node.text if body_node is not None and body_node.text else ""
            clean_body = unescape_body_html(body_text)
            
            # Format the article header imitating a chat style
            article_html = f"<p><b>{html.escape(username)}</b> <i>({html.escape(date_str)})</i>:</p>"
            article_html += f"<div>{clean_body}</div><br/>"
            
            thread_html.append(article_html)
            
        thread_str = "\n".join(thread_html)
        thread_len = len(thread_str)
        
        # If adding this thread exceeds our safe limit, save the current HTML file and start a new one
        if current_char_count + thread_len > MAX_CHARS_PER_DOC and current_char_count > 0:
            save_and_queue_html()
            # Since we are starting a new document, we don't need a page break on the very first item
            if thread_html[0].startswith('<hr class="pb"'):
                thread_html.pop(0)
            thread_str = "\n".join(thread_html)
            thread_len = len(thread_str)
            
        current_html_content.append(thread_str)
        current_char_count += thread_len
        try:
            print(f"Processed: {subject} ({len(articles)} posts)")
        except UnicodeEncodeError:
            print(f"Processed: {subject.encode('ascii', 'replace').decode('ascii')} ({len(articles)} posts)")
        
    # Save the remaining content
    if current_html_content:
        save_and_queue_html()
        
    print(f"\nCreated {len(html_files_to_upload)} payload files. Initiating upload...")
    
    # Authenticate and upload
    try:
        drive_service = get_drive_service()
        for temp_file, doc_title in html_files_to_upload:
            upload_html_to_gdocs(drive_service, temp_file, doc_title)
        print("\nAll uploads complete!")
        
        # Cleanup temp HTML files after successful upload
        print(f"Cleaning up temporary directory '{temp_folder}'...")
        shutil.rmtree(temp_folder)
        print("Cleanup complete.")
        
    except Exception as e:
        print(f"\nError during upload segment: {e}")

if __name__ == '__main__':
    if not os.path.exists(CREDENTIALS_PATH):
        print("="*60)
        print(f"ERROR: '{CREDENTIALS_PATH}' not found in the specified path.")
        print("To use the Google Docs/Drive API, you must:")
        print("1. Go to Google Cloud Console (https://console.cloud.google.com/)")
        print("2. Create a Project and enable the 'Google Drive API' and 'Google Docs API'.")
        print("3. Create Credentials -> OAuth client ID -> Desktop app.")
        print("4. Download the JSON file and securely store it.")
        print("5. Provide the correct path via GUI, .env, or --credentials_path.")
        print("="*60)
        exit(1)
        
    process_xml_files()
