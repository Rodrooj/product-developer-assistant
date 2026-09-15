# Plow × Hermes Hackathon — Compliance

This document tracks the repository's readiness for the Plow × Hermes hackathon. It distinguishes requirements confirmed by the supplied kickoff/CBl materials from items that still require an external action or validation.

## Competition requirements confirmed from the supplied materials

- Build an agent on the Plow ecosystem and demonstrate a real, useful workflow.
- Use Plow Latch as the local execution layer and Plow Chat/iMessage as the user-facing interaction path.
- Build on Hermes Agent.
- Publish the agent as open source on GitHub.
- Register/publish the agent through the AI Worth Using Agent Index so installs and token usage can be measured.
- Run the Agent Index usage reporter/client on the agent; the kickoff explicitly states that a Python script is used to communicate usage back to the API.
- Provide a working demonstration using the real agent. The supplied research notes the requirement for a functional public repository and a demonstration rather than mockups.
- Competition ranking is driven by real installs and token usage during the specified usage window; the top 10 proceed to human judging.

## Repository status

| Requirement | Status | Evidence / next action |
|---|---|---|
| Hermes-based agent | PASS | Repository is a Plow/Hermes base image and boots Hermes through s6-overlay. |
| Plow integration | PASS | The image already contains the Plow initialization path and Plow credential handling. |
| Plow Chat/iMessage path | PASS | The repository is explicitly designed as a hosted Plow agent reachable through Plow Chat. |
| Open-source license | PASS | `LICENSE` is now MIT. |
| Public GitHub repository | BLOCKED | The GitHub repository is currently private. Change repository visibility to public before submission. |
| Agent Index registration | TODO | Register this specific agent and obtain its Agent Index ID. |
| Agent Index usage reporter/client | TODO | Add the required Python reporter/client and configure it with the registered Agent Index ID. |
| Real user workflow | TODO | Implement the product-developer workflow derived from the CBL research; do not submit the base image alone as the finished agent. |
| Working end-to-end demonstration | TODO | Run the finished agent through Plow Latch + Plow Chat/iMessage and record the required demonstration. |
| Usage-window participation | TODO | Dogfood with real users and accumulate installs/token usage during the official counting window. |

## Product direction from the CBL research

The research identifies the target audience as product-development professionals and adjacent roles. The refined challenge is:

> Use Plow Latch to help professional product developers automate heavy and repetitive work processes, giving them more useful working time.

The research collected demand for file/folder organization, app deployment, email organization/summarization, Figma organization, document rewriting/reviewing, simulator/container cleanup, and user-defined automations. It also identifies code assistance, research/netnography, and Figma support as promising directions.

For the hackathon implementation, the repository should converge on one concrete workflow first. The supplied research explicitly warns that broad integrations such as universal email, Figma API/MCP, and App Store deployment can become too complex for a short hackathon.

## Security and release checks

- Never commit `plow-credentials`, API keys, session state, or `.env` files.
- Keep the existing fail-closed Plow initialization behavior intact.
- Do not claim Agent Index registration or measured usage until it has actually been completed.
- Do not claim the repository is submission-ready while its visibility remains private.

## Source basis

This checklist is based on the supplied `CBL_Hackathon.pdf`, the supplied `Plow Hackathon Kickoff` transcript, and the existing repository implementation. The kickoff states that the Agent Index is intended to contain real examples of agents, that ranking is based on installs and token usage, and that a Python script is required on the agent to report usage. The CBL identifies Plow Latch + Hermes as the intended solution path and the product-development automation challenge.
