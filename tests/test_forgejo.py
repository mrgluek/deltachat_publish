import socket
import unittest
from unittest.mock import MagicMock, patch

from forgejo_client import ForgejoClient, is_safe_url


class TestForgejoClientSecurity(unittest.TestCase):
    def test_safe_urls(self):
        self.assertTrue(is_safe_url("https://git.gluek.info"))
        self.assertTrue(is_safe_url("https://github.com/mrgluek/repo"))
        self.assertTrue(is_safe_url("http://example.com/api"))

    def test_rejected_schemes(self):
        self.assertFalse(is_safe_url("ftp://git.gluek.info"))
        self.assertFalse(is_safe_url("file:///etc/passwd"))
        self.assertFalse(is_safe_url("javascript:alert(1)"))
        self.assertFalse(is_safe_url(""))
        self.assertFalse(is_safe_url(None))

    def test_rejected_local_hostnames(self):
        self.assertFalse(is_safe_url("http://localhost:3000"))
        self.assertFalse(is_safe_url("http://server.local"))
        self.assertFalse(is_safe_url("http://git.internal"))
        self.assertFalse(is_safe_url("http://forgejo.lan"))

    def test_rejected_ip_literals(self):
        self.assertFalse(is_safe_url("http://127.0.0.1:3000"))
        self.assertFalse(is_safe_url("http://169.254.169.254/latest/meta-data"))
        self.assertFalse(is_safe_url("http://192.168.1.1:3000"))
        self.assertFalse(is_safe_url("http://10.0.0.1"))
        self.assertFalse(is_safe_url("http://[::1]"))

    def test_dns_resolution_private_ip_blocked(self):
        fake_addr_info = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443)),
        ]
        with patch('socket.getaddrinfo', return_value=fake_addr_info):
            self.assertFalse(is_safe_url("https://git.example.com"))

        fake_metadata_info = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('169.254.169.254', 443)),
        ]
        with patch('socket.getaddrinfo', return_value=fake_metadata_info):
            self.assertFalse(is_safe_url("https://git.example.com"))

    def test_commit_files_rejects_unsafe_base_url(self):
        client = ForgejoClient(
            base_url="http://127.0.0.1:3000",
            token="test-token",
            repo_owner="user",
            repo_name="repo",
        )
        with self.assertRaises(ValueError) as ctx:
            client.commit_files([{"operation": "create", "path": "test.md", "content": "dGVzdA=="}], "Commit")
        self.assertIn("Unsafe or forbidden", str(ctx.exception))

    def test_check_connection_rejects_unsafe_base_url(self):
        client = ForgejoClient(
            base_url="http://169.254.169.254",
            token="test-token",
            repo_owner="user",
            repo_name="repo",
        )
        self.assertFalse(client.check_connection())

    def test_commit_files_with_safe_url(self):
        client = ForgejoClient(
            base_url="https://git.gluek.info",
            token="test-token",
            repo_owner="gluek",
            repo_name="blog",
        )
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"content": {"name": "test.md"}}'
        mock_resp.__enter__.return_value = mock_resp

        with patch('urllib.request.urlopen', return_value=mock_resp):
            res = client.commit_files([{"operation": "create", "path": "test.md", "content": "dGVzdA=="}], "Commit")
            self.assertEqual(res["content"]["name"], "test.md")


if __name__ == "__main__":
    unittest.main()
