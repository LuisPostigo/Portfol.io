import pika
import sqlite3
import json
from backend.config import DB_APPLICANTS_PATH, DB_JOB_POSTING_PATH

def dispatch_applicant_to_all_jobs(applicant_id):
    """
    Dispatches a new applicant to be evaluated against all available job postings.
    """
    print(f"📨 Dispatching Applicant {applicant_id} to all jobs...")

    # Connect to RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='resume_queue_recruiter')

    # Get applicant parsed data
    conn = sqlite3.connect(DB_APPLICANTS_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT parsed_json FROM files WHERE id = ?", (applicant_id,))
    result = cursor.fetchone()
    conn.close()

    if not result or not result[0]:
        print(f"(⚠️) No parsed JSON for applicant {applicant_id}")
        return

    applicant_data = json.loads(result[0])

    # Now also get all job postings
    conn = sqlite3.connect(DB_JOB_POSTING_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, parsed_json FROM files WHERE parsed_json IS NOT NULL")
    job_postings = cursor.fetchall()
    conn.close()

    # Send applicant + each job context
    for job_id, job_json in job_postings:
        job_data = json.loads(job_json)
        message = {
            "type": "mcp_context",
            "target_agent": "RecruiterAgent",  # ✨ NEW
            "applicant_id": applicant_id,
            "job_id": job_id,
            "context": {
                "job": job_data,
                "input": applicant_data
            }
        }
        channel.basic_publish(
            exchange='',
            routing_key='resume_queue_recruiter',
            body=json.dumps(message)
        )
        print(f"📡 Sent applicant {applicant_id} for job {job_id}")

    connection.close()

def dispatch_all_applicants_to_job(job_id):
    """
    Dispatches all existing applicants to be evaluated against a new job posting.
    """
    print(f"📨 Dispatching all applicants for Job {job_id}...")

    # Connect to RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='resume_queue_recruiter')

    # Get job posting parsed data
    conn = sqlite3.connect(DB_JOB_POSTING_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT parsed_json FROM files WHERE id = ?", (job_id,))
    result = cursor.fetchone()
    conn.close()

    if not result or not result[0]:
        print(f"(⚠️) No parsed JSON for job {job_id}")
        return

    job_data = json.loads(result[0])

    # Now also get all applicants
    conn = sqlite3.connect(DB_APPLICANTS_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, parsed_json FROM files WHERE parsed_json IS NOT NULL")
    applicants = cursor.fetchall()
    conn.close()

    # Send each applicant + job context
    for applicant_id, applicant_json in applicants:
        applicant_data = json.loads(applicant_json)
        message = {
            "type": "mcp_context",
            "target_agent": "RecruiterAgent",  # ✨ NEW
            "applicant_id": applicant_id,
            "job_id": job_id,
            "context": {
                "job": job_data,
                "input": applicant_data
            }
        }
        channel.basic_publish(
            exchange='',
            routing_key='resume_queue_recruiter',
            body=json.dumps(message)
        )
        print(f"📡 Sent applicant {applicant_id} for job {job_id}")

    connection.close()
