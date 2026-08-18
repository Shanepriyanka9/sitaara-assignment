import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Sitaara Engineering Status")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
client = gspread.authorize(creds)

sheet = client.open(SPREADSHEET_NAME).sheet1
print(f"Connected successfully to Google Sheet: '{sheet.title}'")