# sitaara-assignment

Part B: Engineering Status Automation
An automated Python pipeline that pulls active tickets from Linear via GraphQL, correlates them with Pull Requests from GitHub via REST, checks for operational discrepancies and workflow bottlenecks, and atomically writes the data to a Google Sheet.

---
## 1. Prerequisites
* Python 3.10+
* Google Cloud Platform Service Account with Google Sheets API access
* Linear API Personal Access Token
* GitHub Personal Access Token (`repo` read permissions)

---

## 2. Local Installation & Configuration

1. **Navigate to the automation folder:**
   ```bash
   cd part-b-automation

2. **Set up a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt

4. **Set up Environment Variables:**  
   Create a `.env` file inside `part-b-automation/` with:
   ```env
   LINEAR_API_KEY=your_linear_api_key
   GITHUB_TOKEN=your_github_personal_access_token
   GITHUB_OWNER=your_github_username_or_org
   GITHUB_REPO=your_repository_name
   GOOGLE_SHEET_NAME=Sitaara Status
   GOOGLE_CREDENTIALS_FILE=credentials.json
5. **Configure Google Service Account:**  
   Place your GCP service account JSON key at `part-b-automation/credentials.json`. Ensure your target Google Sheet is shared with the `client_email` specified inside that JSON file with **Editor** permissions.

##  Execution

### Local Sync
Run the pipeline manually from your terminal:
```bash
python sync.py

Automated CI/CD (GitHub Actions)
The workflow defined in .github/workflows/sync.yml provides:

Scheduled Runs: Runs daily at 04:30 UTC (10:00 AM IST).

On-Demand Dispatch: Run manually at any time via GitHub UI ➔ Actions ➔ Engineering Status Sync ➔ Run workflow.

#Automated Testing
Execute the test suite using pytest to validate regex ticket parsing, boundary cases, and discrepancy hierarchy:

Bash
pytest

# In-Depth Architectural Write-Up
For a comprehensive evaluation of architectural options considered, priority rules matrix, debugging pivot points, and AI collaboration verification, review WRITEUP.md.