from pathlib import Path
import unittest
import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.standalone.yaml"
COMPOSE = ROOT / "compose.standalone.yml"
DOCKERFILE = ROOT / "Dockerfile.standalone"
ENV_EXAMPLE = ROOT / ".env.standalone.example"
SOUL = ROOT / "SOUL.standalone.md"
PATCH = ROOT / "integrations/foxmcp/deny-private-browser-targets.patch"


class StandaloneDeploymentTests(unittest.TestCase):
    def test_uses_openai_compatible_local_model_with_64k_context(self):
        config = yaml.safe_load(CONFIG.read_text())
        self.assertEqual(config["model"]["provider"], "custom")
        self.assertIn("ollama:11434/v1", config["model"]["base_url"])
        self.assertGreaterEqual(config["model"]["context_length"], 64000)

    def test_foxmcp_is_stdio_read_oriented_and_fails_closed(self):
        config = yaml.safe_load(CONFIG.read_text())
        fox = config["mcp_servers"]["foxmcp"]
        self.assertEqual(fox["command"], "/usr/local/bin/foxmcp-server")
        self.assertTrue(fox["enabled"])
        self.assertEqual(fox["trust"], "untrusted")
        self.assertEqual(fox["env"]["FOXMCP_AUTO_APPROVE"], "0")
        self.assertEqual(fox["env"]["CHROME"], "/usr/bin/chromium")
        tools = set(fox["tools"]["include"])
        self.assertIn("browser.open", tools)
        self.assertIn("extract.text", tools)
        self.assertNotIn("dom.click", tools)
        self.assertNotIn("dom.fill", tools)
        compose = yaml.safe_load(COMPOSE.read_text())
        self.assertEqual(compose["services"]["agent"]["environment"]["FOXMCP_AUTO_APPROVE"], "0")
        self.assertEqual(compose["services"]["agent"]["environment"]["API_SERVER_ENABLED"], "true")
        self.assertTrue(compose["services"]["agent"]["ports"][0].startswith("127.0.0.1:"))
        self.assertNotIn("11434", str(compose["services"]["ollama"].get("ports", [])))

    def test_figma_oauth_is_preserved(self):
        config = yaml.safe_load(CONFIG.read_text())
        figma = config["mcp_servers"]["figma"]
        self.assertEqual(figma["auth"], "oauth")
        self.assertEqual(figma["url"], "https://mcp.figma.com/mcp")
        self.assertIn("use_figma", figma["tools"]["include"])

    def test_standalone_does_not_require_plow_or_plow_chat(self):
        config = yaml.safe_load(CONFIG.read_text())
        self.assertNotIn("plow", config["mcp_servers"])
        self.assertNotIn("plow_chat", config.get("platforms", {}))
        self.assertNotIn("plow-chat-platform", str(config))
        self.assertIn("web", config["agent"]["disabled_toolsets"])

    def test_compose_does_not_mount_docker_socket_or_host_home(self):
        compose = yaml.safe_load(COMPOSE.read_text())
        agent = compose["services"]["agent"]
        mounts = agent["volumes"]
        self.assertTrue(any("/workspace" in item for item in mounts))
        self.assertFalse(any("/var/run/docker.sock" in item for item in mounts))
        self.assertFalse(any("/home/" in item for item in mounts))
        self.assertIn("127.0.0.1:", agent["ports"][0])

    def test_dockerfile_builds_foxmcp_and_preserves_official_entrypoint(self):
        text = DOCKERFILE.read_text()
        self.assertIn("FROM rust:1-bookworm AS foxmcp-builder", text)
        self.assertIn("COPY --from=foxmcp-source", text)
        self.assertIn("deny-private-browser-targets.patch", text)
        self.assertIn("cargo test --locked --package foxmcp-server test_non_public_browser_targets_are_blocked", text)
        self.assertIn("FOXMCP_AUTO_APPROVE=0", text)
        self.assertLess(text.index("ARG HERMES_BASE_IMAGE="), text.index("FROM rust:1-bookworm"))
        self.assertIn("USER root", text)  # upstream s6 init must start with its required privileges
        self.assertNotIn("USER hermes", text)
        self.assertNotIn("ENTRYPOINT", text)

    def test_standalone_assets_explain_linux_runtime_boundary(self):
        soul = SOUL.read_text()
        self.assertIn("not running on the user's Mac", soul)
        self.assertIn("/workspace", soul)
        docs = (ROOT / "docs/standalone-linux.md").read_text()
        self.assertIn("Apple Pages is not supported in Linux", docs)
        self.assertIn("DNS rebinding", docs)
        self.assertIn("private FoxMCP checkout", docs)

    def test_all_seven_productivity_skills_remain_in_source_tree(self):
        skills = ROOT / "image/seed/skills/productivity"
        expected = {
            "web-research", "document-reviewer", "figma-organizer",
            "github-ops", "email-reader", "file-organization", "automation",
        }
        actual = {p.name for p in skills.iterdir() if p.is_dir()}
        self.assertTrue(expected.issubset(actual))

    def test_standalone_skill_instructions_use_runtime_scoped_email_path(self):
        email_skill = (ROOT / "image/seed/skills/productivity/email-reader/SKILL.md").read_text()
        web_skill = (ROOT / "image/seed/skills/productivity/web-research/SKILL.md").read_text()
        init_script = (ROOT / "scripts/standalone-init.sh").read_text()
        self.assertIn("$HERMES_HOME/skills/productivity/email-reader/plow-imap.py", email_skill)
        self.assertIn("EMAIL_IMAP_* names or legacy PLOW_IMAP_* aliases", email_skill)
        self.assertIn("does not expose dom.click or dom.fill", web_skill)
        self.assertIn("plow-connectors", init_script)
        self.assertIn("Never delete a skill", init_script)

    def test_env_example_has_no_live_credentials(self):
        text = ENV_EXAMPLE.read_text()
        self.assertIn("LOCAL_MODEL=qwen3:4b", text)
        self.assertIn("OLLAMA_CONTEXT_LENGTH=65536", text)
        self.assertRegex(text, r"(?m)^GH_TOKEN=$")
        self.assertRegex(text, r"(?m)^EMAIL_IMAP_GMAIL_PASSWORD=$")

    def test_startup_script_checks_disk_space_before_build(self):
        script = (ROOT / "scripts/standalone-up.sh").read_text()
        self.assertIn("MIN_FREE_KB", script)
        self.assertIn("10 * 1024 * 1024", script)
        self.assertLess(script.index("MIN_FREE_KB"), script.index("docker compose"))

    def test_foxmcp_security_patch_contains_private_target_guards(self):
        text = PATCH.read_text()
        for token in ("127.0.0.1", "ollama", ".internal", "is_private"):
            self.assertIn(token, text)
        self.assertIn("FOXMCP_AUTO_APPROVE=0", DOCKERFILE.read_text())


if __name__ == "__main__":
    unittest.main()
