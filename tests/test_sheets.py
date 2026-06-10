"""Unit tests for SheetsClient."""

import pytest
from sheets.client import SheetsClient


def test_sheets_client_missing_creds():
    """Verify that sheets client raises FileNotFoundError when credentials file is missing."""
    client = SheetsClient(cred_path="nonexistent_creds.json", sheet_id="some_id")
    
    with pytest.raises(FileNotFoundError):
        client.initialize()
