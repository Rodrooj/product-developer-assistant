import importlib.util
import pathlib
import unittest
from unittest.mock import patch
from email import message_from_string

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "image/seed/skills/productivity/email-reader/plow-imap.py"
spec = importlib.util.spec_from_file_location("plow_imap", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ImapBridgeTests(unittest.TestCase):
    def test_decodes_encoded_subject(self):
        self.assertEqual(module.decode_header("=?utf-8?b?VGVzdGU=?="), "Teste")

    def test_extracts_plain_text_without_marking_attachment(self):
        msg = message_from_string(
            "From: a@example.com\n"
            "Subject: Hello\n"
            "MIME-Version: 1.0\n"
            "Content-Type: text/plain; charset=utf-8\n\n"
            "Important body"
        )
        body, truncated = module.text_part(msg, 100)
        self.assertEqual(body, "Important body")
        self.assertFalse(truncated)

    def test_standalone_email_imap_variables_resolve_gmail(self):
        with patch.dict("os.environ", {
            "EMAIL_IMAP_GMAIL_HOST": "imap.gmail.com",
            "EMAIL_IMAP_GMAIL_PORT": "993",
            "EMAIL_IMAP_GMAIL_USERNAME": "person@example.com",
            "EMAIL_IMAP_GMAIL_PASSWORD": "app-password",
        }, clear=True):
            self.assertEqual(
                module.resolve_credentials("gmail"),
                ("imap.gmail.com", 993, "person@example.com", "app-password"),
            )

    def test_legacy_plow_email_variables_remain_compatible(self):
        with patch.dict("os.environ", {
            "PLOW_IMAP_ICLOUD_USERNAME": "person@icloud.com",
            "PLOW_IMAP_ICLOUD_PASSWORD": "legacy-app-password",
        }, clear=True):
            self.assertEqual(
                module.resolve_credentials("icloud"),
                ("imap.mail.me.com", 993, "person@icloud.com", "legacy-app-password"),
            )

    def test_parser_exposes_safe_read_and_organization_operations(self):
        parser = module.parser()
        self.assertEqual(parser.parse_args(["mailboxes"]).command, "mailboxes")
        self.assertEqual(parser.parse_args(["list", "--unread"]).command, "list")
        self.assertEqual(parser.parse_args(["fetch", "--uid", "42"]).command, "fetch")
        self.assertEqual(parser.parse_args(["move", "--destination", "Work", "--uid", "42"]).command, "move")
        self.assertEqual(parser.parse_args(["flag", "--uid", "42", "--flag", "Flagged"]).command, "flag")
        self.assertEqual(parser.parse_args(["accounts"]).command, "accounts")
        self.assertEqual(parser.parse_args(["list", "--account", "gmail"]).account, "gmail")
        self.assertEqual(parser.parse_args(["mailboxes", "--account", "icloud"]).account, "icloud")


if __name__ == "__main__":
    unittest.main()
