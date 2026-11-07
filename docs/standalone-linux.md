# Standalone Linux deployment

This is a second distribution of Product Developer Assistant. It does not replace the existing Plow image, Dockerfile, Compose project, or Plow initialization path.

## Architecture

- Hermes Agent is the runtime, tool orchestrator, memory store, skill loader, and scheduler.
- Ollama serves a local model through its OpenAI-compatible API. The default model tag is qwen3:4b; it can be changed through LOCAL_MODEL.
- FoxMCP is compiled from the operator's private FoxMCP checkout and launched by Hermes over MCP stdio. It supplies the Chromium browser and Browser Knowledge Graph tools.
- The official Figma MCP remains a separate OAuth-connected service.
- GitHub operations use gh and git inside the Hermes container.
- Email uses the IMAP bridge; both EMAIL_IMAP_* and legacy PLOW_IMAP_* variables are accepted.
- Document and file operations are Linux-local and limited to the explicitly mounted /workspace directory.

## Skill parity and platform boundaries

| Skill | Standalone implementation | Boundary |
|---|---|---|
| Web Research | FoxMCP Chromium browser; extraction and BKG tools | Read/navigation-only MCP allowlist. Clicking and form submission are not exposed. |
| Document Reviewer | DOCX, ODT, PDF, and PowerPoint inspection/editing libraries | Apple Pages is not supported in Linux. Export a copy to DOCX/PDF or use the original Plow/macOS deployment. |
| Figma Organizer | Official Figma MCP with Hermes OAuth | Re-authenticate with the standalone Hermes data volume. |
| GitHub Ops | gh CLI and git in the container | Supply a least-privilege GH_TOKEN/GITHUB_TOKEN. |
| Email Reader | IMAP bridge for Gmail, iCloud, Outlook configuration | Outlook is configured in the bridge but remains functionally unverified; provider policy/app passwords still apply. |
| File Organization | Local filesystem tools within /workspace | Only files deliberately copied/mounted into standalone-workspace are in scope; the user's home directory is not mounted. |
| Automation | Hermes Cron | macOS LaunchAgent/caffeinate assets are retained for Plow but are not installed or used in Linux. |

The skill files remain shared and versioned in image/seed/skills/productivity. The standalone seed deliberately omits the Plow connector skill because no Plow MCP is configured in this runtime.

## Prerequisites

- Docker Engine and Docker Compose v2.17+ (the Compose file uses additional build contexts).
- The private Rodrooj/FoxMCP repository checked out locally. The build reads its Cargo workspace; it does not fetch private source from GitHub.
- At least 10 GiB free disk before building the standalone image (the startup script enforces this), and at least 6 GiB free before pulling the default local model. More space is recommended for image layers, model files, and persistent conversations.
- RAM appropriate for the chosen model and context size. The current Oracle Ampere host has 2 Neoverse-N1 vCPUs and 23 GiB RAM, so it is CPU-limited even if a small quantized model fits in memory.

## First-time setup

1. Clone this repository beside the private FoxMCP checkout, or set FOX_MCP_SOURCE_PATH to the absolute path of that checkout in .env.standalone.
2. Run scripts/standalone-init.sh. It creates .env.standalone, standalone-data, and standalone-workspace and copies the initial config, persona, and seven skills into the persistent data directory.
3. Review .env.standalone. Set FOX_MCP_SOURCE_PATH, LOCAL_MODEL, GH_TOKEN, and any email credentials. Do not commit this file.
4. Run scripts/check-foxmcp-source.sh to verify that the FoxMCP build context is present.
5. Ensure the host has at least 10 GiB free, then run scripts/standalone-up.sh to build the FoxMCP stdio server into the standalone Hermes image and start Hermes + Ollama. The script refuses to build on a nearly full disk.
6. Run scripts/pull-standalone-model.sh to download the model. The script refuses to pull while less than 6 GiB is free.
7. Authenticate Figma once, if needed:
   docker compose --env-file .env.standalone -f compose.standalone.yml exec agent hermes mcp auth figma
8. Inspect the services and installed models with scripts/standalone-status.sh.

The Hermes OpenAI-compatible API is enabled with a generated API key and is bound to 127.0.0.1:8642 on the host by default. The dashboard is not enabled. Use an SSH tunnel or deliberately configure a reverse proxy; do not publish the port directly to the public Internet. The local API key is stored in the ignored, mode-0600 .env.standalone file.

## Model and context requirements

Hermes currently requires a context window of at least 64,000 tokens for agentic tool use. The Compose file configures Ollama with OLLAMA_CONTEXT_LENGTH=65536 and the Hermes model with context_length=65536. After pulling the model, verify the effective context with ollama ps. If the loaded model reports less than 64K, do not treat the deployment as ready.

Qwen 3 is included as the default because Ollama documents tool-calling support for Qwen 3. The default 4B size is a resource-conscious starting point, not a quality match for Claude Sonnet. On a 2-vCPU server, inference and long-context responses can be slow. For better quality, point OLLAMA_BASE_URL at another Ollama host with stronger CPU/GPU resources and select a model that supports tool calls and at least 64K context.

## FoxMCP integration and safety

The current FoxMCP project is a stdio MCP server. Hermes starts /usr/local/bin/foxmcp-server as a child process; there is no HTTP URL or public FoxMCP port to expose.

The standalone build applies a small downstream security patch to the FoxMCP source before compiling it. It elevates non-HTTP(S) schemes, loopback, link-local, private IPv4/IPv6 targets, Docker host aliases, and common internal hostnames to Critical risk. The compose environment also sets FOXMCP_AUTO_APPROVE=0, so high/critical actions are denied when no interactive authorization channel is available. The Hermes MCP allowlist omits dom.click and dom.fill.

Important limitations:
- The patch checks the explicit URL passed to browser.open. It does not provide a complete egress proxy and cannot guarantee protection against DNS rebinding or a public page redirecting the browser to an internal address.
- FoxMCP's current main process does not load foxmcp.toml, so its allowed_domains setting must not be mistaken for an enforced policy in this integration.
- Before exposing this agent to untrusted users or arbitrary automated browsing, add a network egress proxy/firewall that blocks private, loopback, link-local, and metadata destinations after DNS resolution and across redirects. Do not treat this initial integration as a complete SSRF boundary.
- High-risk actions are denied rather than interactively confirmed. The current headless FoxMCP authorizer has no authenticated user approval UI connected to Hermes.

## Updating and rollback

The Plow deployment remains on the existing compose.yml and Dockerfile. Start it exactly as before.

For the standalone deployment, back up standalone-data before upgrading the image. The data directory contains the Hermes config, memory, sessions, OAuth state, and installed skill copies. Changing the image does not delete these files. If an upgrade changes the upstream Hermes schema, review the migration and keep the timestamped backups generated by the upstream image.

To return to Plow, stop the standalone Compose project and use the original Plow compose.yml. The two deployments use separate data stores and do not share session or OAuth state.
