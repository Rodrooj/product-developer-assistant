from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "image/seed/skills/productivity/figma-organizer/SKILL.md"
CONFIG = ROOT / "image/seed/config.yaml"


class FigmaOrganizerSkillTests(unittest.TestCase):
    def test_skill_exists_and_declares_boundary(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("name: figma-organizer", text)
        self.assertIn("inspect -> propose -> approve -> apply -> verify", text)
        self.assertIn("organize, don't design from zero", text)
        self.assertIn("MUST NOT become the primary tool for", text)
        self.assertIn("Never delete components, variables, styles, pages, or assets", text)

    def test_skill_requires_existing_context_before_writes(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("Use `get_metadata` for structural inventory", text)
        self.assertIn("Use `get_variable_defs` when auditing variables/styles/tokens", text)
        self.assertIn("Search connected libraries before creating a component", text)
        self.assertIn("Never call `use_figma` as a substitute for inspecting the existing system first", text)

    def test_config_registers_oauth_figma_server_with_restricted_surface(self):
        text = CONFIG.read_text(encoding="utf-8")
        self.assertIn("figma:", text)
        self.assertIn('url: "https://mcp.figma.com/mcp"', text)
        self.assertIn("auth: oauth", text)
        self.assertIn("trust: untrusted", text)
        for tool in (
            "get_metadata",
            "get_variable_defs",
            "get_libraries",
            "search_design_system",
            "get_screenshot",
            "use_figma",
        ):
            self.assertIn(f"        - {tool}", text)
        self.assertNotIn("        - create_new_file", text)
        self.assertNotIn("        - generate_figma_design", text)
        self.assertNotIn("        - upload_assets", text)


if __name__ == "__main__":
    unittest.main()
