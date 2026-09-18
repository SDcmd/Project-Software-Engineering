from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime


_GITHUB_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/(?:issues/(?P<issue>\d+)|pull/(?P<pull>\d+))/?(?:[?#].*)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GitHubLink:
    owner: str
    repo: str
    kind: str
    number: int
    canonical_url: str

    @property
    def repository(self) -> str:
        return f"{self.owner}/{self.repo}"


class GitHubIntegrationError(ValueError):
    pass


class GitHubService:
    """Small, deliberately bounded GitHub integration for HelperDev tasks.

    HelperDev stores only the issue/PR URL and cached public metadata. Authentication is
    optional through the GITHUB_TOKEN environment variable; tokens are never written to
    the SQLite database.
    """

    def __init__(self, db):
        self.db = db

    @staticmethod
    def parse_url(url: str) -> GitHubLink:
        value = (url or "").strip()
        match = _GITHUB_RE.match(value)
        if not match:
            raise GitHubIntegrationError(
                "Use a GitHub issue or pull-request URL, for example https://github.com/owner/repo/issues/12 or /pull/34"
            )
        owner = match.group("owner")
        repo = match.group("repo")
        if repo.lower().endswith(".git"):
            repo = repo[:-4]
        if match.group("pull"):
            kind = "PULL_REQUEST"
            number = int(match.group("pull"))
            canonical = f"https://github.com/{owner}/{repo}/pull/{number}"
        else:
            kind = "ISSUE"
            number = int(match.group("issue"))
            canonical = f"https://github.com/{owner}/{repo}/issues/{number}"
        return GitHubLink(owner, repo, kind, number, canonical)

    def link_task(self, task_id: int, url: str, auto_complete: bool = False) -> GitHubLink:
        link = self.parse_url(url)
        with self.db.connect() as conn:
            row = conn.execute("SELECT 1 FROM tasks WHERE id=? AND archived=0", (task_id,)).fetchone()
            if not row:
                raise GitHubIntegrationError("Task does not exist or is archived")
            conn.execute(
                """UPDATE tasks
                   SET github_url=?, github_kind=?, github_repo=?, github_number=?, github_state='NOT_SYNCED',
                       github_title=NULL, github_synced_at=NULL, github_auto_complete=?
                   WHERE id=?""",
                (link.canonical_url, link.kind, link.repository, link.number, 1 if auto_complete else 0, task_id),
            )
        return link

    def unlink_task(self, task_id: int) -> None:
        with self.db.connect() as conn:
            cur = conn.execute(
                """UPDATE tasks SET github_url=NULL, github_kind=NULL, github_repo=NULL, github_number=NULL,
                   github_state=NULL, github_title=NULL, github_synced_at=NULL, github_auto_complete=0
                   WHERE id=? AND archived=0""",
                (task_id,),
            )
            if cur.rowcount == 0:
                raise GitHubIntegrationError("Task does not exist or is archived")

    def sync_task(self, task_id: int) -> dict:
        with self.db.connect() as conn:
            row = conn.execute(
                """SELECT id,progress_status,github_url,github_kind,github_repo,github_number,github_auto_complete
                   FROM tasks WHERE id=? AND archived=0""",
                (task_id,),
            ).fetchone()
        if not row:
            raise GitHubIntegrationError("Task does not exist or is archived")
        if not row["github_url"]:
            raise GitHubIntegrationError("This task is not linked to GitHub")

        owner, repo = row["github_repo"].split("/", 1)
        number = int(row["github_number"])
        kind = row["github_kind"]
        endpoint = (
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}"
            if kind == "PULL_REQUEST"
            else f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
        )
        data = self._fetch_json(endpoint)

        if kind == "PULL_REQUEST":
            merged = bool(data.get("merged")) or bool(data.get("merged_at"))
            state = "MERGED" if merged else str(data.get("state", "unknown")).upper()
        else:
            state = str(data.get("state", "unknown")).upper()

        title = str(data.get("title") or "")[:300]
        synced_at = datetime.now().strftime("%Y-%m-%dT%H:%M")
        auto_completed = False
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE tasks SET github_state=?, github_title=?, github_synced_at=? WHERE id=?",
                (state, title, synced_at, task_id),
            )
            if (
                kind == "PULL_REQUEST"
                and state == "MERGED"
                and int(row["github_auto_complete"] or 0) == 1
                and row["progress_status"] != "DONE"
            ):
                conn.execute("UPDATE tasks SET progress_status='DONE' WHERE id=?", (task_id,))
                auto_completed = True

        return {
            "state": state,
            "title": title,
            "synced_at": synced_at,
            "auto_completed": auto_completed,
            "kind": kind,
            "repo": row["github_repo"],
            "number": number,
        }

    def _fetch_json(self, url: str) -> dict:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "HelperDev",
            "X-GitHub-Api-Version": "2026-03-10",
        }
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise GitHubIntegrationError(
                    "GitHub item was not found. For a private repository, set GITHUB_TOKEN before starting HelperDev."
                ) from exc
            if exc.code in {401, 403}:
                raise GitHubIntegrationError(
                    "GitHub denied the request or the API rate limit was reached. Set GITHUB_TOKEN and try again."
                ) from exc
            raise GitHubIntegrationError(f"GitHub API request failed with HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise GitHubIntegrationError("Could not reach GitHub. Check your internet connection and try again.") from exc
        except (json.JSONDecodeError, TimeoutError) as exc:
            raise GitHubIntegrationError("GitHub returned an invalid or timed-out response") from exc
