# config.py
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DEFAULT_GAME_ID = "13"
DEFAULT_OUTPUT_FOLDER = r"D:\Documents\threadpuller\outputfolder\Catan"
DEFAULT_CREDENTIALS_PATH = os.getenv("CREDENTIALS_PATH", "credentials.json")
