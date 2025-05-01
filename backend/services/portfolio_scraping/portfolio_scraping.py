# portfolio_scraping.py

from .scraper_api import GitHubAPIScraper  # ✅ Updated to the API-based scraper
from .analyzer import CodeAnalyzer
from .config import SHOW_PROGRESS_BAR

from pprint import pprint
from tqdm import tqdm
from .utils import safe_request

def portfolio_scraping(url, skills_to_verify, github_token=None):
    """
    Main function to scrape a GitHub profile, analyze skills across projects, and return combined output.
    
    Args:
        url (str): GitHub profile URL (e.g., https://github.com/LuisPostigo)
        skills_to_verify (list): List of skills to analyze (currently not heavily used)
        github_token (str, optional): GitHub API token for higher rate limits
    """
    combined_output = {}

    print(f"\n🔍 Starting scraping for {url}...")
    scraper = GitHubAPIScraper(url, github_token=github_token)
    scraper.scrape_all()

    print(f"\n🧠 Loading Code Analyzer...")
    analyzer = CodeAnalyzer(skills_to_verify)

    projects = scraper.projects

    for project in tqdm(projects, desc="📦 Analyzing Projects", disable=not SHOW_PROGRESS_BAR):
        project_result = {
            "project_name": project,
            "files_analyzed": []
        }

        files = scraper.repo_files.get(project, [])

        print(f"\n📂 Files found for project {project}: {len(files)} files")
        for f in files:
            print(f"  - {f}")

        for file_url in files:
            # Try fetching the file content
            response = safe_request(file_url)
            if not response:
                print(f"⚠️ Failed to fetch file: {file_url}")
                continue
            file_content = response.text
            file_name = file_url.split("/")[-1]  # Just the filename part

            print(f"\n📄 Considering file: {file_name}")

            # Only analyze code files
            if not file_name.endswith(('.py', '.cpp', '.h', '.js', '.java', '.ts')):
                print(f"⚠️ Skipping non-code file: {file_name}")
                continue

            # Analyze the file
            score, explanation = analyzer.analyze_code_file(file_content, "general coding skill")

            if score is not None:
                print(f"✅ Scored file {file_name}: {score}/10 - {explanation}")
                project_result["files_analyzed"].append({
                    "file": file_name,
                    "score": score,
                    "explanation": explanation
                })
            else:
                print(f"⚠️ No valid score returned for file {file_name}")

        if not project_result["files_analyzed"]:
            print(f"⚠️ No code files analyzed for project {project}.")

        combined_output[project] = project_result

    print("\n🎯 Final Combined Output:")
    pprint(combined_output, width=120)

    return combined_output

# --- Manual Tester ---

if __name__ == "__main__":
    # Example usage
    url = "https://github.com/LuisPostigo"
    skills = ["general coding skill"]  # Placeholder, not used right now

    # Optionally: if you have a GitHub token, pass it here
    github_token = None  # Example: "ghp_xxx..." 

    portfolio_scraping(url, skills, github_token=github_token)
