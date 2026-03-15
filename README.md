# ThreadPuller & GDocs Uploader

A comprehensive set of tools for downloading BoardGameGeek (BGG) rules threads and automatically converting these discussion logs into formatted Google Documents. This makes it easier to feed them into a LLM model like NotebookLM.

## Included Components
This project contains three main applications, supported by configuration and requirement files:
1. `download_threads.py`: A CLI Python script that fetches and saves all discussion topics from a specific game's BGG "Rules" forum as XML files securely to your local machine.
2. `upload_to_gdocs.py`: A CLI Python script that parses the saved XML threads, converts them automatically into structured, readable HTML with properly formatted chat logs, and uploads them as new Google Docs to your Google Drive. 
3. `app.py`: A user-friendly desktop Graphic User Interface (GUI) wrapper that allows you to easily run the Download and Upload operations without needing to touch the command line.

## Prerequisites & Installation

### 1. Python & Dependencies
Ensure you have Python 3.x installed on your computer. Install all necessary dependencies by running:
```bash
pip install -r requirements.txt
```

### 2. BoardGameGeek API Setup (for Downloading)
To download threads from BGG, you need a Bearer Token.
1. Create a file named `.env` in the root of the project directory.
2. Add your token inside the file:
   ```env
   BGG_BEARER_TOKEN=your_bgg_api_token_here
   CREDENTIALS_PATH=credentials.json
   ```

### 3. Google Docs API Setup (for Uploading)
To upload directly to Google Drive/Docs, you must configure OAuth Desktop application credentials.
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a Project and enable both the **Google Drive API** and **Google Docs API**.
3. Go to **Credentials -> Create Credentials -> OAuth client ID -> Desktop app**.
4. Download the generated `.json` file and securely store it. By default, the scripts look for `credentials.json` in the project root folder, but you can configure this path dynamically.
*(Note: When you run the upload script for the very first time, it will open your web browser to authenticate your Google Account and generate a local `token.json` file for future uses).*

---

## 1. Using the GUI Desktop App (`app.py`)
The easiest way to use these tools is through the graphical interface.

**Running the app:**
```bash
python app.py
```

**How to use:**
- **GAME_ID**: Input the BGG target game ID (e.g., `13` for Catan) found in its main URL.
- **Folder**: Use the `Browse` button to select a local output/input directory.
- **Credentials**: Use the `Browse` button to select your Google OAuth `credentials.json` file.
- **DOWNLOAD**: Triggers `download_threads.py` using your selected ID and folder.
- **UPLOAD**: Triggers `upload_to_gdocs.py` using your selected folder & credentials.
- The logs and progress are seamlessly printed to the application output window at the bottom.

---

## 2. Using the Command Line Scripts

You can bypass the GUI and use the raw scripts directly. Both scripts can utilize default properties configured inside `config.py`:
```python
# config.py
DEFAULT_GAME_ID = "13" 
DEFAULT_OUTPUT_FOLDER = r"D:\path\to\your\output_folder"
```

### downloading threads: `download_threads.py`
This script uses "smart syncing"—checking local files against the remote server so it only downloads threads with new or updated numbers of posts. It automatically respects API rate limitations.

**Run with configured defaults:**
```bash
python download_threads.py
```

**Run with CLI overrides:**
```bash
python download_threads.py --game_id 174430 --output_folder ./gloomhaven_rules
```

### Uploading threads: `upload_to_gdocs.py`
This script takes a folder of BGG XML discussions and stitches them into an extensive HTML structured stream with subjects and chat logs. If a compiled document exceeds the Google Docs character limit (approx 1M characters), the script will automatically split it into consecutive "Part X" documents to avoid API upload failures.

**Run with configured default input folder:**
```bash
python upload_to_gdocs.py
```

**Run with CLI override:**
```bash
python upload_to_gdocs.py --input_folder ./gloomhaven_rules --credentials_path ./my_creds.json
```
