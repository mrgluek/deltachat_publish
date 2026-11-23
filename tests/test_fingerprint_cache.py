"""1.4.1: the own fingerprint is read once per account, not on every message."""
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DB_PATH"] = tmp_db.name

import bot
import database
import dc_fingerprint

SELF_FP = "D58B5E6C55482F94F9F5B84B6FB9FE3AD2658082"
PEER_FP = "0ECC037BAD768C41CA99B1F5F0B80E7D5DB13122"
INFO = (f"Messages are end-to-end encrypted.\nFingerprints:\n\nMe:\n{SELF_FP}\n\n"
        f"Bob:\n{PEER_FP}\n\nRelays:\nbob@example.net")


def make_bot():
    b = MagicMock()
    b.rpc.get_chat_securejoin_qr_code.return_value = f"https://i.delta.chat/#{SELF_FP}&v=3&i=a&s=b"
    b.rpc.get_contact.return_value = {"address": "bob@example.net", "is_self": False}
    b.rpc.get_contact_encryption_info.return_value = INFO
    return b


def event(text):
    return SimpleNamespace(msg=SimpleNamespace(from_id=10, chat_id=42, text=text, file=None))


class TestOwnFingerprintCache(unittest.TestCase):
    def setUp(self):
        database.init_db()
        getattr(dc_fingerprint, "forget_self_fingerprint", lambda: None)()

    def test_helper_asks_the_core_once(self):
        rpc = make_bot().rpc
        for _ in range(1000):
            self.assertEqual(dc_fingerprint.get_self_fingerprint(rpc, 1), SELF_FP)
        self.assertEqual(rpc.get_chat_securejoin_qr_code.call_count, 1)

    def test_failures_are_not_cached_and_forget_works(self):
        rpc = MagicMock()
        rpc.get_chat_securejoin_qr_code.side_effect = [Exception("down"), f"https://i.delta.chat/#{SELF_FP}&v=3"]
        self.assertIsNone(dc_fingerprint.get_self_fingerprint(rpc, 1))
        self.assertEqual(dc_fingerprint.get_self_fingerprint(rpc, 1), SELF_FP)
        self.assertEqual(rpc.get_chat_securejoin_qr_code.call_count, 2)
        dc_fingerprint.forget_self_fingerprint(rpc, 1)
        rpc.get_chat_securejoin_qr_code.side_effect = None
        rpc.get_chat_securejoin_qr_code.return_value = f"https://i.delta.chat/#{PEER_FP}&v=3"
        self.assertEqual(dc_fingerprint.get_self_fingerprint(rpc, 1), PEER_FP)

    def test_1000_plain_messages_cost_at_most_one_qr_call(self):
        b = make_bot()
        for _ in range(1000):
            bot.on_new_message(b, 1, event("hello"))
        self.assertLessEqual(b.rpc.get_chat_securejoin_qr_code.call_count, 1)

    def test_1000_command_messages_cost_at_most_one_qr_call(self):
        b = make_bot()
        for _ in range(1000):
            bot.on_new_message(b, 1, event("/help"))
        self.assertLessEqual(b.rpc.get_chat_securejoin_qr_code.call_count, 1)


if __name__ == "__main__":
    unittest.main()
