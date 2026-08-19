from datetime import datetime, timezone, timedelta
import pytest
from sync import detect_discrepancy


def test_no_pr_in_progress():
    assert detect_discrepancy("In Progress", None) == "No PR created"


def test_no_pr_backlog():
    assert detect_discrepancy("Backlog", None) == "None"


def test_pr_merged_ticket_not_done():
    pr = {"state": "merged"}
    assert detect_discrepancy("In Progress", pr) == "PR Merged but ticket not Done"


def test_pr_open_ticket_done():
    now_str = datetime.now(timezone.utc).isoformat()
    pr = {"state": "open", "created_at": now_str}
    assert detect_discrepancy("Done", pr) == "Ticket marked Done but PR is still Open"


def test_stale_pr_flagged():
    # Simulate a PR created 10 days ago
    ten_days_ago = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    pr = {"state": "open", "created_at": ten_days_ago}
    assert detect_discrepancy("In Progress", pr) == "Stale PR (Open for 10 days)"


def test_pr_closed_without_merge():
    pr = {"state": "closed"}
    assert detect_discrepancy("Done", pr) == "Ticket Done but PR closed without merge"


def test_in_sync_merged():
    pr = {"state": "merged"}
    assert detect_discrepancy("Done", pr) == "None"


def test_in_sync_recent_open():
    now_str = datetime.now(timezone.utc).isoformat()
    pr = {"state": "open", "created_at": now_str}
    assert detect_discrepancy("In Progress", pr) == "None"