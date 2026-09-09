"""
Tests for transport and admin commands in deltachat_publish.
Verifies private chat enforcement on /addtransport and /initadmin,
resilient mode commands, and error sanitization.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock dependencies if missing
try:
    import deltachat2
except ImportError:
    mock_deltachat2 = MagicMock()
    class MsgData:
        def __init__(self, text="", file="", override_sender_name=None):
            self.text = text
            self.file = file
            self.override_sender_name = override_sender_name
    mock_deltachat2.MsgData = MsgData
    sys.modules['deltachat2'] = mock_deltachat2

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
    mock_deltabot_cli = MagicMock()
    mock_deltabot_cli.BotCli = MockBotCli
    sys.modules['deltabot_cli'] = mock_deltabot_cli

import database
import bot

TEST_DB_PATH = "test_publish_cmds.db"


class TestTransportCommands(unittest.TestCase):
    def setUp(self):
        self.orig_db_path = database.DB_PATH
        database.DB_PATH = TEST_DB_PATH
        with database._transport_stats_lock:
            database._transport_stats_buffer.clear()
        database.init_db()

        self.mock_bot = MagicMock()
        self.mock_event = MagicMock()
        self.mock_msg = MagicMock()
        self.mock_msg.from_id = 100
        self.mock_msg.chat_id = 10
        self.mock_msg.file = None
        self.mock_event.msg = self.mock_msg
        self.accid = 1

        # Contact mock
        self.mock_contact = {
            "address": "admin@gluek.info",
            "fingerprint": "AABBCCDDAABBCCDDAABBCCDDAABBCCDD",
            "is_self": False,
        }
        self.mock_bot.rpc.get_contact.return_value = self.mock_contact

    def tearDown(self):
        database.DB_PATH = self.orig_db_path
        for f in (TEST_DB_PATH, f"{TEST_DB_PATH}-wal", f"{TEST_DB_PATH}-shm"):
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass

    # ── /initadmin tests ───────────────────────────────────────────────────

    @patch("bot._is_private_chat")
    def test_initadmin_rejected_in_group_chat(self, mock_is_private):
        mock_is_private.return_value = False
        self.mock_msg.text = "/initadmin"

        bot.on_new_message(self.mock_bot, self.accid, self.mock_event)

        self.mock_bot.rpc.send_msg.assert_called_once()
        msg_text = self.mock_bot.rpc.send_msg.call_args[0][2].text
        self.assertIn("only be used in a private 1:1 chat", msg_text)

    @patch("bot._is_private_chat")
    def test_initadmin_success_in_private_chat(self, mock_is_private):
        mock_is_private.return_value = True
        self.mock_msg.text = "/initadmin"

        bot.on_new_message(self.mock_bot, self.accid, self.mock_event)

        self.assertEqual(database.get_admin_email(), "admin@gluek.info")
        self.assertEqual(database.get_admin_fingerprint(), "AABBCCDDAABBCCDDAABBCCDDAABBCCDD")
        self.mock_bot.rpc.send_msg.assert_called_once()
        msg_text = self.mock_bot.rpc.send_msg.call_args[0][2].text
        self.assertIn("Ownership successfully claimed", msg_text)

    @patch("bot._is_private_chat")
    def test_initadmin_rejected_if_already_claimed(self, mock_is_private):
        mock_is_private.return_value = True
        database.set_config("admin_dc_email", "existing@example.com")
        self.mock_msg.text = "/initadmin"

        bot.on_new_message(self.mock_bot, self.accid, self.mock_event)

        self.mock_bot.rpc.send_msg.assert_called_once()
        msg_text = self.mock_bot.rpc.send_msg.call_args[0][2].text
        self.assertIn("Admin is already set", msg_text)

    # ── /addtransport tests ────────────────────────────────────────────────

    @patch("bot._is_private_chat")
    def test_addtransport_requires_admin(self, mock_is_private):
        mock_is_private.return_value = True
        # Admin is someone else
        database.set_config("admin_dc_email", "other@example.com")
        self.mock_msg.text = "/addtransport user@example.com pass123"

        bot.on_new_message(self.mock_bot, self.accid, self.mock_event)

        self.mock_bot.rpc.send_msg.assert_called_once()
        msg_text = self.mock_bot.rpc.send_msg.call_args[0][2].text
        self.assertIn("only for the administrator", msg_text)

    @patch("bot._is_private_chat")
    def test_addtransport_rejected_in_group_chat(self, mock_is_private):
        mock_is_private.return_value = False
        database.set_config("admin_dc_email", "admin@gluek.info")
        database.set_admin_fingerprint("AABBCCDDAABBCCDDAABBCCDDAABBCCDD")
        self.mock_msg.text = "/addtransport user@example.com pass123"

        bot.on_new_message(self.mock_bot, self.accid, self.mock_event)

        self.mock_bot.rpc.send_msg.assert_called_once()
        msg_text = self.mock_bot.rpc.send_msg.call_args[0][2].text
        self.assertIn("only be used in a private 1:1 chat", msg_text)

    @patch("bot._is_private_chat")
    def test_addtransport_success_in_private_chat(self, mock_is_private):
        mock_is_private.return_value = True
        database.set_config("admin_dc_email", "admin@gluek.info")
        database.set_admin_fingerprint("AABBCCDDAABBCCDDAABBCCDDAABBCCDD")
        self.mock_msg.text = "/addtransport backup@example.com pass123"

        bot.on_new_message(self.mock_bot, self.accid, self.mock_event)

        self.mock_bot.rpc.add_or_update_transport.assert_called_once_with(
            self.accid, {"addr": "backup@example.com", "password": "pass123"}
        )
        self.mock_bot.rpc.send_msg.assert_called_once()
        msg_text = self.mock_bot.rpc.send_msg.call_args[0][2].text
        self.assertIn("Backup transport `backup@example.com` added", msg_text)

    @patch("bot._is_private_chat")
    def test_addtransport_error_sanitized(self, mock_is_private):
        mock_is_private.return_value = True
        database.set_config("admin_dc_email", "admin@gluek.info")
        database.set_admin_fingerprint("AABBCCDDAABBCCDDAABBCCDDAABBCCDD")
        self.mock_msg.text = "/addtransport backup@example.com pass123"
        self.mock_bot.rpc.add_or_update_transport.side_effect = RuntimeError("secret server database crashed")

        bot.on_new_message(self.mock_bot, self.accid, self.mock_event)

        self.mock_bot.rpc.send_msg.assert_called_once()
        msg_text = self.mock_bot.rpc.send_msg.call_args[0][2].text
        self.assertIn("Failed to add transport. Check server logs", msg_text)
        self.assertNotIn("secret server database", msg_text)

    # ── /resilient tests ───────────────────────────────────────────────────

    def test_resilient_command_toggle(self):
        database.set_config("admin_dc_email", "admin@gluek.info")
        database.set_admin_fingerprint("AABBCCDDAABBCCDDAABBCCDDAABBCCDD")

        self.mock_msg.text = "/resilient on"
        bot.on_new_message(self.mock_bot, self.accid, self.mock_event)
        self.assertEqual(database.get_config("resilient"), "1")

        self.mock_msg.text = "/resilient off"
        bot.on_new_message(self.mock_bot, self.accid, self.mock_event)
        self.assertEqual(database.get_config("resilient"), "0")


if __name__ == "__main__":
    unittest.main()
