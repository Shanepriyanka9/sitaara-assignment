# Part A: Video & Subtitle Automated QC Skill

### 1. The Options I Considered & Trade-offs

* **Option 1: Cloud Transcription API (e.g., OpenAI Whisper API, Deepgram)**
  * *Trade-off:* Fast and requires minimal local compute setup, but introduces external dependencies, recurring costs, and cloud API keys.
  * *Why I rejected it:* If an evaluator or AI agent runs this tool without active network credentials, it immediately fails. It violates the strict zero-setup portability requirement.

* **Option 2: Basic Whole-File String / Levenshtein Comparison**
  * *Trade-off:* Simple to implement without ML models, but completely ignores speech timing and timecode structure.
  * *Why I rejected it:* It cannot verify whether spoken words match at the correct timestamps. Additionally, whole-file comparisons mask missing or completely incorrect subtitle blocks in longer videos.

* **Option 3: Local `faster-whisper` (int8) with Word-Midpoint Alignment (Selected)**
  * *Trade-off:* Requires a local `ffmpeg` binary and an initial model cache (~75MB for `base`), but runs entirely offline on standard CPU hardware with zero API keys.
  * *Why I chose it:* It provides precise, word-level timestamps to verify audio-to-subtitle timeline synchronization while keeping the skill 100% portable, self-contained, and free to run.

---

### 2. How I Worked: Progression, Stuck Points & AI Collaboration

* **What I did first:** I built a baseline pipeline that paired `.mp4` video files with `.srt` subtitle files, validated container integrity using `ffprobe`, transcribed audio locally with `faster-whisper`, and output initial Markdown and JSON reports.
* **Where I got stuck & what I changed:**
  * *Word-Bleed False Positives:* When implementing segment-level checks, words spanning subtitle boundaries caused false-positive mismatches. I resolved this by implementing a **word-midpoint assignment rule** (`(start + end) / 2`), which cleanly anchors each word to a single subtitle cue.
  * *Multi-Format Container Support:*The initial script only scanned for lowercase .mp4 files. Real-world testing with iPhone recordings (.MOV) and editor deliverables highlighted that uppercase extensions (.MOV, .MP4) and alternate video containers (.mov, .mkv, .webm) were being skipped or failing. I updated the ingestion pipeline to case-insensitively match all major video containers (f.suffix.lower() in SUPPORTED_EXTS)
* **AI vs. Human Contribution:**
  * *AI-generated:* Initial boilerplate subprocess wrappers, regex text normalization functions, and Markdown table string formatting.
  * *My decisions & logic:* Designing the 3-state exit criteria (`PASS`, `FAIL`, `NEEDS_REVIEW`), selecting the word-midpoint alignment rule, tuning the WER pass/fail thresholds (35% segment / 20% global), and structuring the failure checks.
  * *How I verified the AI’s output:* I created a dedicated negative test suite in `samples/` with distinct failure fixtures (`good.mp4`, `empty_subtitle`, `no_audio`, `wrong_text`, `wrong_timing`, `video3`). I verified that every single fixture triggered its intended defect code and failure mode in `report.md` and `report.json`.

---

### 3. What I Would Do Next (With Another Week)

* **Audio Loudness Verification (LUFS):** Add an EBU R128 loudness check via `ffmpeg` to ensure video audio adheres to platform delivery standards (-14 LUFS).
* **Automated Subtitle Re-Timing (`--fix`):** Build an auto-remediation flag that uses Whisper's word-level timestamps to automatically shift and correct drifted `.srt` cue times.

---

# Part B: Engineering Status & Operations Automation Write-Up

## 1. Overview & Architecture

### The Problem
Project status is fragmented across two disparate tools: task lifecycles live in Linear, while technical progress lives in GitHub Pull Requests. Stakeholders who need visibility into shipping status do not navigate either platform. Manual reporting in spreadsheets degrades rapidly into stale, untrustworthy data.

### The Solution
A resilient, automated Python pipeline (`sync.py`) running on GitHub Actions that queries Linear (GraphQL) and GitHub (REST) APIs, maps pull requests to tickets, identifies workflow bottlenecks and status contradictions, and writes an idempotent, clean dashboard to a shared Google Sheet via `gspread`.

---

## 2. Options Considered & Architectural Trade-offs

To achieve an unattended, self-healing sync pipeline that works even when laptops are closed, three architectures were evaluated:

| Architecture Considered | Pros | Cons | Final Decision |
| :--- | :--- | :--- | :--- |
| **Option A: Webhook Server (AWS Lambda / Cloudflare Workers + Fastify)** | Instant real-time updates on every Linear/GitHub state change. | Requires public endpoint exposure, secrets management across cloud vendors, signature verification overhead, and cold-start state handling. | Rejected for assignment scope due to unnecessary operational complexity. |
| **Option B: Local Long-Running Daemon (Systemd / Cron on local machine)** | Simple setup, instant execution, zero cloud configuration. | Hard failure when laptop is closed or asleep; violates the core unattended execution requirement. | Rejected. |
| **Option C: Scheduled GitHub Actions Runner (`cron` + `workflow_dispatch`)** | Zero infrastructure maintenance, native access to repository secrets, completely decoupled from local machines, free tier support, and easy manual testing via UI. | Cron triggers may have minor queue delays (5–15 mins) during peak GitHub compute hours. | **Selected & Implemented.** |

### Data Storage & Output Layer Options
* **Direct Google Sheets API (via `gspread` service account):** Selected. Provides non-technical stakeholders with a familiar, accessible live view requiring no specialized software or logins.
* **Slack Bot / Email Digest:** Considered as an add-on, but secondary to the core mandate of creating a persistent single source of truth accessible to executives and PMs.

---

## 3. Discrepancy Detection & Priority Ordering Logic

A key requirement was doing more than simply mirroring raw fields. The script surfaces operational anomalies and human errors.

### Priority Rules Matrix
Because multiple rules can trigger on a single ticket, `detect_discrepancy()` enforces strict precedence: **process contradictions take priority over time-based stale warnings.**

| Linear Status | GitHub PR State | PR Age | Flagged Discrepancy | Operational Rationale |
| :--- | :--- | :--- | :--- | :--- |
| `Done` | `Merged` | Any | `None` | Healthy lifecycle completion. |
| `In Progress` | `Open` | < 7 days | `None` | Active feature development. |
| `In Progress` / `Done` | *None* | N/A | `No PR created` | Work progressing or marked complete without code review linkage. |
| `In Progress` | `Merged` | Any | `PR Merged but ticket not Done` | Code deployed/merged, but engineer forgot to update Linear. |
| `Done` | `Open` | Any | `Ticket marked Done but PR is still Open` | Premature ticket closure before code review/merge completion. |
| `Done` | `Closed` (Unmerged) | Any | `Ticket Done but PR closed without merge` | Ticket closed despite pull request abandonment. |
| `In Progress` | `Open` | >= 7 days | `Stale PR (Open for X days)` | Bottleneck detection for PRs lingering in review. |

### Handling Idempotency & Overwriting
Running the sync repeatedly must never duplicate rows or create messy logs. The pipeline uses an atomic batch-overwrite strategy:
1. Re-fetches the current state across Linear and GitHub.
2. Formats headers, discrepancies, and UTC timestamps into memory.
3. Invokes `sheet.clear()` followed by `sheet.update(rows, "A1")` to replace the view in a single API call.

---

## 4. How I Worked & Step-by-Step Evolution

1. **Initial Setup:** Configured a dedicated Linear workspace (`SIT` team identifier) and populated 6 distinct test tickets (`SIT-5` through `SIT-10`) simulating various project states. Created a GitHub repository with corresponding branches and Pull Requests.
2. **Local Prototyping:** Built `sync.py` using `requests` for Linear GraphQL and GitHub REST APIs, and `gspread` for Google Sheets authentication using a GCP Service Account.
3. **Where I Got Stuck & Pivot Points:**
   * **Rule Collision on SIT-10:** Initially, when testing the stale PR rule, `SIT-10` (Done in Linear, Open in GitHub) was getting flagged as *Stale PR* because the age check ran before the status check. I restructured `detect_discrepancy()` so that critical process contradictions take precedence over stale PR checks.
   * **GitHub API 404 Endpoint Error (Trailing Newline in Secret):** During the initial CI run, the workflow failed with a `404 Client Error` on the GitHub PR endpoint (`https://api.github.com/repos/...%0A/.../pulls`). Inspecting the URL revealed an encoded newline (`%0A`), caused by an accidental trailing space when copying the `GH_OWNER` repository secret. Trimming the secret value resolved the URL resolution.
   * **GitHub Actions Cron Scheduling Delays:** When setting up `schedule: - cron: "30 4 * * *"`, the runner did not fire immediately at 10:00 AM IST. After investigating GitHub's runner infrastructure documentation, I learned that scheduled workflows experience shared queue delays during high-load intervals (especially `:00` and `:30` minute marks). In production, this is mitigated by shifting schedules to uncongested off-peak minutes (e.g., `23 4 * * *`) with a time buffer before morning standups. For development and testing, I paired this with `workflow_dispatch` for instant, manual triggers.
4. **Automated Deployment:** Created `.github/workflows/sync.yml` with scheduled cron (`04:30 UTC` / `10:00 AM IST`) and `workflow_dispatch` manual triggers, injecting GCP credentials and API tokens securely via GitHub Secrets.

---

## 5. AI Collaboration & Verification Process

### Division of Work
* **AI Assistance:** Scaffolded initial GraphQL query structures for Linear, suggested `gspread` method syntax, and helped structure the `pytest` parameter matrix in `test_sync.py`.
* **Human Decisions:**
  * Architecture choice to use scheduled GitHub Actions over cloud webhooks.
  * Definition and prioritization of discrepancy edge cases (e.g., catching premature closures and unmerged abandons).
  * Design of the idempotent batch-overwrite to prevent duplicate spreadsheet entries.
  * Security posture: strictly separating `.env` and `credentials.json` from git history via `.gitignore` and storing them as GitHub repository secrets.

### How I Verified AI Output (Testing Rigor)
1. **Automated Unit Tests (`test_sync.py`):**
   * Built 8 distinct `pytest` unit test cases covering regex parsing, missing PR fallbacks, and all discrepancy permutation states.
   * Verified that all tests pass (`8 passed in 0.04s`).
2. **Live Boundary Testing:**
   * Temporarily set the stale PR threshold to `age_days >= 0` to verify that `SIT-5` dynamically changed to `Stale PR (Open for 0 days)` on the live sheet, while `SIT-10` correctly retained `Ticket marked Done but PR is still Open`.
   * Reverted threshold back to `age_days >= 7` and ran the cloud GitHub Action to confirm production stability.

---

## 6. What I Would Do Next (With Another Week)

1. **Slack & Email Notification Digest:**
   * Introduce automated Slack channel alerts and email summaries that ping the engineering team whenever high-priority discrepancies (such as merged PRs with un-updated tickets or stale PRs older than 7 days) are detected.
2. **Bidirectional Auto-Remediation:**
   * Enable write-back capabilities where the script can automatically update the Linear ticket state to "Done" when its associated GitHub PR is successfully merged, eliminating human forgetfulness.
3. **Pagination & Scalability Support:**
   * Extend the Linear GraphQL and GitHub REST fetch routines with cursor-based pagination to handle organizations with hundreds of concurrent active tickets and pull requests beyond the single-page limit.