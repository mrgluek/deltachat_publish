"""
Tests for automatic account creation on `serve` (ensure_configured_account), with a mocked RPC only.
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

import bot


class TestAutoAccount(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        for key in ("ADDR", "MAIL_PW", "RELAY", "MAIL_SERVER", "MAIL_PORT"):
            os.environ.pop(key, None)

    def _args(self, account=None):
        args = MagicMock(account=account)
        args.cmd = bot.dc_cli.__class__  # anything not named _serve_cmd
        return args

    def _serve_args(self, account=None):
        def _serve_cmd(*_):
            pass
        return MagicMock(account=account, cmd=_serve_cmd)

    def test_creates_account_on_serve_without_configured_one(self):
        b = MagicMock()
        b.rpc.get_all_account_ids.return_value = []
        b.rpc.add_account.return_value = 1
        b.rpc.get_config.return_value = "abc@chatmail.example"
        bot.ensure_configured_account(b, self._serve_args())
        b.rpc.set_config.assert_any_call(1, "bot", "1")
        b.rpc.init_transports.assert_called_once_with(1, None)
        b.rpc.add_transport_from_qr.assert_not_called()

    def test_reuses_unconfigured_account(self):
        b = MagicMock()
        b.rpc.get_all_account_ids.return_value = [3]
        b.rpc.is_configured.return_value = False
        bot.ensure_configured_account(b, self._serve_args())
        b.rpc.add_account.assert_not_called()
        b.rpc.init_transports.assert_called_once_with(3, None)

    def test_nothing_when_configured_or_not_serving(self):
        b = MagicMock()
        b.rpc.get_all_account_ids.return_value = [1]
        b.rpc.is_configured.return_value = True
        bot.ensure_configured_account(b, self._serve_args())
        b.rpc.is_configured.return_value = False
        bot.ensure_configured_account(b, self._args())
        b.rpc.init_transports.assert_not_called()
        b.rpc.add_account.assert_not_called()

    def test_relay_from_env(self):
        os.environ["RELAY"] = "chatmail.example"
        b = MagicMock()
        b.rpc.get_all_account_ids.return_value = [1]
        b.rpc.is_configured.return_value = False
        bot.ensure_configured_account(b, self._serve_args())
        b.rpc.add_transport_from_qr.assert_called_once_with(1, "DCACCOUNT:chatmail.example")
        b.rpc.init_transports.assert_not_called()

    def test_addr_and_password_from_env(self):
        os.environ["ADDR"] = "bot@example.org"
        os.environ["MAIL_PW"] = "secret"
        b = MagicMock()
        b.rpc.get_all_account_ids.return_value = [1]
        b.rpc.is_configured.return_value = False
        bot.ensure_configured_account(b, self._serve_args())
        b.rpc.add_or_update_transport.assert_called_once_with(1, {"addr": "bot@example.org", "password": "secret"})
        b.rpc.init_transports.assert_not_called()

    def test_failure_is_logged_not_raised(self):
        b = MagicMock()
        b.rpc.get_all_account_ids.return_value = []
        b.rpc.init_transports.side_effect = RuntimeError("no relay answered")
        bot.ensure_configured_account(b, self._serve_args())
        b.logger.error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
