import base64
import os
import logging
from typing import List, Dict, Any
import aiohttp

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

    async def commit_files(self, files: List[Dict[str, str]], message: str) -> Dict[str, Any]:
        """
        Creates a single commit with multiple files using Forgejo/Gitea API.
        
        files element format:
        {
            "operation": "create", # "create", "update", "delete"
            "path": "relative/path/in/repo.md",
            "content": "base64_encoded_string"
        }
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

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status not in (200, 201):
                    error_text = await resp.text()
                    logger.error(f"Forgejo API error ({resp.status}): {error_text}")
                    raise RuntimeError(f"Forgejo API returned HTTP {resp.status}: {error_text}")
                
                return await resp.json()

    async def check_connection(self) -> bool:
        """Verifies repository access via API."""
        if not self.is_configured():
            return False
        url = f"{self.base_url}/api/v1/repos/{self.repo_owner}/{self.repo_name}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/json",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=5) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.warning(f"Forgejo connectivity check failed: {e}")
            return False
