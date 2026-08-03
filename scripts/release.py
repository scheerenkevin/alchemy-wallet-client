#!/usr/bin/env python3
"""Compute the next SemVer version from Conventional Commits since the last
release tag, bump the package version, and roll the CHANGELOG's
`[Unreleased]` section into a dated release section.

Used by the `release` GitHub Actions job on merges to `main`. Exits quietly
(writing `skip=true` to `$GITHUB_OUTPUT`) if there are no commits since the
last tag, so a no-op merge to `main` doesn't produce an empty release.
"""

from __future__ import annotations

import os
import re
import subprocess
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INIT_FILE = REPO_ROOT / "src" / "alchemy_wallet_client" / "__init__.py"
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"

VERSION_RE = re.compile(r'__version__\s*=\s*"(?P<version>\d+\.\d+\.\d+)"')
BREAKING_HEADER_RE = re.compile(r"^\w+(\([^)]+\))?!:")


def run(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def get_last_tag() -> str | None:
    try:
        return run("git", "describe", "--tags", "--abbrev=0")
    except subprocess.CalledProcessError:
        return None


def get_commits_since(tag: str | None) -> list[str]:
    rev_range = f"{tag}..HEAD" if tag else "HEAD"
    log = run("git", "log", rev_range, "--pretty=format:%s%n%b---END---")
    return [chunk for chunk in log.split("---END---") if chunk.strip()]


def determine_bump(commits: list[str]) -> str:
    bump = "patch"
    for msg in commits:
        subject = msg.strip().splitlines()[0] if msg.strip() else ""
        if "BREAKING CHANGE" in msg or BREAKING_HEADER_RE.match(subject):
            return "major"
        if subject.startswith("feat"):
            bump = "minor"
    return bump


def bump_version(current: str, bump: str) -> str:
    major, minor, patch = (int(part) for part in current.split("."))
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def read_current_version() -> str:
    match = VERSION_RE.search(INIT_FILE.read_text())
    if not match:
        raise SystemExit(f"Could not find __version__ in {INIT_FILE}")
    return match.group("version")


def write_version(new_version: str) -> None:
    text = INIT_FILE.read_text()
    text = VERSION_RE.sub(f'__version__ = "{new_version}"', text, count=1)
    INIT_FILE.write_text(text)


def roll_changelog(new_version: str) -> None:
    text = CHANGELOG_FILE.read_text()
    today = date.today().isoformat()
    marker = "## [Unreleased]"
    if marker not in text:
        raise SystemExit(f"Could not find '{marker}' in {CHANGELOG_FILE}")
    replacement = f"{marker}\n\n## [{new_version}] - {today}"
    text = text.replace(marker, replacement, 1)
    CHANGELOG_FILE.write_text(text)


def write_output(**kwargs: str) -> None:
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if not gh_output:
        return
    with open(gh_output, "a") as fh:
        for key, value in kwargs.items():
            fh.write(f"{key}={value}\n")


def main() -> None:
    last_tag = get_last_tag()
    commits = get_commits_since(last_tag)

    if not commits:
        print("No commits since last release tag; skipping release.")
        write_output(skip="true")
        return

    bump = determine_bump(commits)
    current = read_current_version()
    new_version = bump_version(current, bump)

    write_version(new_version)
    roll_changelog(new_version)

    print(f"Bumping {current} -> {new_version} ({bump}) based on {len(commits)} commit(s).")
    write_output(skip="false", version=new_version)


if __name__ == "__main__":
    main()
