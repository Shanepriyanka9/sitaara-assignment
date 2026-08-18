import pytest
from sync import detect_discrepancy

def test_no_pr_in_progress():
    assert detect_discrepancy("In Progress", None) == "No PR created"

def test_no_pr_backlog():
    assert detect_discrepancy("Backlog", None) == "None"

def test_pr_merged_ticket_not_done():
    pr = {"state": "merged", "merged": True}
    assert detect_discrepancy("In Progress", pr) == "PR Merged but ticket not Done"

def test_pr_open_ticket_done():
    pr = {"state": "open", "merged": False}
    assert detect_discrepancy("Done", pr) == "Ticket marked Done but PR is still Open"

def test_in_sync():
    pr = {"state": "merged", "merged": True}
    assert detect_discrepancy("Done", pr) == "None"