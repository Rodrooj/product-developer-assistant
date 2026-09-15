# Implementation Rationale and Source Map

## 1. Purpose and scope

This document records the **implementation rationale** used to develop the project capabilities in `Rodrooj/product-developer-assistant`: the problem each skill solves, the architectural constraints adopted, the implementation decisions, the safety boundaries, the source material used to ground those decisions, and the validation status.

It is intentionally a **decision and evidence record**, not a transcript of private model reasoning. Internal chain-of-thought is not reproduced. Instead, the document exposes the technical inputs, observable decision criteria, alternatives considered, resulting design, and known limitations so the implementation can be independently reviewed.

The document covers the following project-specific capabilities:

1. Email reading, triage, organization, and reply drafting.
2. Figma project/design-system organization through Figma MCP.
3. Local document review and revision for Apple Pages and Microsoft Word for Mac.
4. Web research, competitive benchmarking, netnography, and questionnaire/form research.
5. Git and GitHub repository operations.
6. Automation and macOS sleep/wake recovery.
7. Cross-cutting security, approval, provenance, and failure-handling principles.

---

## 2. Development method used across the skills

The common implementation pattern was:

```text
User goal
  -> identify the native capability already provided by Plow/Hermes/Latch
  -> define the smallest project-specific skill that composes that capability
  -> establish explicit boundaries and authorization rules
  -> prefer structured/native interfaces over brittle UI automation
  -> minimize data transferred to the model
  -> make consequential writes approval-gated
  -> verify state after mutations
  -> record failure/uncertainty instead of fabricating success
```

This produced skills that are intentionally **orchestration and policy layers**, rather than independent replacements for Hermes, Latch, Figma, GitHub, or macOS applications.

A recurring design criterion was: **if the underlying platform already has a reliable primitive for the operation, use that primitive rather than introducing a second implementation.** Examples include Hermes cron instead of a new scheduler database, Figma MCP instead of browser scraping, IMAP instead of webmail automation, and native macOS application automation instead of screen-coordinate clicking.

---

# 3. Email Reader and Organizer

## 3.1 Problem addressed

The goal was to allow the agent to inspect and organize the owner's mailbox while avoiding two common failure modes:

- transferring an entire mailbox into model context when only a few messages matter;
- turning a read/triage capability into an implicit outbound-mail capability.

The resulting skill is `image/seed/skills/productivity/email-reader/SKILL.md`, with the transport implementation in `plow-imap.py` and unit tests in `tests/test_plow_imap.py`.

## 3.2 Main implementation decisions

### Metadata first, body second

The client uses a two-stage retrieval model:

```text
mailboxes
  -> compact message metadata
  -> local filtering/ranking
  -> fetch only selected messages
  -> semantic analysis
```

The metadata stage contains UID, sender, recipients, subject, dates, flags, thread headers, and message size. Message bodies are fetched only for messages that require semantic inspection.

This decision reduces bandwidth and model-context consumption while preserving enough information for triage. The skill explicitly uses IMAP UIDs and `BODY.PEEK` so inspection does not unintentionally mark messages as read.

### Server-side search

Where possible, search is delegated to the IMAP server instead of downloading the mailbox and filtering it in the model. This is both an efficiency and privacy decision.

### No ordinary delete operation

The bridge deliberately does not expose a delete command. Organization can move or flag messages, but destructive deletion is outside ordinary triage.

### Approval for state changes

Reading/classification is non-destructive. Moving, archiving, flagging, or marking messages read/unread is treated as a state-changing operation and requires explicit authorization unless the user has already established standing authorization for that exact policy.

### No hidden send capability

The IMAP bridge does not implement outbound sending. The skill can draft a response, but sending must occur through an explicitly authorized send-capable mechanism. This prevents mailbox-reading credentials from becoming a hidden messaging capability.

### Prompt-injection boundary

Email bodies, signatures, forwarded messages, attachments, and subjects are treated as untrusted data. Instructions contained in a message cannot authorize secret disclosure, file access, sending mail, or configuration changes.

## 3.3 Evidence and sources

Primary project sources:

- `image/seed/skills/productivity/email-reader/SKILL.md` — defines the retrieval strategy, authorization model, thread policy, security boundary, and user-facing workflows.
- `image/seed/skills/productivity/email-reader/plow-imap.py` — implements the IMAP transport and command surface.
- `tests/test_plow_imap.py` — verifies header decoding, plain-text extraction, and the intended safe command surface.

The implementation was also grounded in the IMAP protocol model: server-side search, message UIDs, MIME structure, and non-destructive `BODY.PEEK` retrieval are used because they are native mailbox primitives rather than model-specific inventions.

## 3.4 Validation status

Unit-level tests exist for core parsing and command-surface behavior. The repository does **not** establish that a live production mailbox was connected and exercised end-to-end; therefore live IMAP interoperability should be treated as a validation item rather than a completed result.

---

# 4. Figma Project Organizer

## 4.1 Problem addressed

The objective was not to create arbitrary UI designs from prompts. It was to help maintain and organize **existing Figma projects and design systems**: naming, variables, components, variants, libraries, structure, and drift.

The implementation lives in `image/seed/skills/productivity/figma-organizer/SKILL.md`, with the Figma MCP server configured in `image/seed/config.yaml`.

## 4.2 Why Figma MCP was selected

Figma provides structured design information through MCP, including metadata, variables, libraries, design context, screenshots, design-system search, and native write operations. This makes MCP a better architectural boundary for this use case than scraping the Figma web UI.

The configured endpoint is:

```text
https://mcp.figma.com/mcp
```

Authentication is delegated to the MCP client's OAuth flow rather than asking users to paste tokens into chat or skill files.

## 4.3 Main implementation decisions

### Inspect before mutation

The workflow is:

```text
inspect -> propose -> approve -> apply -> verify
```

The skill starts with the smallest useful scope and progressively expands only when necessary.

### Structured inspection before screenshots

The preferred order is metadata/variables/libraries/design-system search first, followed by design context or screenshots when visual information is actually necessary.

This prevents the model from consuming large screenshots or complete project representations when a sparse structural representation is sufficient.

### Existing design language is authoritative

If the project already has naming conventions, token conventions, component taxonomy, accessibility rules, library ownership, or Code Connect mappings, those rules are treated as the source of truth.

When no convention exists, the skill may infer a small consistent convention, but broad normalization is still presented as a proposed change rather than silently applied.

### Organize rather than redesign

The skill explicitly excludes autonomous creation of an entire product UI from a blank file. The target is maintenance and systematization of existing material.

This boundary was chosen because organizational changes can be evidence-based from the existing project, while visual invention introduces subjective design decisions that should remain under human control.

### Deletion is not routine cleanup

Components, variables, styles, pages, and assets are not deleted during ordinary cleanup. Rename, deprecate, isolate, or report is preferred. Deletion requires explicit authorization.

### Incremental writes and post-write verification

After each meaningful write batch, the affected nodes are re-read and checked for naming collisions, broken references, inconsistent properties, unintended changes, and layout/hierarchy regressions.

## 4.4 External sources

The principal external source was Figma's official MCP documentation:

- Figma MCP introduction: urlFigma MCP Server documentationhttps://developers.figma.com/docs/figma-mcp-server/
- Figma MCP tools and prompts: urlTools and promptshttps://developers.figma.com/docs/figma-mcp-server/tools-and-prompts/
- Remote MCP setup/OAuth: urlRemote server installationhttps://developers.figma.com/docs/figma-mcp-server/remote-server-installation/
- Write-to-canvas guidance: urlWrite to canvashttps://developers.figma.com/docs/figma-mcp-server/write-to-canvas/
- Figma guidance on custom rules and inspect-before-write workflows: urlCustom ruleshttps://developers.figma.com/docs/figma-mcp-server/add-custom-rules/

These sources directly support the use of `get_metadata`, `get_variable_defs`, `get_libraries`, `search_design_system`, `get_design_context`, `get_screenshot`, and `use_figma`, as well as the recommendation to inspect existing content before applying writes. citeturn1search0turn1search6

## 4.5 Validation status

The repository configuration and skill workflow are implemented. A live OAuth connection to a real Figma file was **not** established during this implementation cycle, so real-file authorization and end-to-end mutation should remain explicit validation work.

---

# 5. Local Document Reviewer

## 5.1 Problem addressed

The objective was to make the agent useful for reviewing and revising documents already stored on the user's Mac while preserving the native document structure and formatting.

The implementation lives in `image/seed/skills/productivity/document-reviewer/SKILL.md`.

## 5.2 Main implementation decisions

### Native applications first

Apple Pages is treated as a first-class path through Latch's existing macOS AppleScript capabilities.

Microsoft Word for Mac is supported through its native macOS automation interfaces when available. AppleScript is preferred; Word VBA/Office automation is a fallback only when the requested operation cannot be safely expressed through the native AppleScript path.

### Why not generate a new document

Rebuilding a document from extracted text would risk losing styles, tables, pagination, headers/footers, citations, comments, tracked changes, fields, and other rich-document structures. Therefore the skill is explicitly an editing/review workflow rather than a document-generation workflow.

### Inspect before rewrite

The workflow is:

```text
locate -> inspect -> establish requirements -> propose -> approve -> revise -> verify
```

The skill first determines the exact file, application, document type, structure, and requested review criteria.

### Separate facts from editorial decisions

During review, the skill distinguishes document-supported facts, editorial observations, proposed wording, and uncertainties. This prevents stylistic polishing from silently becoming factual invention.

### Preserve formatting and structure

The implementation explicitly preserves headings, lists, tables, styles, links, citations, numbering, page breaks, headers/footers, and other relevant structures whenever the native interface permits it.

### No destructive fallback

If Word/Pages automation is unavailable or permissions are denied, the skill reports the limitation instead of claiming success or silently flattening the document into plain text.

## 5.3 External sources

The implementation uses the native macOS automation model exposed by Latch and Apple's Pages application model. For Word, Microsoft documentation was used to establish that Office for Mac supports its object model/VBA automation and that Word for Mac is a supported Office automation target.

- Microsoft Office for Mac automation/VBA: urlOffice for Mac VBA documentationhttps://learn.microsoft.com/en-us/office/vba/api/overview/office-mac
- Microsoft Word VBA reference: urlWord VBA referencehttps://learn.microsoft.com/en-us/office/vba/api/overview/word

The project skill itself is the more specific source for the final policy: it deliberately prefers direct native macOS automation and does not require embedding VBA into user documents. fileciteturn117file0

## 5.4 Validation status

The skill and workflow are implemented, but no live Mac execution against both Pages and Word was recorded as a completed end-to-end validation. App-specific AppleScript behavior should therefore be validated on the target Mac before relying on broad document mutations.

---

# 6. Web Research and Market Intelligence

## 6.1 Problem addressed

The goal was to turn generic web browsing into a reproducible research workflow for market research, competitive benchmarking, netnography, and questionnaires/forms.

The implementation lives in `image/seed/skills/productivity/web-research/SKILL.md`.

## 6.2 Main implementation decisions

### Research is an evidence workflow, not just browsing

The core pipeline is:

```text
research question
  -> scope
  -> plan
  -> search
  -> evidence
  -> synthesis
  -> dossier
  -> validation
```

### Native Latch browsing

The skill extends Latch's existing internet-navigation capability instead of introducing a second browser stack. This keeps browser interaction within the same local execution boundary used by the rest of the product.

### Primary sources first

Official product/pricing pages, original studies, public filings, platform documentation, first-party research, and direct community material are preferred when they directly answer the question. Secondary sources are used for context and triangulation.

### Observation versus interpretation

Every material finding is separated into factual observation and interpretation. This was important for market and netnographic research because several sources repeating similar language do not automatically constitute independent evidence.

### Source registry

Substantial research produces an auditable local Markdown dossier with source IDs, URLs, retrieval dates, publication dates when available, methodology, findings, limitations, contradictions, and validation status.

The preferred output path is:

```text
research/<YYYY-MM-DD>-<short-topic>-research.md
```

### Missing information is represented explicitly

The skill uses `Not found`, `Not disclosed`, or `Requires verification` rather than filling gaps with assumptions.

### No arbitrary competitive winner

Benchmarking is organized around documented dimensions selected for the research task. The skill does not collapse the evidence into an arbitrary score or winner.

### Netnography is treated as a methodology

Online-community research includes population/context, community selection, observation period, corpus criteria, privacy minimization, separation of observation and interpretation, and preservation of contradictory signals. It is not treated as casually reading social media.

## 6.3 Sources

The primary implementation source is the project skill itself: `image/seed/skills/productivity/web-research/SKILL.md`. Its methodological decisions are based on established research practices around source provenance, triangulation, qualitative observation, questionnaire construction, and reproducibility.

Where the skill invokes named methodological work such as Kozinets' netnography research, the implementation treats that as a methodological reference rather than as evidence for a particular market claim. The actual market claim must still be supported by the sources collected during the research run.

## 6.4 Validation status

The workflow and dossier schema are implemented. A complete live end-to-end browser research session through Latch was not recorded as a completed validation during this implementation cycle. Therefore the skill should not claim that a browser source was inspected unless the corresponding Latch operation actually succeeds.

---

# 7. Git and GitHub Repository Operations

## 7.1 Problem addressed

The objective was to give the assistant a repository-operations role without turning it into the project's primary software-development agent.

The implementation lives in `image/seed/skills/productivity/github-ops/SKILL.md`.

## 7.2 Main implementation decisions

### Broad repository awareness

The skill covers local Git state and GitHub operational state: repositories, branches, commits, issues, pull requests, reviews, Actions, releases, tags, discussions, projects, labels, checks, deployments, and governance signals when exposed by the installed tooling.

### Repository resolution before action

The skill resolves repositories in this order:

1. explicit `OWNER/REPO`;
2. current local Git remote;
3. explicitly selected repository context;
4. unambiguous search.

If multiple repositories plausibly match, it asks rather than guessing.

### Read-before-write

The standard operational lifecycle is:

```text
inspect -> identify candidates -> propose changes -> authorize -> apply -> verify
```

This prevents a status request from accidentally becoming a mutation request.

### Status queries are evidence-based

Relative time expressions such as "since yesterday afternoon" are converted into explicit intervals. Local Git history and remote GitHub history are kept distinct so unpushed commits are not reported as if they already exist on GitHub.

### Maintenance is reversible by default

The skill prefers labels, context, identification of stale candidates, and other metadata-oriented actions over deletion. A stale branch is reported as a cleanup candidate rather than automatically deleted.

### Explicit boundary against code generation

The skill does not become the coding agent simply because it can see source files. It does not automatically implement features, create commits, push branches, merge pull requests, or modify source code as part of routine repository organization.

## 7.3 Sources

Primary project source:

- `image/seed/skills/productivity/github-ops/SKILL.md`.

The operational model follows the documented Git and GitHub CLI/API primitives, especially structured `git status`, Git history, `gh issue`, `gh pr`, `gh workflow`, `gh run`, and `gh api` workflows.

The important architectural choice is not to duplicate GitHub's API in the skill: the skill describes how to select and sequence existing Git/GitHub operations safely.

## 7.4 Validation status

The skill is implemented in the repository. Live execution through a Latch Mac environment has not been recorded as an end-to-end validation of every GitHub operation, so support for any individual `gh` command remains dependent on the installed CLI version, authentication, and repository permissions.

---

# 8. Automation and macOS sleep/wake recovery

## 8.1 Problem addressed

The automation capability needed to convert natural-language requests into durable scheduled work while respecting the fact that Latch depends on a Mac that can be awake.

The implementation lives in `image/seed/skills/productivity/automation/SKILL.md` and the accompanying `macos/` LaunchAgent assets.

## 8.2 Main implementation decision: Hermes remains the scheduler

Hermes already provides the `cronjob` tool and `hermes cron` CLI for one-shot and recurring jobs, skill attachment, lifecycle management, and scheduler state. The project therefore does **not** introduce a second schedule database.

The architecture is:

```text
User request
   -> automation skill
   -> Hermes cron job
   -> attached skill(s)
   -> Plow/Latch/native capability
```

Hermes documentation confirms that cron jobs can be one-shot or recurring and can attach one or more skills. citeturn0search0turn0search5

## 8.3 Sleep/wake bridge

The problem is that Latch cannot execute desktop operations while macOS is asleep. The solution separates **schedule ownership** from **wake recovery**:

```text
macOS sleeps
    |
    v
scheduled time passes
    |
    v
macOS wakes / user session loads
    |
    v
launchd LaunchAgent
    |
    v
hermes cron tick
    |
    v
Hermes determines which jobs are due
    |
    v
job executes with its normal skill/tool policy
```

The LaunchAgent does not own job state. It only asks Hermes to reconsider due jobs. This preserves Hermes as the single source of truth.

## 8.4 Idempotent wake semantics

The bridge performs a single scheduler tick rather than attempting to replay every missed minute. This prevents the recovery layer from creating duplicate executions and leaves repeat semantics to Hermes itself.

Hermes' own documentation describes a scheduler tick that evaluates due jobs and starts fresh sessions for them. citeturn0search0turn0search4

## 8.5 Bounded sleep inhibition

The bridge uses:

```text
caffeinate -i -w <dispatcher-pid>
```

The intent is only to inhibit idle sleep while the recovery dispatcher is alive. It is not a permanent anti-sleep process.

An important limitation is preserved in the skill: `caffeinate` does not solve every hardware-driven sleep condition, such as a MacBook lid being closed. Therefore unattended execution with a closed lid requires appropriate macOS power configuration or a different machine/setup.

## 8.6 Security decision

Scheduling an action does not automatically authorize high-impact side effects. Payments, account changes, destructive file operations, external messages, or other consequential actions remain approval-gated unless the user has explicitly established an appropriate standing authorization.

Scheduled prompts, local files, email content, web content, repository content, and tool output are all treated as untrusted data. They cannot silently redefine the automation's permissions or schedule.

## 8.7 Sources

Primary implementation sources:

- `image/seed/skills/productivity/automation/SKILL.md`.
- `macos/com.plow.product-assistant.automation-wake.plist`.
- `macos/automation-wake.sh`.
- `macos/install-launchagent.sh`.
- `macos/uninstall-launchagent.sh`.

External source:

- Hermes scheduled-task documentation: urlHermes Cron documentationhttps://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md
- Hermes CLI reference: urlHermes CLI cron referencehttps://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/cli-commands.md

The Hermes documentation explicitly describes the unified `cronjob` interface, skill-backed jobs, lifecycle operations, and scheduler tick behavior. citeturn0search0turn0search2

## 8.8 Validation status

The automation assets and skill are implemented. A real macOS sleep/wake cycle with an actual scheduled job has **not** been recorded as a completed end-to-end validation. In particular, the following should be tested on the target Mac:

- LaunchAgent installation/loading;
- wake-triggered `hermes cron tick`;
- behavior when a job becomes due while asleep;
- concurrent dispatcher protection;
- bounded `caffeinate` behavior;
- actual Latch availability after wake;
- Hermes-reported job outcome.

---

# 9. Cross-cutting security and reliability model

The skills were designed around the same trust model.

## 9.1 External content is data, not authority

Email, Figma text, documents, websites, repository files, issue descriptions, commit messages, and scheduled-job inputs can contain instructions. Those instructions are treated as untrusted content and cannot override the skill's authorization policy.

## 9.2 Credentials stay outside prompts and skill text

Credentials are expected to come from the runtime's protected credential mechanisms. The skills do not ask users to paste passwords, OAuth tokens, API keys, or session cookies into prompts.

The project's base configuration also follows a credential-free/tenant-free image model: tenant-specific identity and credentials are injected at runtime rather than baked into the seed configuration. The existing `image/seed/config.yaml` explicitly documents this invariant and configures the Figma MCP server for OAuth rather than embedding a token. fileciteturn122file0

## 9.3 State-changing operations require stronger authorization

A recurring distinction is:

```text
read/analyze
    !=
modify/delete/send/publish
```

Consequential writes require explicit authorization or an already-established standing authorization for the same class of operation.

## 9.4 Verify after mutation

Every state-changing skill contains a post-write verification step whenever the underlying platform supports one. A tool returning without an exception is not treated as proof that the requested state was achieved.

## 9.5 Failure is an observable state

If a browser, Figma MCP, GitHub CLI, Word/Pages automation, IMAP server, Latch bridge, or scheduler is unavailable, the expected behavior is to report the limitation rather than substitute invented state.

This principle is especially important for an agent whose output may be used as a project-management or productivity record.

---

# 10. Architectural source map

| Area | Repository source | External/underlying source | Main decision supported |
|---|---|---|---|
| Base runtime | `README.md`, `image/seed/config.yaml` | Hermes Agent / Plow architecture | Reuse the existing agent/runtime boundary |
| Email | `email-reader/SKILL.md`, `plow-imap.py` | IMAP protocol primitives | Metadata-first retrieval, UID-based precise fetch, no hidden send |
| Figma | `figma-organizer/SKILL.md`, `config.yaml` | Figma MCP docs | Structured inspect/propose/apply workflow |
| Documents | `document-reviewer/SKILL.md` | macOS native automation, Microsoft Office for Mac docs | Preserve rich documents and prefer native automation |
| Web research | `web-research/SKILL.md` | Research-methodology principles | Evidence registry, triangulation, observation/interpretation separation |
| GitHub | `github-ops/SKILL.md` | Git/GitHub CLI/API model | Repository operations without silently becoming a coding agent |
| Automation | `automation/SKILL.md`, `macos/*` | Hermes cron docs, macOS scheduling primitives | One scheduler + wake/recovery bridge |

---

# 11. What is implemented versus what is still an assumption

The distinction below is important for independent validation.

### Implemented in the repository

- Skill specifications for all six capabilities.
- Email IMAP bridge and unit tests.
- Figma MCP configuration and OAuth-oriented connection model.
- Pages/Word native-automation workflow specification.
- Research dossier and source-registry specification.
- Git/GitHub operations workflow specification.
- Hermes-based automation workflow.
- macOS LaunchAgent wake/recovery assets.
- Cross-cutting approval, security, and failure-handling policies.

### Not established by this document as a completed live validation

- Successful live IMAP connection to a real mailbox.
- Successful live Figma OAuth connection and mutation of a real Figma file.
- Successful end-to-end Pages automation on a real document.
- Successful end-to-end Word automation on a real document.
- Successful Latch-driven web research session producing and validating a live dossier.
- Successful end-to-end GitHub CLI operations from the target Latch environment.
- Successful real macOS sleep/wake automation cycle.

These are intentionally left as validation tasks rather than being presented as test results.

---

# 12. Recommended validation matrix

| Capability | Minimum validation | Evidence to retain |
|---|---|---|
| Email | Connect to a test mailbox; list metadata; fetch one UID; move/flag with explicit approval | command output + resulting mailbox state |
| Figma | OAuth; inspect metadata/variables; perform one approved rename; re-read node | before/after node metadata |
| Pages | Open a copy; make a small correction; save; reopen | document before/after + application state |
| Word | Same as Pages using `.docx` | document before/after + application state |
| Web research | Run a small benchmark and create dossier | dossier + source registry + rechecked URLs |
| GitHub | Inspect repo, issues, PRs and Actions; perform one authorized metadata change | before/after GitHub state |
| Automation | Schedule one job; sleep Mac; wake; inspect run result | Hermes job state + LaunchAgent logs |

---

# 13. Final implementation principle

The project is deliberately structured as a **local productivity agent composed from existing platform capabilities** rather than as a monolithic autonomous system.

The main implementation choices can therefore be summarized as:

1. **Compose instead of duplicate.** Use Hermes, Latch, Figma MCP, IMAP, Git/GitHub, and native macOS automation where they already provide the primitive required.
2. **Inspect before changing.** Establish the current state and source of truth before proposing mutations.
3. **Use the smallest sufficient context.** Retrieve only the data needed for the decision.
4. **Keep human authority over consequential changes.** Reading and analysis can be broad; writes, deletion, sending, publishing, and external side effects are more restrictive.
5. **Verify actual state.** A successful tool invocation is not equivalent to a successful business outcome.
6. **Preserve provenance.** Research and operational claims should remain traceable to their source or observed state.
7. **Expose uncertainty.** Missing validation, unavailable integrations, ambiguous evidence, and partial failures remain visible.

This is the basis on which each current skill was designed and is the intended standard for future skills added to the project.
