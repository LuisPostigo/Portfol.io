import os
import json
import subprocess
from pathlib import Path

GH_URL = "https://github.com/LuisPostigo"

# Commonly‑claimed skills for the smoke test
CLAIMED_SKILLS = [
    "python", "javascript", "java", "c++",
    "sql", "aws", "docker", "react",
]


def run_cli(url: str, skills: list[str]) -> dict:
    """Invoke the repo_analyzer CLI and return its JSON payload."""
    skills_arg = ",".join(skills)
    cmd = [
        "python",
        "-m",
        "backend.services.github_analyzer.repo_analyzer",
        url,
        skills_arg,
    ]

    # Force UTF‑8 pipes so Windows never trips on Unicode characters
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        env=env,
        encoding="utf-8",
        errors="replace",
    )

    # Extract the JSON object from mixed log + JSON stdout
    out = res.stdout
    first = out.find("{")        # first opening brace
    last  = out.rfind("}")       # last closing brace
    if first == -1 or last == -1 or last < first:
        raise AssertionError("No JSON payload found in CLI output")

    json_blob = out[first : last + 1]
    return json.loads(json_blob)


def test_repo_analyzer_smoke(tmp_path, monkeypatch):
    """
    End‑to‑end smoke test of the GitHub analyzer.
    Ensures:
    • top‑level keys are present
    • every requested skill returns an int 0‑10
    • language counts are non‑negative ints
    """
    report = run_cli(GH_URL, CLAIMED_SKILLS)

    # ── top‑level shape ───────────────────────────────
    assert {"url", "num_projects", "projects", "overall_skill_scores"} <= report.keys()
    assert report["url"] == GH_URL
    assert report["num_projects"] == len(report["projects"]) >= 1

    # ── overall skill scores ─────────────────────────
    overall = report["overall_skill_scores"]
    for sk in CLAIMED_SKILLS:
        assert sk in overall, f"missing skill '{sk}'"
        score = overall[sk]
        assert isinstance(score, int) and 0 <= score <= 10

    # ── per‑project sanity ───────────────────────────
    for proj in report["projects"]:
        assert "file_language_counts" in proj and proj["file_language_counts"]
        for lang, count in proj["file_language_counts"].items():
            assert isinstance(count, int) and count >= 0
