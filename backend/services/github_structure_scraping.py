#!/usr/bin/env python3
"""
github_portfolio_scraper.py
----------------------------------
Scrape every public repository of a GitHub user and output an
indented directory‑tree for each one.

Usage from another script
-------------------------
from github_portfolio_scraper import portfolio_scraping
portfolio_scraping("https://github.com/<user>")

…or standalone
--------------
$ python github_portfolio_scraper.py https://github.com/<user>
"""

from __future__ import annotations
import os
import sys
import requests
from urllib.parse import urlparse

API_ROOT = "https://api.github.com"
TOKEN = os.getenv("GITHUB_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

# ─────────────────────── helpers ────────────────────────
def _username_from_url(url: str) -> str:
    path = urlparse(url.rstrip("/")).path.lstrip("/")
    return path.split("/")[0] if path else ""

def _get_json(url: str) -> list | dict:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def _list_repos(user: str) -> list[dict]:
    repos, page = [], 1
    while True:
        batch = _get_json(f"{API_ROOT}/users/{user}/repos?per_page=100&page={page}")
        if not batch: break
        repos.extend(batch); page += 1
    return repos

def _fetch_tree(user: str, repo: str, sha: str) -> list[dict]:
    url = f"{API_ROOT}/repos/{user}/{repo}/git/trees/{sha}?recursive=1"
    return _get_json(url).get("tree", [])

def _pretty_tree(paths: list[str]) -> str:
    root: dict = {}
    for path in sorted(paths):
        cur = root
        for part in path.split("/"):
            cur = cur.setdefault(part, {})
    lines: list[str] = []
    def walk(node, prefix=""):
        items = list(node.items())
        for i, (name, children) in enumerate(items):
            connector = "└── " if i == len(items)-1 else "├── "
            lines.append(prefix + connector + name)
            if children:
                ext = "    " if i == len(items)-1 else "│   "
                walk(children, prefix + ext)
    walk(root)
    return "\n".join(lines) or "(Empty repository)"

# ───────────────────── main callable ─────────────────────
def portfolio_scraping(github_url: str) -> str:
    user = _username_from_url(github_url)
    if not user:
        msg = f"No GitHub profiles were found under {github_url}"
        print(msg)
        return msg

    try:
        repos = [r for r in _list_repos(user) if r["name"].lower() != user.lower()]
    except requests.HTTPError as e:
        if e.response.status_code == 404:          # profile doesn’t exist
            msg = f"No GitHub profiles were found under {github_url}"
            print(msg)
            return msg
        raise   
     
    repos = [r for r in _list_repos(user) if r["name"].lower() != user.lower()]
    if not repos:
        output = "⚠️  No public repositories found."
        print(output)
        return output

    lines = []
    lines.append("\n📂 Found repositories:")
    lines.extend(f"- {repo['name']}" for repo in repos)
    lines.append("")

    for repo in repos:
        branch = repo["default_branch"]
        sha = _get_json(f"{API_ROOT}/repos/{user}/{repo['name']}/branches/{branch}")["commit"]["sha"]
        tree = _fetch_tree(user, repo["name"], sha)
        paths = [item["path"] for item in tree if item["type"] in {"tree", "blob"}]

        lines.append(f"🛠️  Structure for \"{repo['name']}\":")
        lines.append(_pretty_tree(paths))
        lines.append("")  # blank line between repos

    output = "\n".join(lines).rstrip()
    print(output)
    return output

# ────────────────────── CLI entry point ───────────────────
if __name__ == "__main__":
    # --- Manual Tester ---
    if len(sys.argv) == 1:          # run the example if no args supplied
        url = "https://github.com/LuisPostigo"
        portfolio_scraping(url)
    elif len(sys.argv) == 2:        # called from shell with an argument
        portfolio_scraping(sys.argv[1])
    else:
        sys.exit("Usage: python github_portfolio_scraper.py <github‑url>")
