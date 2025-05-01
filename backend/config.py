import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Base project directory

# - Upload directories -
UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads') 
RAW_APPLICANT_DIR = os.path.join(UPLOADS_DIR, 'applicants')
RAW_JOB_POSTING_DIR = os.path.join(UPLOADS_DIR, 'jobPostings')

# - Database directories -
DB_APPLICANTS_PATH = os.path.join(BASE_DIR, 'databases', 'applicants.db')
DB_JOB_POSTING_PATH = os.path.join(BASE_DIR, 'databases', 'jobPostings.db')
MATCHES_DB_PATH = os.path.join(BASE_DIR, "databases", "matches.db")

# - Upload directories -
MODEL_DIR =  os.path.join(BASE_DIR, 'models')

# - Agent directories -
RECRUITER_AGENT_DIR = os.path.join(BASE_DIR, 'agents', "first_recruiter_agent.py")
PORTFOLIO_AGENT_DIR = os.path.join(BASE_DIR, 'agents', "second_portfolio_agent.py")
HIRING_MANAGER_AGENT_DIR = os.path.join(BASE_DIR, 'agents', "third_hiring_manager_agent.py")
TECHNICAL_LEAD_AGENT_DIR = os.path.join(BASE_DIR, 'agents', "fourth_technical_lead_agent.py")
HR_COMPLIANCE_AGENT_DIR = os.path.join(BASE_DIR, 'agents', "fifth_hr_compliance_agent.py")