import base64
import ipaddress
import json
import logging
import os
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse
from typing import List, Dict, Any

logger = logging.getLogger("deltachat_publish.forgejo")


def is_safe_url(url: str) -> bool:
    """Validate that URL uses http(s) and does not target loopback, private, link-local, or cloud metadata IP ranges."""
    if not url or not isinstance(url, str):
        return False
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return False
        hostname = (p.hostname or "").lower().strip()
        if not hostname:
            return False
        if hostname in ("localhost", "127.0.0.1", "::1") or hostname.endswith((".local", ".internal", ".lan")):
            return False

        # Direct IP checks
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
                return False
            if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
                mapped_v4 = ip.ipv4_mapped
                if (
                    mapped_v4.is_private
                    or mapped_v4.is_loopback
                    or mapped_v4.is_link_local
                    or mapped_v4.is_multicast
                    or mapped_v4.is_reserved
                ):
                    return False
        except ValueError:
            pass

        # DNS resolution check
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for _, _, _, _, sockaddr in addr_info:
                ip_str = sockaddr[0]
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
                    return False
                if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
                    mapped_v4 = ip.ipv4_mapped
                    if (
                        mapped_v4.is_private
                        or mapped_v4.is_loopback
                        or mapped_v4.is_link_local
                        or mapped_v4.is_multicast
                        or mapped_v4.is_reserved
                    ):
                        return False
        except (socket.gaierror, OSError):
            pass

        return True
    except Exception:
        return False


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

        if not is_safe_url(self.base_url):
            raise ValueError(f"Unsafe or forbidden Forgejo target URL: {self.base_url}")

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
                body = resp.read(10 * 1024 * 1024).decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            error_text = e.read(65536).decode("utf-8", errors="replace")
            logger.error(f"Forgejo API error ({e.code}): {error_text}")
            raise RuntimeError(f"Forgejo API returned HTTP {e.code}: {error_text}")
        except Exception as e:
            logger.error(f"Forgejo API request failed: {e}")
            raise

    def check_connection(self) -> bool:
        """Verifies repository access via API synchronously."""
        if not self.is_configured():
            return False
        if not is_safe_url(self.base_url):
            logger.warning(f"Unsafe Forgejo target URL: {self.base_url}")
            return False
        url = f"{self.base_url}/api/v1/repos/{self.repo_owner}/{self.repo_name}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/json",
        }
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read(65536)
                return resp.status == 200
        except Exception as e:
            logger.warning(f"Forgejo connectivity check failed: {e}")
            return False
