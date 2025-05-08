import os
import subprocess
import sqlite3
import psutil
import json
from typing import List

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

from backend.pre_processing.pre_processing_main import insert_file_if_missing, initialize_and_import_all
from backend.config import RAW_APPLICANT_DIR, RAW_JOB_POSTING_DIR, DB_JOB_POSTING_PATH, DB_APPLICANTS_PATH

#######################################################################################
#----------------------------------  FastAPI setup -----------------------------------#
#######################################################################################

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status")
def get_file_status():
    def fetch_from_db(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, file_path, file_name, original_name, file_type, status, uploaded_at FROM files')
        rows = cursor.fetchall()
        conn.close()
        return rows

    applicant_rows = fetch_from_db(DB_APPLICANTS_PATH)
    job_rows = fetch_from_db(DB_JOB_POSTING_PATH)

    combined = applicant_rows + job_rows
    return [{
        "id": row[0],
        "file_path": row[1],
        "file_name": row[2],
        "original_name": row[3],
        "file_type": row[4],
        "status": row[5],
        "uploaded_at": row[6],
    } for row in combined]

@app.get("/view")
def view_file(path: str):
    """
    Serves a file given its path on the server.
    """
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "File not found"}

@app.delete("/delete")
def delete_file(id: str = Query(...), path: str = Query(...)):
    try:
        # 1. Deletes file from disk
        if os.path.exists(path):
            os.remove(path)
            print(f"(main.py)[X] Deleted file at {path}")
        else:
            print(f"(main.py)[!] File {path} not found on disk")

        # 2. Deletes from applicants.db
        conn = sqlite3.connect(DB_APPLICANTS_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM files WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        print(f"(main.py)[X] Deleted applicant {id} from applicants.db")

        # 3. Deletes from matches.db
        matches_db_path = os.path.join("backend", "databases", "matches.db")
        if os.path.exists(matches_db_path):
            conn = sqlite3.connect(matches_db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM matches WHERE applicant_id = ?", (id,))
            conn.commit()
            conn.close()
            print(f"(main.py)[X] Deleted all matches for applicant {id} from matches.db")
        else:
            print(f"(main.py)[!] matches.db not found")

        return {"message": "(main.py)[!] File and related records deleted"}

    except Exception as e:
        print(f"(main.py)[E] Failed to delete: {e}")
        return {"error": str(e)}

@app.get("/matches/{job_id}")
def get_matches_for_job(job_id: str):
    matches_db_path = os.path.join("backend", "databases", "matches.db")
    if not os.path.exists(matches_db_path):
        return []

    conn = sqlite3.connect(matches_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT applicant_id FROM matches WHERE job_id = ?", (job_id,))
    applicants = cursor.fetchall()
    conn.close()

    return [row[0] for row in applicants] 

@app.get("/match_details")
def get_match_details(applicant_id: str, job_id: str):
    """
    Returns all four agent evaluations plus, if present, the full debate
    transcript and the winner column.

    Response shape:
    {
        "recruiter_agent": "<markdown/llm text>",
        "hiring_manager_agent": "<markdown/llm text>",
        "portfolio_agent": "<markdown/llm text>",
        "technical_lead_agent": "<markdown/llm text>",
        "debate_transcript": [               # list[dict] or []
            {"source": "RecruiterAgent", "text": "..."},
            {"source": "HiringManagerAgent", "text": "..."},
            ...
        ],
        "debate_winner": "recruiteragent" | "hiringmanageragent" | None
    }
    """
    db_path = os.path.join("backend", "databases", "matches.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    base = "recruiteragent_hiringmanageragent_debate_response"

    cur.execute(
        f"""
        SELECT recruiter_agent,
               hiring_manager_agent,
               portfolio_agent,
               technical_lead_agent,
               "{base}"        AS debate_raw,
               "{base}_winner" AS debate_winner
        FROM matches
        WHERE applicant_id = ? AND job_id = ?
        """,
        (applicant_id, job_id)
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return JSONResponse({"error": "No match found"}, status_code=404)

    # ---------- reshape the debate transcript ----------
    transcript_struct = []
    raw = row["debate_raw"]

    if raw:
        try:
            raw_list = json.loads(raw)  # expect list[dict]
            for item in raw_list:
                if isinstance(item, dict):
                    agent, text = next(iter(item.items()))
                    transcript_struct.append({"source": agent, "text": text})
                else:
                    transcript_struct.append({"source": "system", "text": str(item)})
        except Exception:
            transcript_struct = [{"source": "system", "text": raw}]

    # ---------- build response ----------
    return {
        "recruiter_agent":       row["recruiter_agent"],
        "hiring_manager_agent":  row["hiring_manager_agent"],
        "portfolio_agent":       row["portfolio_agent"],
        "technical_lead_agent":  row["technical_lead_agent"],
        "debate_transcript":     transcript_struct,
        "debate_winner":         row["debate_winner"],
    }

@app.get("/debate")
def get_debate(applicant_id: str, job_id: str):
    db = os.path.join("backend", "databases", "matches.db")
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    base = "recruiteragent_hiringmanageragent_debate_response"
    cur.execute(
        f'''SELECT "{base}", "{base}_winner"
            FROM matches
            WHERE applicant_id = ? AND job_id = ?''',
        (applicant_id, job_id)
    )
    row = cur.fetchone()
    conn.close()

    if not row or row[base] is None:
        return JSONResponse({"error": "No debate found"}, status_code=404)

    try:
        transcript = json.loads(row[base])
    except Exception:
        # fall back to raw text if it somehow wasn't stored as JSON
        transcript = [{"source": "system", "text": row[base]}]

    return {"debate_transcript": transcript, "winner": row[f"{base}_winner"]}

@app.get("/details")
def get_file_details(id: str):
    """
    Returns parsed_json from either applicants.db or jobPostings.db based on the ID.
    """
    for db_path in [DB_APPLICANTS_PATH, DB_JOB_POSTING_PATH]:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT parsed_json FROM files WHERE id = ?", (id,))
        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            try:
                return json.loads(result[0])
            except Exception as e:
                return JSONResponse(content={"error": f"Failed to parse JSON: {e}"}, status_code=500)

    return JSONResponse(content={"error": "No parsed data found"}, status_code=404)

#######################################################################################
#----------------------------------   main setup   -----------------------------------#
#######################################################################################

def save_file(file: UploadFile, file_type: str):
    """
    Saves the uploaded file to the correct raw directory.
    """
    try:
        if file_type == "resume":
            save_dir = RAW_APPLICANT_DIR
        elif file_type == "job_posting":
            save_dir = RAW_JOB_POSTING_DIR
        else:
            save_dir = os.path.join("uploads", "raw", file_type)

        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, file.filename)

        with open(save_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)

        print(f"(main.py)[Check] Saved: {save_path}")
        return {'file_path': save_path, 'file_type': file_type, 'file_name': file.filename}
    except Exception as e:
        print(f"(main.py)[!] Failed to save {file.filename}: {e}")
        return None

def run_processing_pipeline(all_files_info):
    """
    Full backend pipeline: DB registration, transcript extraction, parsing, and agent trigger.
    """
    try:
        initialize_and_import_all()
        # (0) Launches RabbitMQ server
        if not any("rabbitmq-server" in p.name().lower() for p in psutil.process_iter()):
            print("Starting RabbitMQ Server...")
            subprocess.Popen([
                'start', 'cmd.exe', '/k',
                '"C:\\Program Files\\RabbitMQ Server\\rabbitmq_server-3.12.2\\sbin\\rabbitmq-server.bat"'
            ], shell=True)
        else:
            print("RabbitMQ Server already running.")

        # (1)
        # Launches recruiter agent
        subprocess.Popen([
            'start', 'cmd.exe', '/k',
            'title RecruiterAgent && conda activate portfol_io && python -m backend.agents.first_recruiter_agent'
        ], shell=True)

        # Launches portfolio agent
        subprocess.Popen([
            'start', 'cmd.exe', '/k',
            'title PortfolioAgent && conda activate portfol_io && python -m backend.agents.second_portfolio_agent'
        ], shell=True)

        # Launches hiring manager agent
        subprocess.Popen([
            'start', 'cmd.exe', '/k',
            'title HiringManagerAgent && conda activate portfol_io && python -m backend.agents.third_hiring_manager_agent'
        ], shell=True)

        # Launches technical lead agent
        subprocess.Popen([
            'start', 'cmd.exe', '/k',
            'title TechnicalLeadAgent && conda activate portfol_io && python -m backend.agents.fourth_technical_lead_agent'
        ], shell=True)

        # (2) Inserts files and triggers processing
        for file in all_files_info:
            db_path = DB_APPLICANTS_PATH if file['file_type'] == "resume" else DB_JOB_POSTING_PATH
            suffix = "a" if file['file_type'] == "resume" else "j"
            insert_file_if_missing(db_path, file['file_path'], file['file_name'], file['file_type'], suffix)

        print("(main.py)[Check] All files processed and system triggered accordingly.")

    except Exception as e:
        print(f"(main.py)[!] Error in background processing: {e}")

@app.post("/process")
async def process_files(
    background_tasks: BackgroundTasks,
    resumes: List[UploadFile] = File([]),
    jobs: List[UploadFile] = File([]),
):
    all_files_info = []

    for resume in resumes:
        info = save_file(resume, "resume")
        if info:
            all_files_info.append(info)

    for job in jobs:
        info = save_file(job, "job_posting")
        if info:
            all_files_info.append(info)

    if all_files_info:
        background_tasks.add_task(run_processing_pipeline, all_files_info)

    return {"message": "(main.py)[Check] Files received!"}

if __name__ == "__main__":
    import uvicorn
    print("Starting development server at http://localhost:8000...")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000)