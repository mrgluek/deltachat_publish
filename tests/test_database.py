import os
import sys
import unittest
from unittest.mock import MagicMock

# Setup test DB path before importing modules
TEST_DB = "test_publish_database.db"
os.environ["DB_PATH"] = TEST_DB

# Mock deltachat2 and deltabot_cli if not installed
try:
    import deltachat2
except ImportError:
    mock_dc2 = MagicMock()
    class MsgData:
        def __init__(self, text="", file="", override_sender_name=None):
            self.text = text
            self.file = file
    mock_dc2.MsgData = MsgData
    sys.modules['deltachat2'] = mock_dc2

try:
    import deltabot_cli
except ImportError:
    class MockBotCli:
        def __init__(self, *args, **kwargs):
            pass
        def on(self, *args, **kwargs):
            return lambda func: func
        def on_init(self, func):
            return func
        def on_start(self, func):
            return func
        def start(self):
            pass
    mock_dbc = MagicMock()
    mock_dbc.BotCli = MockBotCli
    sys.modules['deltabot_cli'] = mock_dbc

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database


class TestDatabase(unittest.TestCase):
    def setUp(self):
        database.DB_PATH = TEST_DB
        database.init_db()

    def tearDown(self):
        for path in [TEST_DB, TEST_DB + "-wal", TEST_DB + "-shm"]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    # --- Config ---

    def test_set_and_get_config(self):
        database.set_config("test_key", "test_value")
        self.assertEqual(database.get_config("test_key"), "test_value")

    def test_get_config_missing(self):
        self.assertIsNone(database.get_config("nonexistent_key"))

    def test_set_config_overwrite(self):
        database.set_config("k", "v1")
        database.set_config("k", "v2")
        self.assertEqual(database.get_config("k"), "v2")

    # --- Admin email ---

    def test_get_admin_email_from_db(self):
        database.set_config("admin_dc_email", "admin@example.com")
        self.assertEqual(database.get_admin_email(), "admin@example.com")

    def test_get_admin_email_normalized(self):
        database.set_config("admin_dc_email", "  ADMIN@EXAMPLE.COM  ")
        self.assertEqual(database.get_admin_email(), "admin@example.com")

    # --- Admin fingerprint ---

    def test_set_and_get_admin_fingerprint(self):
        database.set_admin_fingerprint("A1:B2:C3:D4:E5:F6:78:90:A1:B2:C3:D4:E5:F6:78:90")
        fp = database.get_admin_fingerprint()
        self.assertIsNotNone(fp)
        self.assertNotIn(":", fp)       # colons stripped
        self.assertEqual(fp, fp.upper())  # uppercase

    def test_invalid_fingerprint_returns_none(self):
        database.set_admin_fingerprint("not-a-fingerprint")
        self.assertIsNone(database.get_admin_fingerprint())

    # --- Authorization ---

    def test_is_authorized_email_only(self):
        database.set_config("admin_dc_email", "admin@gluek.info")
        self.assertTrue(database.is_authorized_sender("admin@gluek.info"))
        self.assertTrue(database.is_authorized_sender("ADMIN@GLUEK.INFO"))
        self.assertFalse(database.is_authorized_sender("hacker@evil.com"))

    def test_is_authorized_no_admin_configured(self):
        # No admin set → nobody is authorized
        self.assertFalse(database.is_authorized_sender("anyone@example.com"))

    def test_is_authorized_with_correct_fingerprint(self):
        database.set_config("admin_dc_email", "admin@gluek.info")
        database.set_admin_fingerprint("AABBCCDDAABBCCDDAABBCCDDAABBCCDD")
        self.assertTrue(database.is_authorized_sender(
            "admin@gluek.info", "AABBCCDDAABBCCDDAABBCCDDAABBCCDD"
        ))

    def test_is_authorized_wrong_fingerprint(self):
        database.set_config("admin_dc_email", "admin@gluek.info")
        database.set_admin_fingerprint("AABBCCDDAABBCCDDAABBCCDDAABBCCDD")
        self.assertFalse(database.is_authorized_sender(
            "admin@gluek.info", "DEADBEEFDEADBEEFDEADBEEFDEADBEEF"
        ))

    # --- Published posts ---

    def test_log_and_get_recent_posts(self):
        database.log_published_post(slug="my-post", title="My Post", commit_sha="abc1234")
        posts = database.get_recent_posts(limit=5)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["slug"], "my-post")
        self.assertEqual(posts[0]["title"], "My Post")
        self.assertEqual(posts[0]["commit_sha"], "abc1234")

    def test_get_recent_posts_ordering(self):
        database.log_published_post(slug="first", title="First")
        database.log_published_post(slug="second", title="Second")
        database.log_published_post(slug="third", title="Third")
        posts = database.get_recent_posts(limit=5)
        # Most recent first
        self.assertEqual(posts[0]["slug"], "third")
        self.assertEqual(posts[-1]["slug"], "first")

    def test_get_posts_count(self):
        self.assertEqual(database.get_posts_count(), 0)
        database.log_published_post(slug="p1", title="P1")
        database.log_published_post(slug="p2", title="P2")
        self.assertEqual(database.get_posts_count(), 2)

    # --- Transport stats ---

    def test_update_transport_stats_sent(self):
        database.update_transport_stats("bot@chatmail.uk", sent=True)
        stats = database.get_all_transport_stats()
        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0]["addr"], "bot@chatmail.uk")
        self.assertEqual(stats[0]["msgs_sent"], 1)
        self.assertEqual(stats[0]["msgs_received"], 0)
        self.assertIsNotNone(stats[0]["last_sent_at"])
        self.assertIsNone(stats[0]["last_received_at"])

    def test_update_transport_stats_received(self):
        database.update_transport_stats("bot@chatmail.uk", received=True)
        stats = database.get_all_transport_stats()
        self.assertEqual(stats[0]["msgs_received"], 1)
        self.assertIsNotNone(stats[0]["last_received_at"])

    def test_transport_stats_accumulate(self):
        database.update_transport_stats("bot@chatmail.uk", sent=True)
        database.update_transport_stats("bot@chatmail.uk", sent=True)
        database.update_transport_stats("bot@chatmail.uk", received=True)
        stats = database.get_all_transport_stats()
        self.assertEqual(stats[0]["msgs_sent"], 2)
        self.assertEqual(stats[0]["msgs_received"], 1)

    def test_multiple_transport_stats(self):
        database.update_transport_stats("addr1@example.com", sent=True)
        database.update_transport_stats("addr2@example.com", received=True)
        stats_map = {s["addr"]: s for s in database.get_all_transport_stats()}
        self.assertIn("addr1@example.com", stats_map)
        self.assertIn("addr2@example.com", stats_map)
        self.assertEqual(stats_map["addr1@example.com"]["msgs_sent"], 1)
        self.assertEqual(stats_map["addr2@example.com"]["msgs_received"], 1)

    # --- Resilient flag ---

    def test_resilient_flag_default_off(self):
        self.assertNotEqual(database.get_config("resilient"), "1")

    def test_resilient_flag_toggle(self):
        database.set_config("resilient", "0")
        self.assertFalse(database.get_config("resilient") == "1")
        database.set_config("resilient", "1")
        self.assertTrue(database.get_config("resilient") == "1")
        database.set_config("resilient", "0")
        self.assertFalse(database.get_config("resilient") == "1")


if __name__ == "__main__":
    unittest.main()
