#!/usr/bin/env python3
"""
github_portfolio_scraper.py
----------------------------------
Scrapes a GitHub user’s public repositories, keeps only source files
(≥10 lines) in a predefined language set plus READMEs, prints
clickable GitHub links per kept file, and finishes with fractional
language usage.

Public
  portfolio_scraping(github_url: str, *, debug: bool = False) -> str
"""
import requests
from typing import List, Dict, Tuple
from urllib.parse import urljoin
from backend.sensible_info import GitHubToken

LANGUAGE_EXTS = {
    "python": (".py",), "javascript": (".js", ".jsx"), "typescript": (".ts", ".tsx"),
    "java": (".java",), "c++": (".cpp", ".cc", ".cxx", ".hpp", ".h"),
    "csharp": (".cs",), "go": (".go",), "rust": (".rs",), "ruby": (".rb",),
    "php": (".php",), "swift": (".swift",), "kotlin": (".kt", ".kts"),
    "shell": (".sh", ".bash"), "html": (".html", ".htm"), "css": (".css",)
}

class GitHubStructureScraper:
    def __init__(self, github_url: str):
        self.username = github_url.strip("/").split("/")[-1].lower()
        self.api_url = f"https://api.github.com/users/{self.username}/repos"
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': f'token {GitHubToken}'
        })
    
    def get_repos(self) -> List[Dict]:
        response = self.session.get(self.api_url)
        response.raise_for_status()
        return response.json()

    def get_repo_structure(self, repo_name: str) -> Dict:
        default_branch = self.get_default_branch(repo_name)
        repo_api = f"https://api.github.com/repos/{self.username}/{repo_name}/git/trees/{default_branch}?recursive=1"
        response = self.session.get(repo_api)
        if response.status_code != 200:
            return {}
        return response.json()

    def get_default_branch(self, repo_name: str) -> str:
        response = self.session.get(f"https://api.github.com/repos/{self.username}/{repo_name}")
        response.raise_for_status()
        return response.json().get("default_branch", "main")

    def is_valid_file(self, filename: str) -> bool:
        ext = '.' + filename.split('.')[-1].lower()
        return (
            filename.lower().startswith("readme") or 
            any(ext in exts for exts in LANGUAGE_EXTS.values())
        )

    def has_minimum_lines(self, repo_name: str, file_path: str, branch: str) -> bool:
        raw_url = f"https://raw.githubusercontent.com/{self.username}/{repo_name}/{branch}/{file_path}"
        response = self.session.get(raw_url)
        if response.status_code != 200:
            return False
        return len(response.text.strip().splitlines()) >= 10

    def scrape_with_error(self) -> Tuple[Tuple[int, List[str], Dict[str, List[str]]], Exception | None]:
        """
        Executes scrape() and returns both the result and any caught exception.
        If no error occurs, the second item in the tuple is None.
        """
        try:
            result = self.scrape()
            return result, None
        except Exception as e:
            return (0, [], {}), e
        
    def scrape(self) -> Tuple[int, List[str], Dict[str, List[str]]]:
        repos = self.get_repos()
        file_links = []
        structures = {}

        for repo in repos:
            repo_name = repo['name']
            if repo_name.lower() == self.username:
                continue  # Ignore repos named after the user

            branch = repo.get("default_branch", "main")
            structure = []
            tree_data = self.get_repo_structure(repo_name)
            tree_items = tree_data.get("tree", [])

            for item in tree_items:
                if item['type'] == 'blob' and self.is_valid_file(item['path']):
                    if self.has_minimum_lines(repo_name, item['path'], branch):
                        github_url = f"https://github.com/{self.username}/{repo_name}/blob/{branch}/{item['path']}"
                        file_links.append(github_url)
                        structure.append(item['path'])

            structures[repo_name] = structure
        
        return len(structures), file_links, structures

if __name__ == "__main__":
    scraper = GitHubStructureScraper("https://github.com/KhizarFareed")
    (result, error) = scraper.scrape_with_error()

    if error:
        print(f"[!] Error scraping GitHub user '{scraper.username}': {type(error).__name__} - {error}")
    else:
        num_repos, urls, structures = result

        print(f"\nFound {num_repos} repos.")
        print("\nSample URLs:")
        for url in urls[:5]:
            print(f"- {url}")
        
        print("\nProject Structure Summary:")
        for repo, files in structures.items():
            print(f"{repo} ({len(files)} files):")
            for f in files:
                print(f"  └── {f}")
