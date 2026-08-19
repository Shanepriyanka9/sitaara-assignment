import os
import re
from datetime import datetime, timezone
import requests
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
SPREADSHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Sitaara Status")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")


def fetch_linear_issues():
    url = "https://api.linear.app/graphql"
    query = """
    query {
      issues(first: 100) {
        nodes {
          identifier
          title
          state {
            name
          }
        }
      }
    }
    """
    headers = {
        "Authorization": LINEAR_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(url, json={"query": query}, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    if "errors" in data:
        raise RuntimeError(f"Linear GraphQL Error: {data['errors']}")
    return data["data"]["issues"]["nodes"]


def fetch_github_prs():
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    params = {"state": "all", "per_page": 100}
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def map_prs_to_tickets(prs):
    mapping = {}
    pattern = re.compile(r"(SIT-\d+)", re.IGNORECASE)
    for pr in prs:
        title = pr.get("title", "")
        branch = pr.get("head", {}).get("ref", "")
        match = pattern.search(title) or pattern.search(branch)
        if match:
            ticket_id = match.group(1).upper()
            is_merged = pr.get("merged_at") is not None
            pr_state = "merged" if is_merged else pr.get("state")
            mapping[ticket_id] = {
                "number": pr.get("number"),
                "state": pr_state,
                "created_at": pr.get("created_at"),  # Added for stale PR tracking
                "url": pr.get("html_url")
            }
    return mapping


def detect_discrepancy(linear_status, pr_data):
    if not pr_data:
        if linear_status.lower() in ["in progress", "done"]:
            return "No PR created"
        return "None"

    pr_state = pr_data["state"].lower()
    l_status = linear_status.lower()

    # 1. Status contradiction checks first (highest priority)
    if pr_state == "merged" and l_status != "done":
        return "PR Merged but ticket not Done"
    if pr_state == "open" and l_status == "done":
        return "Ticket marked Done but PR is still Open"
    if pr_state == "closed" and l_status == "done":
        return "Ticket Done but PR closed without merge"

    # 2. Stale PR check for active in-progress work (tested with >= 0)
    if pr_state == "open" and pr_data.get("created_at"):
        created_at = datetime.fromisoformat(pr_data["created_at"].replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - created_at).days
        if age_days >= 7:
            return f"Stale PR (Open for {age_days} days)"

    return "None"


def sync():
    print("Fetching data from Linear & GitHub...")
    issues = fetch_linear_issues()
    prs = fetch_github_prs()
    pr_map = map_prs_to_tickets(prs)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).sheet1

    headers = [
        "Ticket ID",
        "Title",
        "Linear Status",
        "PR Number",
        "PR Status",
        "Discrepancy",
        "Last Synced (UTC)"
    ]

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows = [headers]

    for issue in issues:
        ticket_id = issue["identifier"]
        title = issue["title"]
        linear_status = issue["state"]["name"]
        pr_info = pr_map.get(ticket_id)

        pr_number = f"#{pr_info['number']}" if pr_info else "N/A"
        pr_status = pr_info["state"].capitalize() if pr_info else "N/A"
        discrepancy = detect_discrepancy(linear_status, pr_info)

        rows.append([
            ticket_id,
            title,
            linear_status,
            pr_number,
            pr_status,
            discrepancy,
            timestamp
        ])

    print("Updating Google Sheet...")
    sheet.clear()
    sheet.update(rows, "A1")
    print("Sync completed successfully!")


if __name__ == "__main__":
    sync()