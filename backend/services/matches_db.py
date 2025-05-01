import sqlite3
from datetime import datetime
import re
import os

from backend.config import MATCHES_DB_PATH

def initialize_matches_db():
    """
    Creates the matches database and 'matches' table if not present.
    """
    conn = sqlite3.connect(MATCHES_DB_PATH)
    cursor = conn.cursor()

    # 🛠 Matches table with (applicant_id, job_id) as PRIMARY KEY
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            applicant_id TEXT NOT NULL,
            job_id TEXT NOT NULL,
            recruiter_agent TEXT,
            other_agent1 TEXT,
            final_decision TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (applicant_id, job_id)
        )
    ''')

    conn.commit()
    conn.close()

def save_match_result(applicant_id, job_id, agent_name, agent_opinion):
    """
    Saves an agent's opinion to the matches.db.
    Dynamically creates the column if it does not exist.
    """
    conn = sqlite3.connect(MATCHES_DB_PATH)
    cursor = conn.cursor()

    # Step 1: Ensure the column exists
    cursor.execute("PRAGMA table_info(matches)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    if agent_name not in existing_columns:
        print(f"🛠 Adding missing column '{agent_name}' to matches table...")
        cursor.execute(f"ALTER TABLE matches ADD COLUMN {agent_name} TEXT")

    # Step 2: Insert or update match record
    cursor.execute('''
        INSERT INTO matches (applicant_id, job_id)
        VALUES (?, ?)
        ON CONFLICT(applicant_id, job_id) DO NOTHING
    ''', (applicant_id, job_id))

    cursor.execute(f'''
        UPDATE matches
        SET {agent_name} = ?, updated_at = CURRENT_TIMESTAMP
        WHERE applicant_id = ? AND job_id = ?
    ''', (agent_opinion, applicant_id, job_id))

    conn.commit()
    conn.close()
    print(f"✅ Opinion saved for applicant {applicant_id} vs job {job_id} ({agent_name})")

def load_recruiter_opinion(applicant_id):
    """
    Loads the recruiter's decision and opinion for a given applicant from matches.db.
    Returns a dictionary with 'flag' and 'message'.
    """
    try:
        conn = sqlite3.connect(MATCHES_DB_PATH)
        cursor = conn.cursor()

        query = "SELECT recruiter_agent FROM matches WHERE applicant_id = ?"
        cursor.execute(query, (applicant_id,))
        result = cursor.fetchone()

        conn.close()

        if result is None or result[0] is None:
            print(f"⚠️ No recruiter result found for applicant {applicant_id}")
            return None

        recruiter_text = result[0]

        # Extract YES or NO from the recruiter's final recommendation
        match = re.search(r'Final recommendation:\s*\*\*(Yes|No)\*\*', recruiter_text, re.IGNORECASE)
        flag = match.group(1) if match else "Unknown"

        return {
            "flag": flag,
            "message": recruiter_text
        }

    except Exception as e:
        print(f"❌ Error loading recruiter opinion: {e}")
        return None


def upload_debates(agent1_name, agent2_name, job_id, applicant_id):
    """
    Combines two agent opinions and saves them into a debate column in matches.db.
    Creates a dynamic {agent1}_{agent2}_debate_resolution column if it does not exist.
    """
    conn = sqlite3.connect(MATCHES_DB_PATH)
    cursor = conn.cursor()

    try:
        # Fetch the two agent opinions directly
        cursor.execute(f'''
            SELECT "{agent1_name}", "{agent2_name}"
            FROM matches
            WHERE applicant_id = ? AND job_id = ?
        ''', (applicant_id, job_id))

        row = cursor.fetchone()

        if not row:
            print(f"⚠️ No match record found for applicant {applicant_id} and job {job_id}.")
            return

        opinion_agent1, opinion_agent2 = row

        if not opinion_agent1 or not opinion_agent2:
            print(f"⚠️ Missing opinions for debate: {agent1_name} or {agent2_name}")
            return

        # Create debate transcript
        debate_transcript = f"""
{agent1_name} says:
{opinion_agent1}

{agent2_name} says:
{opinion_agent2}
        """.strip()

        # Column name for debate resolution
        debate_column = f"{agent1_name}_{agent2_name}_debate_resolution"

        # Check if debate_column exists
        cursor.execute("PRAGMA table_info(matches)")
        columns = [info[1] for info in cursor.fetchall()]

        if debate_column not in columns:
            cursor.execute(f'''
                ALTER TABLE matches ADD COLUMN "{debate_column}" TEXT
            ''')
            conn.commit()
            print(f"🛠 Created missing column: {debate_column}")

        # Save the debate transcript
        cursor.execute(f'''
            UPDATE matches
            SET "{debate_column}" = ?
            WHERE applicant_id = ? AND job_id = ?
        ''', (debate_transcript, applicant_id, job_id))

        conn.commit()
        print(f"✅ Debate transcript uploaded under column '{debate_column}' for applicant {applicant_id} and job {job_id}")

    except Exception as e:
        print(f"❌ Error uploading debate: {e}")

    finally:
        conn.close()