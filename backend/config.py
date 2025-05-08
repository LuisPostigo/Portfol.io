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
FOUNDATION_MODEL = "mistral-7b-instruct-v0.1.Q4_K_M.gguf"
CODING_MODEL = "deepseek-coder-1.3b-instruct.Q4_K_M.gguf"

# - Repo Analysis directories -
REPO_ANALYSIS_DIR = os.path.join(BASE_DIR, 'services', 'github_analyzer')
ANALYZE_EACH_SCRIPT_BACKGROUND_DIR = os.path.join(REPO_ANALYSIS_DIR, 'main.py')
REPO_STRUCTURE = os.path.join(REPO_ANALYSIS_DIR, 'github_structure_scraper.py')
REPO_SUMMARY_ASSESSMENT = os.path.join(REPO_ANALYSIS_DIR, 'analizes_a_repo.py')

# - Agent directories -
RECRUITER_AGENT_DIR = os.path.join(BASE_DIR, 'agents', "first_recruiter_agent.py")
PORTFOLIO_AGENT_DIR = os.path.join(BASE_DIR, 'agents', "second_portfolio_agent.py")
HIRING_MANAGER_AGENT_DIR = os.path.join(BASE_DIR, 'agents', "third_hiring_manager_agent.py")
TECHNICAL_LEAD_AGENT_DIR = os.path.join(BASE_DIR, 'agents', "fourth_technical_lead_agent.py")
HR_COMPLIANCE_AGENT_DIR = os.path.join(BASE_DIR, 'agents', "fifth_hr_compliance_agent.py")