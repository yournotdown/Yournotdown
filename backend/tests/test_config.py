"""Shared test config — keeps credentials out of source files.

Set ADMIN_SESSION_TOKEN and USER_SESSION_TOKEN env vars (the testing-agent
injects matching docs into mongo and writes the values to
/app/memory/test_credentials.md). The defaults here mirror what's in that
file and exist only so the suite is runnable locally without manual setup.
"""
import os

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://whatsyoudown.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_TOKEN = os.environ.get("ADMIN_SESSION_TOKEN", "test_session_admin_1780165861579")
USER_TOKEN = os.environ.get("USER_SESSION_TOKEN", "test_session_user_1780165861637")
