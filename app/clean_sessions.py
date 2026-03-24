import os
from pathlib import Path
from datetime import datetime, timedelta

SESSIONS_DIR = Path("../sessions")
MAX_AGE_DAYS = 30

def cleanup_sessions():
    cutoff = datetime.now() - timedelta(days=MAX_AGE_DAYS)
    for session_file in SESSIONS_DIR.glob("*.json"):
        modified = datetime.fromtimestamp(session_file.stat().st_mtime)
        if modified < cutoff:
            session_file.unlink()
            print(f"Deleted {session_file.name}")

if __name__ == "__main__":
    cleanup_sessions()