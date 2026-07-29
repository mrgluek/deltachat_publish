import base64
import json
import logging
import os
import urllib.request
import urllib.error
from typing import List, Dict, Any

logger = logging.getLogger("deltachat_publish.forgejo")


class ForgejoClient:
    def __init__(
        self,
        base_url: str = None,
        token: str = None,
        repo_owner: str = None,
        repo_name: str = None,
        branch: str = None,
    ):
        self.base_url = (base_url or os.getenv("FORGEJO_URL", "https://git.gluek.info")).rstrip("/")
        self.token = token or os.getenv("FORGEJO_TOKEN", "")
        self.repo_owner = repo_owner or os.getenv("FORGEJO_REPO_OWNER", "gluek")
        self.repo_name = repo_name or os.getenv("FORGEJO_REPO_NAME", "gluek.info")
        self.branch = branch or os.getenv("FORGEJO_BRANCH", "main")

    def is_configured(self) -> bool:
        return bool(self.token and self.base_url and self.repo_owner and self.repo_name)

    def commit_files(self, files: List[Dict[str, str]], message: str) -> Dict[str, Any]:
        """
        Creates a single commit with multiple files using Forgejo/Gitea API synchronously.
        """
        if not self.is_configured():
            raise ValueError("Forgejo client is missing configuration (FORGEJO_TOKEN required).")

        url = f"{self.base_url}/api/v1/repos/{self.repo_owner}/{self.repo_name}/contents"
        headers = {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "branch": self.branch,
            "message": message,
            "files": files,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            error_text = e.read().decode("utf-8")
            logger.error(f"Forgejo API error ({e.code}): {error_text}")
            raise RuntimeError(f"Forgejo API returned HTTP {e.code}: {error_text}")
        except Exception as e:
            logger.error(f"Forgejo API request failed: {e}")
            raise

    def check_connection(self) -> bool:
        """Verifies repository access via API synchronously."""
        if not self.is_configured():
            return False
        url = f"{self.base_url}/api/v1/repos/{self.repo_owner}/{self.repo_name}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/json",
        }
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning(f"Forgejo connectivity check failed: {e}")
            return False
