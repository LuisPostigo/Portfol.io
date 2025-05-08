import os
import sys
import json
import shutil
import contextlib
from llama_cpp import Llama
from backend.config import MODEL_DIR, CODING_MODEL
from backend.services.github_analyzer.github_structure_scraper import GitHubStructureScraper
from backend.services.github_analyzer.analizes_a_single_script import SingleScriptAnalyzer

# ======================================
# Suppresses llama_cpp noisy output
# ======================================

@contextlib.contextmanager
def suppress_output():
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

MODEL_PATH = os.path.join(MODEL_DIR, CODING_MODEL)
with suppress_output():
    model = Llama(model_path=MODEL_PATH, n_ctx=4096, n_gpu_layers=-1)

class PortfolioAnalyzer:
    def __init__(self, github_url: str, skills: list[str]):
        self.github_url = github_url
        self.skills = [s.lower() for s in skills]
        self.repo_count = 0
        self.file_links = []
        self.analysis_results = {}

    def save_analysis_to_local(self, repo: str, file_path: str, result: str):
        from urllib.parse import urlparse
        user = urlparse(self.github_url).path.strip("/")
        base_dir = os.path.join("backend", "services", "github_analyzer", "analized_files", user)
        structure_path = os.path.join(base_dir, repo, file_path)
        os.makedirs(os.path.dirname(structure_path), exist_ok=True)
        with open(structure_path + ".json", "w", encoding="utf-8") as f:
            json.dump({"file": file_path, "result": result}, f, indent=2)

    def analyze(self) -> Exception | None:
        from urllib.parse import urlparse
        username = urlparse(self.github_url).path.strip("/")
        base_dir = os.path.join("backend", "services", "github_analyzer", "analized_files", username)

        if os.path.exists(base_dir) and any(os.scandir(base_dir)):
            print(f"[>>] Analysis already exists for {username}, skipping reprocessing.")
            return None

        scraper = GitHubStructureScraper(self.github_url)
        (scrape_result, error) = scraper.scrape_with_error()

        if error:
            print(f"[!] GitHub scraping failed for {username}: {error}")
            return error

        self.repo_count, self.file_links, repo_structure = scrape_result
        print(f"[✓] Found {self.repo_count} repositories with {len(self.file_links)} relevant files.")

        for repo_index, (repo, files) in enumerate(repo_structure.items(), start=1):
            print(f"\n[→] Working on Repository {repo_index}/{self.repo_count}: {repo}")
            repo_results = []
            for i, file_path in enumerate(files, start=1):
                print(f"   {i}/{len(files)}")
                file_url = f"https://github.com/{scraper.username}/{repo}/blob/main/{file_path}"
                try:
                    analyzer = SingleScriptAnalyzer(file_url, self.skills, model)
                    result_dict = analyzer.run()

                    if "result" in result_dict:
                        raw_result = result_dict["result"]
                        lines = raw_result.strip().splitlines()
                        lines = [l for l in lines if not l.lower().startswith("note") and not l.strip().startswith("```json")]
                        cleaned_output = "\n".join(lines).strip()

                        repo_results.append({"file": file_url, "result": cleaned_output})
                        self.save_analysis_to_local(repo, file_path, cleaned_output)
                    else:
                        print(f"(!) Skipped saving for {file_url} due to error: {result_dict.get('error')}")
                except Exception:
                    pass
            self.analysis_results[repo] = repo_results

        return None

if __name__ == "__main__":

    ##############################################################
    #                           Testing                          #
    ##############################################################

    url = "https://github.com/KhizarFareed"
    skills = ["Data Structures", "Operating Systems", "AI", "ML"]

    analyzer = PortfolioAnalyzer(url, skills)
    error = analyzer.analyze()

    if error:
        print(f"[ERROR] Portfolio analysis failed: {type(error).__name__} - {error}")
    else:
        n_repos, files, results = analyzer.get_results()
        print("\n--- Summary ---")
        print(f"Total Repositories: {n_repos}")
        print(f"Total Files Analyzed: {len(files)}")
