"""
pre_processing_main.py
──────────────────────
Main entry point for pre-processing raw applicant and job posting files
in the Portfol.io MAS pipeline.

Functions
─────────
• initialize_and_import_all() -> None
      Ensures databases and tables are initialized, then bulk processes 
      files found in the applicant and job folders.

• insert_file_if_missing(db_path, file_path, original_name, file_type, suffix) -> None
      Registers a file in the appropriate database, extracts its text,
      processes it with the LLM, and stores both raw and parsed outputs.

• generate_unique_id(db_path, suffix: str) -> str
      Creates a unique ID for each file using a 7-digit number + suffix 
      ('a' for applicants, 'j' for job postings).

• bulk_import_all() -> None
      Loads all available applicant and job files into their respective databases.

• update_file_status(db_path, file_path, new_status: str) -> None
      Updates the status and timestamp of an imported file.

Behavior
────────
Automatically dispatches parsed JSONs from new resumes to all jobs, or vice versa.
Uses the resume_queue_recruiter to communicate with the RecruiterAgent.

Example CLI (manual test)
─────────────────────────
from backend.pre_processing import pre_processing_main
pre_processing_main.initialize_and_import_all()
"""

import os
import sqlite3
import json
from datetime import datetime
from backend.config import RAW_APPLICANT_DIR, RAW_JOB_POSTING_DIR, DB_APPLICANTS_PATH, DB_JOB_POSTING_PATH
from backend.pre_processing.cleans_before_parsing import FilePreprocessor
from backend.pre_processing.LLM_parser import Preprocessor
from backend.pre_processing.matching_scenarios import dispatch_applicant_to_all_jobs, dispatch_all_applicants_to_job
from backend.services.matches_db import initialize_matches_db

def initialize_and_import_all():
    """
    Ensures databases and tables exist, then bulk imports any existing files.
    """
    initialize_db(DB_APPLICANTS_PATH)
    initialize_db(DB_JOB_POSTING_PATH)
    initialize_matches_db()

    bulk_import_all()

def initialize_db(db_path):
    """
    Creates a database and corresponding 'files' table if not already present.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            original_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            transcript TEXT,
            parsed_json TEXT,
            status TEXT DEFAULT 'imported',
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def generate_unique_id(db_path, suffix):
    """
    Generates a unique 7-digit numerical ID with a suffix ('a' or 'j').
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM files")
    existing_ids = cursor.fetchall()
    existing_ids = [int(row[0][:-1]) for row in existing_ids if row[0].endswith(suffix)]

    base = 1000000
    while True:
        candidate = base
        if candidate not in existing_ids:
            break
        base += 1

    conn.close()
    return f"{candidate}{suffix}"

def insert_file_if_missing(db_path, file_path, original_name, file_type, suffix):
    """
    Inserts or updates file metadata in the specified database.
    Renames files with a unique ID, extracts the transcript,
    preprocesses it with the LLM, and saves both outputs to the DB.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, file_path FROM files WHERE file_path = ?", (file_path,))
    existing = cursor.fetchone()

    if existing:
        unique_id = existing[0]
        print(f"(pre_processing_main)[CHECK] Re-imported (updated): {original_name} as {unique_id}")
    else:
        unique_id = generate_unique_id(db_path, suffix)

    # Step 1: Renames file with ID
    new_file_name = f"{unique_id}.pdf"
    new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)
    if not os.path.exists(new_file_path):
        os.rename(file_path, new_file_path)

    # Step 2: Extracts transcript
    file_preprocessor = FilePreprocessor()
    text = file_preprocessor.extract_text_from_pdf(new_file_path) if new_file_path.endswith(".pdf") else None
    transcript = file_preprocessor.clean_text(text) if text else None

    # Step 3: Preprocesses with LLM
    parsed_json = None
    if transcript:
        llm_preprocessor = Preprocessor(mode="applicants" if file_type == "resume" else "jobPostings")
        parsed = llm_preprocessor.process_text(transcript)
        parsed_json = json.dumps(parsed, indent=2) if parsed else None

    # Step 4: Inserts full record
    cursor.execute('''
        INSERT OR REPLACE INTO files (id, file_path, file_name, original_name, file_type, transcript, parsed_json, status, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (unique_id, new_file_path, new_file_name, original_name, file_type, transcript, parsed_json, "imported", datetime.now()))

    conn.commit()
    conn.close()
    print(f"(pre_processing_main)[CHECK] Saved: {new_file_name} (original: {original_name})")

    # Step 5: Dispatches matching jobs
    if file_type == "resume":
        dispatch_applicant_to_all_jobs(unique_id)
    elif file_type == "job_posting":
        dispatch_all_applicants_to_job(unique_id)

def bulk_import_all():
    """
    Scans applicant and job posting folders and inserts all found files into their corresponding DBs.
    """
    initialize_db(DB_APPLICANTS_PATH)
    initialize_db(DB_JOB_POSTING_PATH)

    for folder, file_type, db_path, suffix in [
        (RAW_APPLICANT_DIR, "resume", DB_APPLICANTS_PATH, "a"),
        (RAW_JOB_POSTING_DIR, "job_posting", DB_JOB_POSTING_PATH, "j")
    ]:
        if not os.path.exists(folder):
            continue
        for file in os.listdir(folder):
            full_path = os.path.join(folder, file)
            if os.path.isfile(full_path):
                insert_file_if_missing(db_path, full_path, file, file_type, suffix)

def update_file_status(db_path, file_path, new_status):
    """
    Updates the status and timestamp of a file in the specified database by its full path.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM files WHERE file_path = ?", (file_path,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            "UPDATE files SET status = ?, uploaded_at = ? WHERE file_path = ?",
            (new_status, datetime.now(), file_path)
        )
        print(f"(pre_processing_main)[UPDATED] Status updated to '{new_status}' for: {os.path.basename(file_path)}")
    else:
        print(f"(pre_processing_main)[!] File not found in DB: {file_path}")

    conn.commit()
    conn.close()