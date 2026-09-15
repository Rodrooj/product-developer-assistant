import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / "image/seed/skills/productivity/automation/SKILL.md"
WAKE = ROOT / "image/seed/skills/productivity/automation/macos/automation-wake.sh"
PLIST = ROOT / "image/seed/skills/productivity/automation/macos/com.plow.product-assistant.automation-wake.plist"
INSTALL = ROOT / "image/seed/skills/productivity/automation/macos/install-launchagent.sh"


class AutomationSkillTests(unittest.TestCase):
    def test_skill_documents_composition_and_sleep_recovery(self):
        text = SKILL.read_text()
        for required in (
            "cronjob",
            "skill-backed",
            "launchd",
            "caffeinate",
            "Latch",
            "overdue",
            "do not fabricate success",
        ):
            self.assertIn(required, text)

    def test_wake_bridge_is_single_tick_and_uses_caffeinate(self):
        text = WAKE.read_text()
        self.assertIn('caffeinate -i -w $$', text)
        self.assertIn('"$HERMES_BIN" cron tick', text)
        self.assertIn("mkdir \"$LOCK_DIR\"", text)
        self.assertNotIn("cron run", text)

    def test_launchagent_is_per_user_and_not_permanently_awake(self):
        text = PLIST.read_text()
        self.assertIn("com.plow.product-assistant.automation-wake", text)
        self.assertIn("<key>RunAtLoad</key>", text)
        self.assertIn("<key>StartInterval</key>", text)
        self.assertIn("<integer>60</integer>", text)
        self.assertNotIn("KeepAlive", text)

    def test_installer_uses_gui_user_domain(self):
        text = INSTALL.read_text()
        self.assertIn('launchctl bootstrap "gui/$(id -u)"', text)
        self.assertIn('launchctl print "gui/$(id -u)/$LABEL"', text)
        self.assertIn("__AUTOMATION_WAKE_SCRIPT__", text)


if __name__ == "__main__":
    unittest.main()
