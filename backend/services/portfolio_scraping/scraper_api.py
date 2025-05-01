# scraper_api.py

import requests
from urllib.parse import urlparse
from collections import defaultdict
import time

class GitHubAPIScraper:
    def __init__(self, url, github_token=None):
        """
        Initialize with GitHub profile URL. Optionally pass a GitHub token for higher rate limits.
        """
        self.url = url
        self.projects = []
        self.repo_files = defaultdict(list)  # repo_name -> list of file download URLs
        self.github_token = github_token

    def _get_headers(self):
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    def _is_github(self):
        return "github.com" in self.url.lower()

    def _get_username(self):
        parsed = urlparse(self.url)
        username = parsed.path.strip('/')
        return username

    def _list_repos(self, username):
        api_url = f"https://api.github.com/users/{username}/repos"
        response = requests.get(api_url, headers=self._get_headers())
        response.raise_for_status()

        repos = response.json()
        for repo in repos:
            self.projects.append(repo['name'])

    def _scrape_repo_files_recursive(self, username, repo_name, path=""):
        api_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{path}"
        response = requests.get(api_url, headers=self._get_headers())
        if response.status_code == 404:
            print(f"⚠️ Skipping missing path: {path}")
            return
        response.raise_for_status()

        items = response.json()

        if isinstance(items, dict) and items.get("type") == "file":
            # Single file
            self.repo_files[repo_name].append(items['download_url'])
            return

        for item in items:
            if item['type'] == 'file':
                self.repo_files[repo_name].append(item['download_url'])
            elif item['type'] == 'dir':
                self._scrape_repo_files_recursive(username, repo_name, path=item['path'])

    def scrape_all(self):
        if not self._is_github():
            print("❌ Only GitHub profiles are supported.")
            return

        username = self._get_username()
        print(f"📂 Listing repos for {username}...")
        self._list_repos(username)

        for project in self.projects:
            print(f"🔍 Scraping files for repo: {project}")
            self._scrape_repo_files_recursive(username, project)

        print(f"✅ Done scraping all projects for {username}.")

