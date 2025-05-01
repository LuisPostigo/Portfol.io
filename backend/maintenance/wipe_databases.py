import sqlite3
import os
import sys
import shutil

# Add backend folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import (
    DB_APPLICANTS_PATH, 
    DB_JOB_POSTING_PATH, 
    MATCHES_DB_PATH,
    RAW_APPLICANT_DIR, 
    RAW_JOB_POSTING_DIR
)

def wipe_table(db_path, table_name):
    if not os.path.exists(db_path):
        print(f"❌ DB not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(f"DELETE FROM {table_name}")
        conn.commit()
        print(f"🗑️ Wiped all entries from {db_path} (table: {table_name})")
    except Exception as e:
        print(f"⚠️ Failed to wipe {db_path}: {e}")
    finally:
        conn.close()

def wipe_directory(directory_path):
    if not os.path.exists(directory_path):
        print(f"❌ Directory not found: {directory_path}")
        return

    try:
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        print(f"🗑️ Wiped all files inside {directory_path}")
    except Exception as e:
        print(f"⚠️ Failed to wipe {directory_path}: {e}")

if __name__ == "__main__":
    # Wipe databases
    wipe_table(DB_APPLICANTS_PATH, "files")
    wipe_table(DB_JOB_POSTING_PATH, "files")
    wipe_table(MATCHES_DB_PATH, "matches")

    # Wipe uploaded files
    wipe_directory(RAW_APPLICANT_DIR)
    wipe_directory(RAW_JOB_POSTING_DIR)
