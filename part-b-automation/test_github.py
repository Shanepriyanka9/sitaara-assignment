import os
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OWNER = os.getenv("GITHUB_OWNER")
REPO = os.getenv("GITHUB_REPO")

url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls"

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

params = {
    "state": "all",
    "per_page": 100
}

response = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=30
)

response.raise_for_status()
pull_requests = response.json()

for pr in pull_requests:
    print(
        f"#{pr['number']} | "
        f"{pr['title']} | "
        f"{pr['state']} | "
        f"merged={pr['merged_at'] is not None}"
    )