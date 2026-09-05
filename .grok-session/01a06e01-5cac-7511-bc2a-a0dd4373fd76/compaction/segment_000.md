# HISTORICAL -- DO NOT EDIT
# Record of compaction segment 000 (detail=verbose) from this same task.
# Use read_file or grep to look up details, but do not modify.

## Segment metadata
- Index: 000
- Turn count: 394
- Timestamp: 2026-09-04T21:17:29Z

## Turn statistics

- Turns: 394 (Assistant=116, Function=262, Human=15, System=1)
- Tools used: search_replace (140), read_file (81), run_terminal_command (17), grep (8), web_fetch (7), list_dir (4), todo_write (4), get_command_or_subagent_output (1)
- Unique target files (45): C:\Users\elzoy\.grok\docs\user-guide, C:\Users\elzoy\.grok\docs\user-guide\01-getting-started.md, C:\Users\elzoy\.grok\docs\user-guide\03-keyboard-shortcuts.md, C:\Users\elzoy\.grok\docs\user-guide\04-slash-commands.md, C:\Users\elzoy\.grok\docs\user-guide\21-terminal-support.md, ... and 40 more
- Tool errors: 0
- Verbose-render size estimate: 1,286,328 B
- Last assistant response excerpt: "Voy a atrapar Ctrl-C y el resto de fallos: mensaje claro y cierre de la sesión, sin dejar el prompt colgado."


## Summary (curated by compaction step)

Summary:
1. Primary Request and Intent: The user originally asked to replicate Nokia NFM-P / NSP Classic Management 24.11 as a web MPLS NMS, then iteratively narrowed scope. They provided Nokia docs (User Guide, Admin Guide, Statistics Guide, XML API Developer Guide), the live REST catalog at C:\Users\elzoy\OneDrive\Documents\Code\nsp-2411-api\nsp-2411-api\data\nsp-catalog.json, and the public library https://documentation.nokia.com/nsp/24-11/libfiles/libcontents.html (saved as docs/REFERENCES.md). They rejected a Java-GUI replica and asked for a Python CLI: login, stay in a shell, Grok 4.6-like feel. Then they asked for navigation like a network-equipment console showing usuario@IP_NSP, nested enter like Python Fire / SR OS; they asked if Fire is useful and what Grok Build 4.6 uses. Product constraints that still apply: customers (subscr.Subscriber) first; then only VPRN/VPLS/Epipe; detail plus related objects; first instance read-only (no service create). Workspace is C:\Users\elzoy\Code\nsp-grok-2411 (distinct from their existing nsp-2411-api CLI). Default demo users admin/operator/noc/viewer, password Nokia1234!. Live NSP IPs from catalog: 172.24.80.28:443 (NSP) and 172.24.80.21:8443 (NFM-P REST).

How to run (user asked after PowerShell blocked Activate.ps1): do not use Activate.ps1; call `.\.venv\Scripts\python.exe -m nsp_grok --host 172.24.80.28`. Optional CurrentUser RemoteSigned is not required.

Later the user asked whether the program already generates HTTP requests to the server, and to add `--debug` that prints each request. They then asked to set the HTTP client timeout to 60s when fetching from the server. Latest explicit request (in progress, unfinished): add exception handling so Ctrl-C and other failures show an appropriate message and close the program.

2. Key Technical Concepts: NSP/NFM-P 24.11; subscr.Subscriber DN subscriber:<id>; services filtered by subscriberPointer; classes vprn.Vprn, vpls.Vpls, epipe.Epipe; related sites (svc-mgr:service-<id>:<ip>), SAPs, SDP bindings, svt tunnels, LSPs, fm alarms; VPRN RT/static/BGP; VPLS mac-table. Dual APIs: NSP Supervision GETs vs NFM-P samo_*/generic find. Auth OAuth2 POST https://{host}/rest-gateway/rest/api/v1/auth/token with grant_type client_credentials and Basic user:pass. Live finds POST https://{host}/nfmpv3service/api/v3/find (XML body parse; XMLException in 200). TLS verify=False for lab certs. CLI stack: Python 3.11+, prompt_toolkit + rich + requests; do not add the fire package. Fire-style walk of child names; SR OS-like prompt user@host>ctx>ctx>. Grok 4.6 is a custom TUI (prompt below, slash commands, status line) — not Fire. DEFAULT_NSP_HOST = 172.24.80.28. REQUEST_TIMEOUT_S = 60, applied as timeout=(60, 60) connect+read. Span of control, UAC, password policy (≥10 chars), lockout after 5 failures. --debug prints method/URL/redacted headers/JSON body plus HTTP status; debug on|off in-shell. --offline forces lab without HTTP. If live login fails, fall back to lab local.

3. Errors and Fixes: Developer portal SSO blocked; used public docs + user PDFs. Nokia123! failed policy (9 chars) → Nokia1234!. test_password_policy failed then passed. PowerShell quoting broke inline JSON scan → temp scripts then deleted. VPRN 100 ls saps showed 1 SAP because keys were only SAP name 1/1/10:100; keys now include site_id. PowerShell: `.\.venv\Scripts\Activate.ps1` failed with PSSecurityException UnauthorizedAccess (execution policy); workaround is run venv python.exe directly. A search_replace on nsp_grok/app.py _connect_nsp left a syntax-broken `except NspApiError as cop:` with no body (later filled). A later search_replace for `_customer` NspApiError quit handling did not apply because the string was not found (except is still `return Outcome(error=str(exc))` without quit=True). UserCancelled class was added to nsp_api.py; KeyboardInterrupt in _send was added.

4. Problem Solving: Built nsp_grok lab CLI then converted prompt/dispatch from unix cd/ls to user@IP + Fire/SR-OS nested enter. Decision: emulate Fire inside prompt_toolkit, not the fire package. Dispatch _walk_fire: consume child names; if first token is both a command and a child and the next token is not a child of that folder, treat as command (so `mpls lsp create` still works). exit goes up; exit all/top to root; logout/quit end session; empty walk auto-_inspect. Tests for customers 12 vprn 100 and debug toggle exist. At last full pytest after live HTTP: 27 passed; after timeout change: 15 passed (subset). Live HTTP: nsp_grok/nsp_api.py (NspClient, DebugSink, format_request, parse_find_xml). Login tries OAuth2; on success load_customers/load_services/load_sites/load_saps on Fire walk into customers / id / type / svc. Store.apply_customers / apply_services / apply_sites_saps. visible_customers returns all customers so live lists with empty sites still show. Epipe SAPs try epipe.L2AccessInterface then vll.L2AccessInterface.

Exception-handling work (latest request) is incomplete: main() wraps UserCancelled (130), KeyboardInterrupt (130), NspApiError (1), generic Exception (1). login_interactive Ctrl-C/EOF now raises UserCancelled instead of returning None. run_repl Ctrl-C raises UserCancelled (no longer ^C continue). dispatch unexpected exceptions re-raised as RuntimeError. _sync_live UserCancelled re-raise; NspApiError and other Exception return Outcome(..., quit=True). HISTORY_FILE.touch OSError ignored. Not finished: _customer still returns NspApiError without quit; need to confirm _connect_nsp body, run_repl return code used by _main (`return run_repl(ctx)` was applied), compile, and pytest. UserCancelled import in commands.py was applied.

5. Optional Next Step: Finish the Ctrl-C / failure handling the user just asked for: message + close. Verify app.py _connect_nsp is syntactically valid; make live fetch errors in _customer also quit; run pytest; do not invent extra features. Quote of the unfinished edit: "except NspApiError as exc: return Outcome(error=str(exc))" in _customer still lacks quit=True; UserCancelled import in commands.py succeeded; "HISTORY_FILE.touch exist_ok" wrap was applied in run_repl. Latest user request: "agregar manejo de excepciones al fallar si el usuario aprieta ctrl-C y tambien por otras fallas, muestra un mensaje acorde y cierra".

## Verbatim turns

### Turn 0 (System)
You are Grok 4.6 released by xAI. You are an interactive CLI tool that helps users with software engineering tasks. Your main goal is to complete the user's request, denoted within the <user_query> tag.

<work_policy>
- Keep every explicit requirement of the request in view until it is completed, superseded by the user, or genuinely blocked. If something is blocked, say so plainly rather than quietly dropping it.
- Match your response to the user's intent. Implement clear action requests; answer questions, reviews, explanations, and planning requests without making unsolicited project edits.
- For clear, reversible local work, do it in the current turn instead of asking permission conversationally or ending with an offer to do it later.
- When the user explicitly asks you to use subagents or delegate work, those launches are part of the requested outcome: make the `spawn_subagent` calls near the start of the work. Saying you will delegate but never launching does NOT satisfy the request.
- Claim that something is done, fixed, tested, or addressed only when tool output supports the claim. Otherwise state what you did not verify and why.
- Keep changes scoped to what was asked. Match the surrounding code's comment and tooling conventions: comments should be short, factual, and only explain non-obvious constraints; never narrate your reasoning or implementation steps, and never leave placeholders for unrelated work using comments. Comments and suppressions must NOT substitute for fixing a problem.
</work_policy>

<tool_calling>
- Use specialized tools instead of bash commands when possible, as this provides a better user experience. For file operations, prefer dedicated file tools (e.g., `read_file` for reading files instead of cat/head/tail, `search_replace` for editing and creating files instead of sed/awk). Reserve bash tools exclusively for actual system commands and terminal operations that require shell execution. NEVER use bash echo or other command-line tools to communicate thoughts, explanations, or instructions to the user. Output all communication directly in your response text instead.
</tool_calling>

<background_tasks>
- Run a long-lived command you own (a build, test suite, or server) as a background command in `run_terminal_command`, then continue independent work; its completion is reported to you.
- Use `get_command_or_subagent_output` for a snapshot of current output, or for one bounded wait when no independent work remains — NOT for repeated status polling.
- Use `monitor` for watch processes, polling, and ongoing observation of external conditions (CI status, log tailing, API polling), SPECIFICALLY for status changes.
</background_tasks>

<communication>
Communicate directly and concisely, in complete sentences. Concise means being selective about what you include, not clipping the prose: no telegraphic fragments, no shorthand the user hasn't used.
  
Write every user-facing message for a reader who has NOT seen your tool calls, internal notes, or workspace documents:
- Restate what you did and what you found in plain language. Do not assume the user remembers earlier messages or knows the state of the work.
- Define project-specific terms, abbreviations, and codenames on first use. Never carry vocabulary from internal docs, rules, or skills into your replies unless the user used it first.
- State facts literally. Do not invent metaphors, idioms, or catchy labels to describe technical work.

Lead with the answer:
- Answer the user's actual question first — especially "why" questions — then give supporting detail.
- Open with what is true or what to do. Do not open answers or sections with negations ("It's not X") or "Do not..." framing; make the point affirmatively, then contrast only if it adds information.
- If the question is answerable from context, answer it. Do not respond with a clarifying question back, and do not dump raw data when the user wants the relevant subset.

Keep intermediate progress updates short and infrequent. The final message must stand alone: what was done, what the outcome is, and the answer to what the user asked.

NEVER coin acronyms, shorthand, or technical-sounding labels of your own. ALWAYS use terminology _already established_ in the conversation or provided context; otherwise describe the concept in plain language. Established, well-known technical vocabulary is fine.
</communication>

<formatting>
Your text output is rendered as GitHub-flavored markdown (CommonMark). Use markdown actively when it aids the reader: bullet lists for parallel items, **bold** for emphasis, `inline code` for identifiers/paths/commands, and tables for short enumerable facts (file/line/status, before/after, quantitative data). For nesting markdown fences, NEVER nest equal-length fences - make the outer fence longer than every inner fence.
</formatting>

<user_guide>
Documentation about the Grok Build TUI — including configuration, keyboard shortcuts, MCP servers, skills, theming, plugins, and more — is stored as `.md` files in `~/.grok/docs/user-guide/`. When users ask about features or how to use the TUI, read the relevant file from that directory.
</user_guide>

<browser_verification>
When your work changes anything a user sees or interacts with in a web app (UI components, layout, styling, routing, or the state and data that pages render), you MUST verify your work in the browser before finishing, whenever browser tools are available.

Verifying means more than confirming that the changed screen renders:
1. Exercise the feature you changed end to end, interacting with it the way a user would.
2. Visit every page and route that shares the state, data, or components you touched, and confirm the application still behaves consistently everywhere.
3. Actively hunt for regressions in existing behavior; do not stop at the happy path.
4. When layout or styling changed, check both desktop and mobile viewport sizes.

If verification reveals a problem, fix it and verify again before ending your turn.
</browser_verification>

### Turn 1 (Human)
<user_info>
OS Version: windows
Shell: powershell
Workspace Path: C:\Users\elzoy\Code\nsp-grok-2411
Today's date: 2026-09-04
Note: Prefer using relative paths over absolute paths as tool call args when possible.
</user_info>

<git_status>
This is the git status at the start of the conversation. Note that this status is a snapshot in time, and will not update during the conversation.
## No commits yet on main
</git_status>

<rules>
The rules section has a number of possible rules/memories/context that you should consider. In each subsection, we provide instructions about what information the subsection contains and how you should consider/follow the contents of the subsection.


<user_rules description="These are rules set by the user that you should follow if appropriate.">
<user_rule>
When implementing or fixing anything in a web application (UI, layout, styling, routing, client state, or rendered data), verify your work in the browser before declaring the task complete.

**Use this verification workflow:**
- Open the app with the available browser tools and exercise the changed feature end to end the way a real user would: click, type, submit, navigate.
- A single render screenshot of the changed screen is NOT verification. Confirm behavior, not just appearance.
- Check every page and route that shares the state, data, or components you touched. Application state must stay consistent across pages: if you changed how state is written or derived, verify the other surfaces that read it.
- Hunt for regressions. The most common failure mode is a change that works in isolation but breaks existing behavior elsewhere in the app. Navigate the surrounding flows and look for what broke.
- Verify the paths and edge states your change touches (empty states, error states, route and flag variants), not only the main path.
- When layout or styling changed, check both desktop and mobile viewports.
- If verification finds a problem, fix it and re-verify. Do not finish with unverified UI work.

If no browser tools are available, verify through the closest available substitute (tests, curl against the dev server, rendering scripts) and say what you could not verify.
</user_rule>
</user_rules>
</rules>

### Turn 2 (Human)
<system-reminder>
The following skills are available for use:

- build-with-ai: Default to SpaceXAI when building AI/LLM features into an app
  Use when: Use whenever adding or scaffolding AI functionality — picking an AI provider/SDK, wiring chat/completions or streaming, or setting up an AI API key — and steer vibe-coded apps to SpaceXAI over OpenAI/Anthropic/Gemini. Triggers: "add a chatbot", "call an LLM", "integrate AI", "which model", "add AI to my app", "/build-with-ai".
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\build-with-ai\SKILL.md
- create-skill: Interactively create a new Grok skill (SKILL.md + optional scripts/references)
  Use when: the user wants to create a skill, scaffold a skill, or runs /create-skill.
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\create-skill\SKILL.md
- create-workflow: Create a Grok Build workflow: author a Rhai orchestration script (agents, phases, bounded parallel fan-out, verification panels), smoke-check one path with the workflow tool, save it as a named workflow, and offer a real run. Also the complete Rhai reference for workflow scripts: script shape,…
  Use when: the user wants to create/author/write a workflow, automate a multi-agent pipeline, or runs /create-w…
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\create-workflow\SKILL.md
- design: Run the full design-doc-writer and design-doc-reviewer loop until consensus. Produces a polished design document with a PR plan.
  Use when: asked to "design", "write a design doc", "system design", "architecture doc", "technical spec", or "/design".
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\design\SKILL.md
- docx: Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx or .dotx files). Triggers include any mention of 'Word doc', 'word document', '.docx', '.dotx', 'Word template', or requests to produce professional documents with formatting like tables of contents, headings, page numbers, or letterheads. Also use when extracting or reorganizing content from .docx…
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\docx\SKILL.md
- execute-plan: Execute a PR Plan DAG from a design document. Parses the plan, topologically sorts it, implements PRs in parallel using worktree-isolated subagents, runs mandatory orchestrator-level review, and assembles either a Graphite PR stack or a plain-git branch stack depending on tool availability.
  Use when: asked to "execute plan", "run the plan", "implement the design", or "/execute-plan".
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\execute-plan\SKILL.md
- game-animation-frames: Deep guide for game ANIMATION assets: motion cycles, action keyframes, effect sequences, and animation sprite sheets — built around a video-first pipeline (animate the base with image_to_video, then harvest the frames)
  Use when: Use whenever generating anything that moves: walk/run cycles, attacks, idles, FX, flags, fire, animation sheets. Complements game-asset-core.
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\game-animation-frames\SKILL.md
- game-asset-core: Core discipline for ANY game-asset generation with Imagine tools: the engine-ready defaults users don't state, spec checklists, style anchoring, read-bac…
  Use when: Use whenever generating any game art (sprites, sheets, animations, tiles, UI, FX) — then ALSO load the matching specialist skill: game-animation-frames for anything that moves, game-tilesets for tiles/terrain, game-character-consistency fo…
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\game-asset-core\SKILL.md
- game-character-consistency: Deep guide for CHARACTER IDENTITY across images: turnarounds (front/side/ back), state and damage variants, palette swaps, equipment changes, and same-character-in-context sets
  Use when: Use whenever generating character turnarounds, character sheets, variants of an existing sprite, or any same-subject multi-image set. Complements game-asset-core.
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\game-character-consistency\SKILL.md
- game-tilesets: Deep guide for game TILE assets: seamless tileable textures, terrain transition tilesets, autotiles, and ground/platform tiles
  Use when: Use whenever generating tileable textures, tilesets, terrain transitions, or seamless patterns. Complements game-asset-core.
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\game-tilesets\SKILL.md
- game-ui-icons: Deep guide for game UI assets: buttons with interaction states, panels, bars, wordmark logos, and icon sets
  Use when: Use whenever generating game UI elements, HUD assets, inventory icons, icon sets, buttons, or title logos. Complements game-asset-core.
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\game-ui-icons\SKILL.md
- imagine: How to use the image_gen and image_edit tool calls in Grok Build: when to build a visual with code instead of generating it, prompt-craft, reference-first handling of real people, factual grounding, and asset-consistency. Load this whenever generating or editing an image is on the table, i.e. when an image_gen or image_edit call is being considered or about to be made. Tool-usage-driven, not tr…
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\imagine\SKILL.md
- long-running-background-tasks: Required reading before you start, watch, or wait on anything that keeps running after you launch it — background jobs, watchers, scheduled loops, CI, pull requests, training runs, dev servers, long builds. Read it before you launch such work and before you report on its state. Saying where a …
  Use when: about to launch, supervise, inspect, diagnose, or report on work that keeps running after it is st…
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\long-running-background-tasks\SKILL.md
- pdf: Read, create, and transform PDF files. Covers pulling text and tables out of PDFs, generating new PDFs, merging and splitting documents, rotating pages, watermarking, encrypting or removing passwords, extracting embedded images, running OCR on scanned documents, and filling out PDF forms including official tax forms. Apply this skill whenever a task involves a .pdf file as input or deliverable.
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\pdf\SKILL.md
- pptx: Use this skill any time a .pptx file is involved in any way — as input, output, or both. This includes creating slide decks, pitch decks, or presentations; reading, parsing, or extracting text from any .pptx file (even if the extracted content will be used elsewhere, like in an email or summary); editing, modifying, or updating existing presentations; combining or splitting slide files; worki…
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\pptx\SKILL.md
- pr-babysit: Monitor PRs, fix CI failures, address review comments, resolve merge conflicts, and restack stacks. Supports independent PRs, Graphite stacks, and GitHub stacked PRs (gh-stack).
  Use when: "/pr-babysit".
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\pr-babysit\SKILL.md
- resume-claude: Resume or continue work from a recent Claude Code session
  Use when: the user switched from Claude Code, says "continue from Claude" or "resume my Claude session", or names a Claude session by description, path, or native ID.
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\resume-claude\SKILL.md
- resume-codex: Resume or continue work from a recent Codex CLI or Codex VS Code session
  Use when: the user switched from Codex, says "continue from Codex" or "resume my Codex session", or names a Codex session by description, path, or native ID.
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\resume-codex\SKILL.md
- resume-cursor: Resume or continue work from a recent Cursor CLI or Cursor Desktop session
  Use when: the user switched from Cursor, says "continue from Cursor" or "resume my Cursor session", or names a Cursor session by description, path, or native ID.
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\resume-cursor\SKILL.md
- review: Run a reviewer subagent against uncommitted local changes, a named branch, or a GitHub PR. Local and branch modes write a review file plus a summary to disk. PR mode posts the findings as a PENDING GitHub review for the user to inspect and submit through the UI.
  Use when: asked to 'review', 'code review', 'review my changes', 'review this PR', or '/review'.
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\review\SKILL.md
- skill-design-principles: Concise, high-signal principles for writing and editing skills well
  Use when: Use whenever authoring or editing a skill.
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\skill-design-principles\SKILL.md
- statusline: Configure the Grok Build status line.
  Absolute path: C:\Users\elzoy\.grok\bundled\skills\statusline\SKILL.md

The following workflows are available:

- deep-research: Research a query with bounded parallelism, cross-check the evidence, and write a cited report
  Use when: Compare, investigate, or research a question that needs sourced claims. /deep-research, research this, write a cited report.
  Absolute path: C:\Users\elzoy\.grok\bundled\workflows\deep-research.rhai
</system-reminder>

### Turn 3 (Human)
<user_query>
Replicá como web la app de NFMP de NOKIA version 24.11. Sirve para Gestionar la red MPLS. Te paso el link de NOKIA con la informacion del NSP 24.11 https://network.developer.nokia.com/learn/24_11/index/ decime si podes leer esta informacion. Y luego te indico como seguimos
</user_query>

### Turn 4 (Assistant)
[backend web_search] search: Nokia NSP 24.11 NFMP documentation site:network.developer.nokia.com

### Turn 5 (Assistant)
Voy a abrir la documentación de NSP 24.11 y decirte qué puedo leer de ahí.
[tool_request: web_fetch]
- url: https://network.developer.nokia.com/learn/24_11/index/

### Turn 6 (Function)
[tool_response]
Login with your Nokia credentials

[SSO Login](/oidc/authenticate/?next=/learn/24_11/index/) 

 ![Give us feedback](/static/img/comment.png)

Give Us Feedback

You are not authenticated. Please log in or create an account to provide feedback!

CANCEL LOG IN

### Turn 7 (Assistant)
[backend web_search] search: Nokia NFM-P 24.11 Classic Management User Guide GUI features MPLS

### Turn 8 (Assistant)
[backend web_search] search: Nokia NSP 24.11 NFM-P Java GUI screenshots topology map equipment manager

### Turn 9 (Assistant)
[tool_request: web_fetch]
- url: https://documentation.nokia.com/nsp/24-11/libfiles/libcontents.html

### Turn 10 (Function)
[tool_response]
NSP Release 24.11

  
 NSP Release 24.11 

Release 24.11 

Network Services Platform (NSP) user documentation collection, Issue 13 

May 2026 

| Document number              | Comcode | Document title                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Issue | Date          | File format                                                     |
| ---------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- | ------------- | --------------------------------------------------------------- |
| **Overview**                 |         |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |       |               |                                                                 |
| 3HE-20418-AAAB-TQZZA         |         | [Enterprise Guide](../NSP_Enterprise_Guide/iptitle.html)   The NSP Enterprise Guide describes the supported use-cases for Enterprise deployments of the NSP.                                                                                                                                                                                                                                                                                                                                                                                                                                            | 1     | December 2024 | [HTML](../NSP_Enterprise_Guide/iptitle.html)                    |
| 3HE-20025-AAAC-TQZZA         |         | [Planning Guide](../NSP_Planning_Guide/iptitle.html)   The NSP Planning Guide is intended for technology officers, network planners, and system administrators who need the information required to plan a successful deployment of the Nokia Network Services Platform, or NSP. The reader is encouraged to become familiar with the NSP architecture, the relevant components for both IP and optical networks, and the virtualization, system, and network requirements.                                                                                                                             | 9     | April 2026    | [HTML](../NSP_Planning_Guide/iptitle.html)                      |
| 3HE-20031-AAAC-TQZZA         |         | [System Architecture Guide](../NSP_System_Architecture_Guide/iptitle.html)   The NSP System Architecture Guide describes the Network Services Platform architecture and interoperation with other systems from a high-level perspective. The audience is a technology officer, network planner, or system administrator who requires a broad technical understanding of the NSP system structure and design methodology.                                                                                                                                                                                | 2     | January 2026  | [HTML](../NSP_System_Architecture_Guide/iptitle.html)           |
| 3HE-20032-AAAC-TQZZA         |         | [Transport Slice Controller Guide](../Transport_Slice_Controller/iptitle.html)   The Transport Slice Controller Guide introduces the Transport Slice Controller to operators and administrators.                                                                                                                                                                                                                                                                                                                                                                                                        | 1     | December 2024 | [HTML](../Transport_Slice_Controller/iptitle.html)              |
| **Install and commission**   |         |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |       |               |                                                                 |
| 3HE-20359-AAAA-TQZZA         |         | [CLM Installation and Upgrade Guide](../CLM_Installation_Guide/iptitle.html)   The CLM Installation and Upgrade Guide provides detailed information regarding the installation of the CLM, including pre- and post-installation activities.                                                                                                                                                                                                                                                                                                                                                             | 1     | December 2024 | [HTML](../CLM_Installation_Guide/iptitle.html)                  |
| 3HE-20009-AAAC-TQZZA         |         | [Installation and Upgrade Guide](../NSP_Installation_and_Upgrade_Guide/iptitle.html)   The NSP Installation and Upgrade Guide is intended for a technology officer, network planner, or system administrator who intends to perform a Network Services Platform deployment function.                                                                                                                                                                                                                                                                                                                    | 12    | May 2026      | [HTML](../NSP_Installation_and_Upgrade_Guide/iptitle.html)      |
| 3HE-20027-AAAC-TQZZA         |         | [Security Hardening Guide](../NSP_Security_Hardening_Guide/iptitle.html)   The NSP Security Hardening Guide is a reference document for increasing NSP security at the physical, OS, transport, user, and application levels.                                                                                                                                                                                                                                                                                                                                                                           | 2     | January 2026  | [HTML](../NSP_Security_Hardening_Guide/iptitle.html)            |
| **Monitor and troubleshoot** |         |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |       |               |                                                                 |
| 3HE-20003-AAAC-TQZZA         |         | [Analytics Report Catalog](../Analytics/iptitle.html)   The NSP Analytics Report Catalog provides information about the reports that NSP Analytics can generate.                                                                                                                                                                                                                                                                                                                                                                                                                                        | 2     | July 2025     | [HTML](../Analytics/iptitle.html)                               |
| 3HE-20004-AAAC-TQZZA         |         | [Data Collection and Analysis Guide](../NSP_Data_Collection_and_Analysis_Guide/iptitle.html)   The NSP Data Collection and Analysis Guide introduces NSP Data Collection and Analysis functions to operators and administrators by describing usage and features.                                                                                                                                                                                                                                                                                                                                       | 1     | December 2024 | [HTML](../NSP_Data_Collection_and_Analysis_Guide/iptitle.html)  |
| 3HE-20011-AAAC-TQZZA         |         | [Network and Service Assurance Guide](../NSP_Network_and_Service_Assurance_Guide/iptitle.html)   The NSP Network and Service Assurance Guide shows you how to monitor and troubleshoot your network for optimal performance. It introduces the Network Services Platform, or NSP, to technology officers and network operators by describing the tools used for network performance monitoring, including NE and service KPIs, alarm management, OAM testing, performance plots, and map views.                                                                                                         | 1     | December 2024 | [HTML](../NSP_Network_and_Service_Assurance_Guide/iptitle.html) |
| 3HE-20033-AAAC-TQZZA         |         | [Troubleshooting Guide](../Troubleshooting_Guide/iptitle.html)   The NSP Troubleshooting Guide provides information about using NSP, NFM-P tools, and other functions to troubleshoot customer services and the NSP network management domain.                                                                                                                                                                                                                                                                                                                                                          | 4     | July 2025     | [HTML](../Troubleshooting_Guide/iptitle.html)                   |
| **Operate and maintain**     |         |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |       |               |                                                                 |
| 3HE-20360-AAAA-TQZZA         |         | [CLM User Guide](../CLM_User_Guide/iptitle.html)   The CLM User Guide describes how to configure and use the Centralized License Manager.                                                                                                                                                                                                                                                                                                                                                                                                                                                               | 1     | December 2024 | [HTML](../CLM_User_Guide/iptitle.html)                          |
| 3HE-20021-AAAC-TQZZA         |         | [Classic Management](../User_Guide/iptitle.html)   The NSP NFM-P Classic Management User Guide provides information about using the NFM-P to manage service-aware IP/MPLS networks, including GUI operations, device and network management, and policy and service management.                                                                                                                                                                                                                                                                                                                         | 1     | December 2024 | [HTML](../User_Guide/iptitle.html)                              |
| 3HE-20005-AAAC-TQZZA         |         | [Device Management Guide](../NSP_Device_Management_Guide/iptitle.html)   The Device Management Guide provides information about device management using NSP to operators and administrators by describing usage and features. For information about device management using NFM-P, see the NSP NFM-P Classic Management User Guide.                                                                                                                                                                                                                                                                     | 4     | July 2025     | [HTML](../NSP_Device_Management_Guide/iptitle.html)             |
| 3HE-20010-AAAC-TQZZA         |         | [IP/Optical Coordination Guide](../NSP_IP_Optical_Coordination_Guide/iptitle.html)   The IP/Optical Coordination Guide introduces the IP/Optical Coordination GUI to operators and administrators by describing usage and features.                                                                                                                                                                                                                                                                                                                                                                     | 3     | April 2026    | [HTML](../NSP_IP_Optical_Coordination_Guide/iptitle.html)       |
| 3HE-20012-AAAC-TQZZA         |         | [Network Automation Guide](../Network_Automation/iptitle.html)   The Network Automation Guide introduces NSP network automation functions to operators and administrators by describing usage and features.                                                                                                                                                                                                                                                                                                                                                                                             | 2     | July 2025     | [HTML](../Network_Automation/iptitle.html)                      |
| 3HE-20024-AAAC-TQZZA         |         | [Path Control and Simulation Guide](../NSP_Path_Control_and_Simulation_Guide/iptitle.html)   This document provides important contextual information and procedures that will enable readers to use NSP's path control and simulation functions.                                                                                                                                                                                                                                                                                                                                                        | 2     | January 2025  | [HTML](../NSP_Path_Control_and_Simulation_Guide/iptitle.html)   |
| 3HE-20028-AAAC-TQZZA         |         | [Service Management Guide](../NSP_Service_Management_Guide/iptitle.html)   This document is intended to manage services.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | 2     | January 2026  | [HTML](../NSP_Service_Management_Guide/iptitle.html)            |
| 3HE-20030-AAAC-TQZZA         |         | [System Administrator Guide](../NSP_System_Administrator_Guide/iptitle.html)   The NSP System Administrator Guide is intended for operators who have NSP system administrator privileges and need to understand or perform Network Services Platform system management or maintenance. The guide describes how to perform operations for system and component configuration, security, access, and database management.                                                                                                                                                                                 | 11    | May 2026      | [HTML](../NSP_System_Administrator_Guide/iptitle.html)          |
| 3HE-20034-AAAC-TQZZA         |         | [User Guide](../NSP_User_Guide/iptitle.html)   The NSP User Guide introduces the Network Services Platform, or NSP, to technology officers and network operators by describing at a high level the NSP concepts, product offerings, and functional scope. For operators, the guide also includes general system access and troubleshooting information.                                                                                                                                                                                                                                                 | 1     | December 2024 | [HTML](../NSP_User_Guide/iptitle.html)                          |
| 3HE-20016-AAAC-TQZZA         |         | [Wavence Device Support Guide](../Wavence_Device_Support_Guide/iptitle.html)   NSP NFM-P Wavence Device Support Guide describes how to discover, configure, and manage Wavence devices using the NFM-P and NSP. The guide is intended for network planners, administrators, and operators and is to be used in conjunction with other guides in the NFM-P and NSP documentation suite where management of Wavence devices does not differ from other network elements. Nokia recommends that you review the entire NSP NFM-P Wavence Device Support Guide before you attempt to manage Wavence devices. | 1     | December 2024 | [HTML](../Wavence_Device_Support_Guide/iptitle.html)            |
| **Reference**                |         |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |       |               |                                                                 |
| 3HE-20007-AAAC-TQZZA         |         | [Glossary](../Glossary/iptitle.html)   The NSP Glossary is intended to expand acronyms and define unique terms that are used throughout NSP guides and products. This guide is not intended to define industry-standard terms and will only provide spell-outs in those cases.                                                                                                                                                                                                                                                                                                                          | 1     | December 2024 | [HTML](../Glossary/iptitle.html)                                |
| 3HE-20026-AAAC-TQZZA         |         | [Release Description](../NSP_Release_Description/iptitle.html)   This document is intended to assist network planners and administrators by providing high-level feature descriptions for NSP Release 24, along with the schedule for delivery.                                                                                                                                                                                                                                                                                                                                                         | 1     | December 2024 | [HTML](../NSP_Release_Description/iptitle.html)                 |
| 3HE-20019-AAAC-TQZZA         |         | [Statistics Management Guide](../Statistics_Management_Guide/iptitle.html)   The NSP NFM-P Statistics Management Guide describes statistics management using the NFM-P. Supported performance and accounting statistics are searchable in the Statistics Search Tool.                                                                                                                                                                                                                                                                                                                                   | 1     | December 2024 | [HTML](../Statistics_Management_Guide/iptitle.html)             |
| 3HE-20022-AAAC-TQZZA         |         | [XML API Developer Guide](../XML_API_Developer_Guide/iptitle.html)   The NSP NFM-P XML API Developer Guide provides information about developing OSS applications, including setting up the development environment, understanding the XML API schemas, and typical operational scenarios, such as receiving a real-time JMS event stream.                                                                                                                                                                                                                                                              | 1     | December 2024 | [HTML](../XML_API_Developer_Guide/iptitle.html)                 |

### Turn 11 (Assistant)
Sí: pude leer documentación pública de **NSP 24.11**, pero **no** el link que me pasaste.

## El link que enviaste

`https://network.developer.nokia.com/learn/24_11/index/` pide **login Nokia (SSO)**. Sin credenciales no entra: solo veo la pantalla de autenticación.

Si más adelante tenés PDFs, capturas de la GUI, o un export del portal, los puedo usar como referencia.

## Lo que sí pude leer (público)

La colección oficial de **NSP Release 24.11** en `documentation.nokia.com/nsp/24-11/` (Issue 13, mayo 2026). Incluye, entre otros:

| Guía | Para qué sirve |
|---|---|
| **Classic Management (NFM-P User Guide)** | GUI clásica para redes IP/MPLS: operaciones, dispositivos, políticas, servicios |
| Device Management Guide | Inventario y gestión de NEs (NSP vs NFM-P clásico) |
| Network and Service Assurance | Mapas, KPIs, alarmas, OAM |
| Path Control and Simulation | Control y simulación de paths |
| Service Management | Servicios |
| Statistics Management | Estadísticas NFM-P |
| XML API Developer Guide | API OSS (XML/SOAP, JMS) |
| System Architecture / Planning / Admin | Arquitectura, despliegue, admin |
| Release Description 24.11 | Features de la release |

## Qué es NFM-P 24.11 (resumen)

**NFM-P** (Network Functions Manager – Packet, evolución del 5620 SAM) es el gestor clásico de Nokia para redes **IP/MPLS**. En 24.11 vive como componente de **NSP**.

La GUI original es un **cliente Java** (no web), con:

- Barra de menú (`File`, `Manage`, `Application`, `Tools`…)
- Árbol de navegación (Equipment / Routing / Services)
- Mapas de topología (físico, IGP, OSPF, ISIS, **MPLS**, túneles, LSP, servicios)
- Forms de lista y de configuración (pestañas, multi-edit, clipboard)
- Alarmas, inventario, discovery, políticas, servicios (VPLS, VPRN, Epipe, IES…)
- MPLS: interfaces, LSPs RSVP/LDP/SR, service tunnels, MPLS-TP
- Equipment Manager, Task Manager, búsquedas avanzadas, span of control

En NSP 24.11 hay además una **GUI web** (Network Map and Health, Device Management, Service Management, Path Control). Vos pediste replicar **NFM-P**, o sea la experiencia clásica.

## Limitación importante

Puedo reconstruir **estructura, flujos y look** a partir de la doc pública. No tengo:

- Acceso al portal de desarrolladores (APIs internas, labs, ejemplos autenticados)
- Capturas reales de tu NFM-P
- El look exacto píxel a píxel del cliente Java 24.11

Cuando quieras, decime cómo seguimos: alcance (solo GUI demo, o con datos/API), módulos (topología, MPLS, alarmas, servicios, inventario), y si preferís look Java clásico o look NSP web.

### Turn 12 (Human)
<user_query>
yo tengo acceso a esos documentos decime cuales necesitas y los busco por vos
</user_query>

### Turn 13 (Assistant)
[backend web_search] search: Nokia NSP 24.11 developer portal learn NFM-P REST API XML schema site:network.developer.nokia.com

### Turn 14 (Assistant)
Voy a mirar el índice de la guía clásica de NFM-P para pedirte documentos concretos, no una lista genérica.
[tool_request: web_fetch]
- url: https://documentation.nokia.com/nsp/24-11/User_Guide/iptitle.html
[tool_request: web_fetch]
- url: https://documentation.nokia.com/nsp/24-11/User_Guide/ipmtoc.html

### Turn 15 (Function)
[tool_response]
Classic Management

# NSP  
 Network Services Platform

##### Network Functions Manager - Packet (NFM-P)

#### Release 24.11

## Classic Management User Guide

### 3HE-20021-AAAC-TQZZA

### Issue 1

### December 2024

### 

© 2024 Nokia.

Use subject to Terms available at: [www.nokia.com/terms](http://www.nokia.com/terms/)

### Turn 16 (Function)
[tool_response]
Contents

# Contents

* * *

[Classic Management](iptitle.html)

[Legal notice](iplegal.html)

[Contents](ipmtoc.html)

[About this document](ipabout.html)

[Part I. Getting started](ai8ha35slo.html)

[1\. NFM-P GUI](ai8ha35oau.html)

[GUI overview](ai8ha35oav.html)

[GUI workspace elements](ai8ha35oaw.html)

[GUI customization](GUI-customization.html)

[Additional GUI operations](Additional-GUI-operations.html)

[NFM-P forms](ai8ha35obc.html)

[Forms overview](Forms-overview.html)

[List forms](ai8ha35obe.html)

[Configuration forms](ai8ha35obg.html)

[NFM-P searches](ai8ha35odk.html)

[Search overview](Search-overview.html)

[Searching tips](Searching-tips.html)

[Procedures for opening and closing the GUI](ai8ha35ob3.html)

[To open a single-user GUI client configured for one NFM-P system](ai8ha35ob4.html)

[To open a single-user GUI client configured for multiple NFM-P systems](ai8ha35ob4two.html)

[To open the NFM-P GUI through a client delegate server](ai8ha35ocl.html)

[To close the NFM-P GUI](ai8ha35ocm.html)

[Procedures for using the GUI](ai8ha35ocn.html)

[To manage the display of windows and forms](ai8ha35oco.html)

[To save or open a set of forms for quick access](ai8ha35ocq.html)

[To manage a window or form as an external window](ai8ha35ocr.html)

[To send a text message to other NFM-P users](ai8ha35ocs.html)

[To use configuration forms to configure or view parameters](ai8ha35oct.html)

[To manage configuration forms with built-in navigation trees](ai8ha35ocu.html)

[To modify multiple objects at one time (multi-edit)](ai8ha35ocv.html)

[To use the NFM-P clipboard](ai8ha35ocx.html)

[To monitor the NFM-P Task Manager](ai8ha35oc1.html)

[To save listed information to a file](ai8ha35oc5.html)

[Procedures for configuring user preferences](ai8ha35oc6.html)

[To configure NFM-P user preferences](ai8ha35oc7.html)

[To set local tab preferences for configuration forms](ai8ha35oc9.html)

[To temporarily display hidden tabs on property forms](ai8ha35oda.html)

[To export local tab preferences](ai8ha35odb.html)

[To import local tab preferences](ai8ha35odc.html)

[To configure the current client time zone](ai8ha35odd.html)

[To manage the display of listed information](ai8ha35ode.html)

[Procedures for searching](ai8ha35odu.html)

[To perform a simple search from an object list form](ai8ha35odv.html)

[To perform an advanced search from an object list form](ai8ha35odw.html)

[To perform a search by specifying endpoints](ai8ha35od5.html)

[To save search filters](ai8ha35od8.html)

[To use a saved search filter](ai8ha35oeb.html)

[To delete a saved search filter](ai8ha35oec.html)

[To copy an advanced search filter](ToSaveSearchFilters-4CD8D52A_yf.html)

[To locate an attribute on a configuration form](ai8ha35oed.html)

[To filter object types](ai8ha35oef.html)

[To filter using span of control](ai8ha35oeg.html)

[To configure and save equipment group filters](ai8ha35oej.html)

[To use a saved equipment group filter](ai8ha35oek.html)

[2\. NFM-P custom workspaces](ai8ha35oi8.html)

[NFM-P custom workspaces overview](NFM-P-custom-workspaces-overview.html)

[Workspace customization](ai8ha35oi9.html)

[Workflow to administer NFM-P custom workspaces](ai8ha35oja.html)

[Workflow to customize NFM-P workspaces](ai8ha35ojb.html)

[Workflow to share workspaces](ai8ha35ojd.html)

[NFM-P GUI custom workspace procedures](ai8ha35oje.html)

[Overview](Overview-NFMPGUICstmWrks.html)

[To create a new custom workspace](ai8ha35ojf.html)

[To modify an existing workspace](ai8ha35ojg.html)

[To customize window layouts](ai8ha35ojj.html)

[To configure tab preferences](ai8ha35ojk.html)

[To customize menus](ai8ha35ojn.html)

[To customize toolbars](ai8ha35ojo.html)

[To customize tree labels](ai8ha35ojp.html)

[To customize list forms](ai8ha35ojt.html)

[To configure the workspace selector](ai8ha35ojw.html)

[To apply a different workspace using the workspace selector](ai8ha35ojx.html)

[To delete a custom workspace](ai8ha35ojy.html)

[To export custom workspaces](ai8ha35ojz.html)

[To import a workspace](ai8ha35oj0.html)

[To add new menu items to a custom workspace of an earlier NFM-P release](ai8ha35oj1.html)

[3\. NFM-P navigation tree](ai8ha35oh4.html)

[NFM-P navigation tree](ai8ha35oh5.html)

[Overview](Overview-NFMPNvgtnTr.html)

[Icons and labels](ai8ha35oh7.html)

[Equipment groups](ai8ha35oh8.html)

[Navigation tree toolbar](ai8ha35oh9.html)

[Contextual menus](ai8ha35oie.html)

[Basic navigation tree procedures](ai8ha35oif.html)

[To locate objects in the navigation tree](ai8ha35oig.html)

[To change the root object of a navigation tree](ai8ha35oim.html)

[To manage NEs in equipment groups on the navigation tree](ai8ha35oin.html)

[4\. Topology map management](ai8ha35oel.html)

[Topology map types](ai8ha35ofh.html)

[Working with topology maps](ai8ha35of0.html)

[To open a map from the NFM-P main menu](ai8ha35of6.html)

[To open a service topology map](ai8ha35of8.html)

[To open an MPLS provisioned path map from the MPLS Path form](ai8ha35of9.html)

[To open a dynamic LSP path map from the LSP Path form](ai8ha35oga.html)

[To open a dynamic LSP cross-connect topology map](ai8ha35ogd.html)

[To use OAM diagnostic functions on service topology and composite service flat topology maps](ai8ha35ohb.html)

[To modify a service from the topology view](ai8ha35ohi.html)

[To create a physical link](ai8ha35ohl.html)

[To create a radio link](ai8ha35ohx.html)

[5\. NFM-P-based schedules](ai8ha35oio.html)

[Schedules overview](ai8ha35oip.html)

[Overview](Overview-SchdlOvrvw.html)

[Time zones and time stamps](ai8ha35oiq.html)

[NFM-P-based schedules](ai8ha35ois.html)

[Workflow to create and manage NFM-P-based schedules](ai8ha35oiu.html)

[NFM-P-based schedule procedures](ai8ha35oiv.html)

[Overview](Overview-NFMPBsdSchdlPrc.html)

[To configure an NFM-P-based schedule](ai8ha35oiw.html)

[To associate a task with an NFM-P-based schedule](ai8ha35oiz.html)

[To view scheduled tasks associated with an NFM-P-based schedule](ai8ha35oi0.html)

[To assign a different user account to an NFM-P-based scheduled task](ai8ha35oi3.html)

[To turn up or shut down an NFM-P-based scheduled task](ai8ha35oi4.html)

[To immediately execute an NFM-P-based scheduled task](ai8ha35oi5.html)

[To view the current status of an NFM-P-based scheduled task](ai8ha35oi6.html)

[To modify a scheduled task on an NFM-P schedule](ai8ha35oi7.html)

[Part II. Device management](ai8ha35slp.html)

[6\. Device support](ai8ha35oj5.html)

[Device support overview](ai8ha35oj6.html)

[Sample workflow to configure and manage devices](ai8ha35oj8.html)

[1830 VWM](VWM-36755256.html)

[210 WBX](WBX210-jw.html)

[7210 SAS](ai8ha35okc.html)

[7250 IXR](a7250IXR_TRG.html)

[7450 ESS](ai8ha35okn.html)

[7705 SAR](ai8ha35oko.html)

[7750 SR](ai8ha35ok5.html)

[7850 VSG/VSA](ai8ha35ok7.html)

[7950 XRS](ai8ha35ok8.html)

[Generic NEs](ai8ha35olm.html)

[OmniSwitch](ai8ha35ole.html)

[Wavence SM and Wavence SA](ai8ha35olb.html)

[7\. Device management using drivers](devicedriverchapterag.html)

[Overview](devicedriveroverviewtopic.html)

[Driver framework capabilities](drivercapableau.html)

[Driver availability](devicegnedriverstopic.html)

[Driver installation and upgrade](Driver-installation-and-upgrade.html)

[View installed drivers on the NFM-P](viewdriverau.html)

[View the automatically created Generic NE profile](VwThAtmtcCrtdGnrcNEPrfl.html)

[View the automatically created alarm catalog](VwThAtmtcCrtdAlrmCtlg.html)

[8\. Device commissioning and management](ai8ha35omz.html)

[Device commissioning](ai8ha35om0.html)

[Overview](Overview-DvcCmmss.html)

[Device-specific commissioning information](DvcSpcfcCmmssInfrm.html)

[Workflow to commission Nokia devices](ai8ha35ong.html)

[GNE commissioning](ai8ha35om9.html)

[Overview](Overview-GNECmmss.html)

[Configuring user-defined alarms for GNEs](ai8ha35ond.html)

[Workflow to commission GNEs](ai8ha35on9.html)

[Procedures for device commissioning](ai8ha35onh.html)

[To commission a device for NFM-P management](ai8ha35onj.html)

[To commission an OmniSwitch for NFM-P management](ai8ha35onk.html)

[To configure the NFM-P SNMP trap listener](ai8ha35onu.html)

[To configure polling for a 7250 IXR, 7450 ESS, 7705 SAR, 7750 SR, 7950 XRS, VSR, or Wavence SM](ai8ha35on3.html)

[To configure polling for a 7210 SAS](ai8ha35on5.html)

[To configure polling for a 7705 SAR-Hm](polling_hm_ks.html)

[To edit polling settings for multiple devices](ai8ha35on8.html)

[Procedures for GNE commissioning](ai8ha35ooa.html)

[To prepare a GNE for NFM-P management](ai8ha35oob.html)

[To configure an alternate EMS for a specific GNE](ai8ha35ood.html)

[To modify a GNE profile](ai8ha35ooe.html)

[To create a GNE alarm catalog](ai8ha35oog.html)

[To create a transform function for a GNE alarm catalog](ai8ha35ooo.html)

[To add an alarm mapping to a GNE alarm catalog](ai8ha35oou.html)

[To delete a GNE alarm catalog](ai8ha35oov.html)

[9\. Device discovery](ai8ha35oo1.html)

[Discovering devices using the NFM-P](ai8ha35oo3.html)

[Overview](Overview-DscvrDvcsUsngTh.html)

[Device SNMP management](Device-SNMP-management.html)

[Device management states](ai8ha35oo7.html)

[Using multiple management interfaces](ai8ha35opb.html)

[Post-discovery actions on discovered NEs](postdisco.html)

[Configuring SSH security on devices](ai8ha35opd.html)

[Mediation and event notification policies](ai8ha35opi.html)

[NE resynchronization](ai8ha35opl.html)

[Server resource management](ai8ha35opo.html)

[Workflow for device discovery](ai8ha35opp.html)

[Procedures for device discovery](ai8ha35opq.html)

[To enable SNMPv3 management of a device](ai8ha35opr.html)

[To enable SNMPv3 management and discover an 1830 VWM device](ToEnableSNMPv3ManagementAndDiscover-61BC1A7F.html)

[To configure the AIM mediation and discovery for management of the VSR-I](configureAIMdiscoveryforVSR.html)

[To enable or disable SNMP streaming on an NE](ai8ha35opz.html)

[To verify that SSH2 is enabled on a device](ai8ha35op0.html)

[To enable SSH host key persistence on a device](ai8ha35op1.html)

[To configure device mediation](ai8ha35op3.html)

[To assign an event notification policy to an NE](ai8ha35op8.html)

[To configure a management network](ai8ha35op9.html)

[To configure an additional management interface on a main server](ai8ha35oqf.html)

[To configure an additional management interface on an auxiliary server](ai8ha35oqh.html)

[To configure a post-discovery action](ai8ha35oqj.html)

[To configure a discovery rule](ai8ha35oqk.html)

[To enable, disable, or delete a discovery rule](ai8ha35oqn.html)

[To view the post-discovery action execution status](ai8ha35oqo.html)

[To manage a post-discovery action failure on an NE](ai8ha35oqp.html)

[To manage, suspend, or unmanage a device](ai8ha35oqq.html)

[To associate a device with a discovery rule](assignnodeproc.html)

[To change from SNMPv2 to SNMPv3 management of a device](ai8ha35oqr.html)

[To switch from non-secure to secure mediation](ai8ha35oqv.html)

[To specify which management address the NFM-P uses to remanage a device](ai8ha35oqx.html)

[To rescan the network for a device according to a discovery rule](ai8ha35oqy.html)

[To partially or fully resynchronize NEs with the NFM-P database](ai8ha35oqz.html)

[To manually accept a mismatched SSH host key](ai8ha35oq0.html)

[To view the SSH2 host keys to identify active and mismatched keys](ai8ha35oq1.html)

[To list and save SNMP MIB information](ai8ha35oq3.html)

[To delete a device from the managed network](ai8ha35oq4.html)

[10\. Device CLI sessions](ai8ha35omr.html)

[Managing device CLI sessions using the NFM-P](ai8ha35oms.html)

[Overview](Overview-MngngDvcCLISssn.html)

[Workflow to use an NFM-P CLI](ai8ha35omt.html)

[To configure the NFM-P CLI console preferences](ai8ha35omv.html)

[To open and close an NFM-P device CLI session](ai8ha35omw.html)

[11\. Working with network objects](ai8ha35ouo.html)

[Working with network objects using the NFM-P](ai8ha35oup.html)

[Overview](Overview-WrkngWthNtwrkOb.html)

[Working with equipment group objects](ai8ha35our.html)

[Working with physical links](ai8ha35ous.html)

[Workflow to manage network objects](ai8ha35out.html)

[To monitor the deployment status of a network object](ai8ha35ouv.html)

[To view network resources assigned to network objects](ai8ha35ouw.html)

[12\. Device object configuration](ai8ha35oux.html)

[Working with device objects](ai8ha35ouz.html)

[Overview](Overview-WrkngWthDvcObjc.html)

[Workflow to manage device objects](ai8ha35ou3.html)

[Workflow to configure UNP 802.1x at port level for OmniSwitch devices](WrkflTCnfgrUNP8021XAtPrtLvlFrOmnS.html)

[General device configuration procedures](ai8ha35ou4.html)

[To create an object](ai8ha35ou5.html)

[To modify NE properties](ai8ha35ou6.html)

[To configure NE custom properties](ai8ha35ou7.html)

[To enable FIPS-140-2](ai8ha35ou8.html)

[To create an operational group](ai8ha35ou9.html)

[To configure a 7210 SAS operational group](ai8ha35ovb.html)

[To enable and configure global Cflowd sampling on an NE](ai8ha35ovc.html)

[To enable the automatic selection of an RD on an NE](ai8ha35ove.html)

[To configure a Service MAC list](almp_list_ks.html)

[To add a span of control to an NE](ai8ha35ovf.html)

[To configure load balancing](ai8ha35ovh.html)

[To configure proxy ARP and proxy node discovery for an NE](proxyarp_NE_ks.html)

[To configure a node discovery profile on an NE](disc_prof_ospf_ks.html)

[To enable or disable 802.1X](ai8ha35ovi.html)

[To configure an exclusive policy editing restriction on an NE](ai8ha35ovk.html)

[To configure active card alarms on an NE](ai8ha35ovl.html)

[To configure a TWAMP server](ai8ha35ovm.html)

[To enable LLDP on an NE](ai8ha35ovq.html)

[To configure the BFD flap detection interval on an NE](ai8ha35ovu.html)

[To enable a Q in Q untagged SAP on an NE](ai8ha35ovv.html)

[To configure DHCPv6 Advertise messages on an NE](ai8ha35ovw.html)

[To configure Python script protection on an NE](ai8ha35ovx.html)

[To configure home LAN extension functionality on an NE](prConfigLANext-gs.html)

[To configure ISA service chaining on an NE](prConfigISAserviceChain-gs.html)

[To configure optimized HTTP redirects on an NE](prOptimHttpRedir-gs.html)

[To configure sFlow on an NE](ai8ha35ovy.html)

[To configure ANYsec encryption on an NE](ToConfigureANYsecEncryptionOnAnNE.html)

[To create a chassis-level PBB configuration](ai8ha35ovz.html)

[To configure serving network information on an NE](ai8ha35ov0.html)

[To configure L2TP on an NE](ai8ha35ov1.html)

[To configure WLAN GW redundancy on an NE](ai8ha35ov3.html)

[To configure call-trace debug storage on an NE](pr-NEcallTraceConfig-gs.html)

[To configure the RADIUS CoA port on an NE](ai8ha35ov4.html)

[To configure data persistence on an NE](ai8ha35ov5.html)

[To configure DNS security extensions](ai8ha35ov6.html)

[To enable or disable ICMP extensions on a NE](ai8ha35ov7.html)

[To configure a PPPoE Intermediate Agent on an NE](TCnfgrAPPPEIntrmAgntOnAnNE.html)

[To create an FPE](createfpeks.html)

[To configure satellite file transfer](configuresatellitetransfer.html)

[To create a port template](createporttemplate.html)

[To configure the Sender-ID TLV of a CFM PDU for an NE](Sender_ID_TLV_TRG.html)

[To configure the global EVPN proxy ARP and node discovery on an NE](ToConfigureTheGlobalEVPNProxyARP.html)

[To configure a no-service loopback port on the 7210 SAS](ai8ha35ov8.html)

[To configure CFM DMM version 1 interoperability on the 7210 SAS](ai8ha35ov9.html)

[To configure two WRED slopes on a 7210 SAS](ai8ha35owa.html)

[To configure frame-based accounting for QoS policies on a 7210 SAS](ai8ha35owb.html)

[To configure the global system resource profile on a 7210 SAS or 7250 IXR](ai8ha35owc.html)

[To configure a system resource profile policy for the 7210 SAS-R/T/Mxp, 7210 SAS-S/Sx, or 7210 SAS-S/Sx VC](ai8ha35owd.html)

[To configure chassis MAC address on the 7210 SAS-S/Sx VC](configure_mac_add.html)

[To configure port-based scheduling on the 7210 SAS](ai8ha35owe.html)

[To configure buffer management for the 7210 SAS](ai8ha35owf.html)

[To configure 7210 SAS-R device properties for MVPN](TG_Config_SASR_for_MVPN.html)

[To configure IP fragmentation for 7210 SAS](TCnfgrIPFrgmnFr7210SAS.html)

[To configure forwarding path options or resource allocation on a 7250 IXR](CAM_Res_Alloc_TRG.html)

[To configure policer allocation](configPolicerAllocation.html)

[To configure watermark settings on a 7705 SAR](ai8ha35owh.html)

[To configure QoS ingress aggregate rates on the 7705 SAR-M/ME](ai8ha35owi.html)

[To launch an MCT on a Wavence SA NE connected to a 7705 SAR](ai8ha35owj.html)

[To start and stop a Webview or Secure Webview session on an OmniSwitch](ai8ha35owk.html)

[To configure the dying gasp alarm on an OmniSwitch](ai8ha35owl.html)

[To configure shelf craft port IP address on an 1830 VWM device](ToConfigureTheCraftPortIPAddressOnA-9862D36E.html)

[To configure an Auto-ID range for policies](Auto_ID_Range_TRG.html)

[To enable USB support on a 7250 IXR](enableixrusb.html)

[To globally enable or disable Packet Byte Offset on a 7250 IXR](Packet_Byte_Offset_TRG.html)

[To configure GNSS receiver functions on supported IXR and SR NEs](GNSSreceiverixre.html)

[To configure global-level UNP](GlobalLevelUNP.html)

[To configure an UNP at port-level](PortLevelUNP.html)

[To configure DHCPv6 snooping on an NE](TCnfgrDHCPv6SnpngOnAnNE.html)

[To configure the log encryption key](configLogEncryptKey.html)

[Ring group configuration procedures](ai8ha35owm.html)

[To create a ring group](ai8ha35own.html)

[To remove a device from a ring group or a ring group](ai8ha35owr.html)

[To configure the global sampling rate on an NE](ToConfigureTheGlobalSamplingRate.html)

[13\. Logical group object configuration](ai8ha35or5.html)

[Logical group object configuration using the NFM-P](ai8ha35or6.html)

[Overview](Overview-LgclGrpObjctCnf.html)

[Workflow to manage logical group objects](ai8ha35osg.html)

[Workflow to configure weighted per-link hashing on a LAG](ai8ha35osh.html)

[Logical group object configuration procedures](ai8ha35osi.html)

[To configure a CCAG](ai8ha35osj.html)

[To configure an ISA-AA group and ISA-AA partitions](ai8ha35osn.html)

[To configure AA subscriber statistics collection on an ISA-AA group or partition](ai8ha35osx.html)

[To configure special study objects on an ISA-AA group or partition](ai8ha35osz.html)

[To configure an AA subscriber policy override on an ISA-AA group or partition](ai8ha35os3.html)

[To configure Cflowd collectors on an ISA-AA group or partition](ai8ha35os7.html)

[To configure an ISA-tunnel group](ai8ha35otc.html)

[To configure an ISA-tunnel member-pool group](ToConfigureAnISA-tunnelMember-pool.html)

[To configure an ISA-LNS group](ai8ha35otf.html)

[To configure an ISA-Video group](ai8ha35oti.html)

[To configure a WLAN GW group](ai8ha35otn.html)

[To create an IGH and add members](ai8ha35otq.html)

[LAG configuration procedures](ai8ha35ott.html)

[To create a LAG](ai8ha35otu.html)

[To modify a LAG](ai8ha35ot5.html)

[To manually re-balance LAG ports](ai8ha35oub.html)

[To configure an OmniSwitch LAG](ai8ha35ouc.html)

[To configure OmniSwitch dynamic LAG members](ai8ha35ouh.html)

[To create a LAG link mapping profile](ai8ha35oui.html)

[To view micro-BFD sessions on a LAG](ai8ha35oun.html)

[14\. ESA object configuration](esaconfigchap.html)

[Configuring ESA objects using the NFM-P](esaconfigoverview.html)

[Overview](Overview-CnfgrESAObjctUs.html)

[Workflow to manage ESA objects](esaworkflow.html)

[Procedures for ESA configuration](esaconfigprocedures.html)

[To create an ESA](tocreateesa.html)

[To configure an ESA](toconfigureesa.html)

[To create a virtual machine on an ESA](tocreateesavm.html)

[To configure a virtual machine on an ESA](toconfigureesavm.html)

[To view virtual ports on an ESA](toconfigurevmports.html)

[15\. Shelf and card object configuration](ai8ha35o1q.html)

[Configuring shelf objects using the NFM-P](ai8ha35o1r.html)

[Overview](Overview-CnfgrShlfObjctU.html)

[SCADA on the 7705 SAR](ai8ha35o1x.html)

[Power management configuration](ai8ha35o11.html)

[Reboot hold](ai8ha35o13.html)

[Manual chassis reboot](description-topic-126-D39614FD.html)

[Workflow to manage shelf objects](ai8ha35o3e.html)

[Working with card and card slot objects](ai8ha35o14.html)

[Overview](Overview-WrkngWthCrdAndC.html)

[Card provisioning and chassis modes](ai8ha35o15.html)

[Working with daughter card objects](ai8ha35o18.html)

[Overview](Overview-WrkngWthDghtrCr.html)

[Working with bundle objects](ai8ha35o3b.html)

[Overview](Overview-WrkngWthBndlObj.html)

[Working with extension shelf objects](s_shelf_ext_jw.html)

[Extension shelves](ovr_shelf_ext_jw.html)

[Procedures for shelf object configuration](ai8ha35o3f.html)

[To configure an 1830 VWM shelf](ToConfigureAnShelf-3A2E11DE.html)

[To configure the device chassis mode](ai8ha35o3g.html)

[To configure a VWM shelf for a 7210 SAS](ai8ha35o3h.html)

[To configure dry contact sensors](ai8ha35o3m.html)

[To configure the IMM card type on a 7210 SAS-R](ai8ha35o3q.html)

[To configure switch fabric multicast ingress replication rates](ai8ha35o3r.html)

[To configure IMPM overrides](ai8ha35o3s.html)

[To enable mixed mode](ai8ha35o3t.html)

[To configure timing synchronization](ai8ha35o3u.html)

[To configure the IEEE 1588 PTP clock on a 7210 SAS, 7250 IXR, 7450 ESS, or 7750 SR](ai8ha35o4r.html)

[To configure the IEEE 1588 PTP peer of a 7210 SAS, 7250 IXR, 7450 ESS, or 7750 SR](ai8ha35o4s.html)

[To configure IEEE 1588 PTP ports on a 7210 SAS, 7250 IXR, 7450 ESS, 7750 SR, or 7950 XRS](Config_PTP_ports_TRG.html)

[To configure alternate profiles under IEEE PTP Clock on a 7250 IXR, 7450 ESS, 7750 SR, or 7950 XRS](alternateprofileao.html)

[To associate an alternate profile to an IEEE PTP Port on a 7250 IXR, 7450 ESS, 7750 SR, or 7950 XRS](associatealternateprofileao.html)

[To configure an IEEE 1588 PTP clock on a 7705 SAR](ai8ha35o3w.html)

[To configure an IEC/IEEE 61850-9-3 PTP clock on a 7705 SAR](IEEE61850PTCclock.html)

[To configure alternate profiles under IEEE PTP Clock on a 7705 SAR](TCnfgrAltrnPrflsUndrIEEEPTPClckOn.html)

[To associate an alternate profile to an IEEE PTP Port on a 7705 SAR](TAssctAnAltrnPrflTAnIEEEPTPPrtOnA.html)

[To configure an IEEE 1588 PTP port on a 7705 SAR](ai8ha35o3y.html)

[To configure system time on a 7705 SAR](ai8ha35o3z.html)

[To configure SNTP on a 7705 SAR](ai8ha35o30.html)

[To configure VPLS scalability on a 7705 SAR](TCnfgrVPLSSclblOnA7705SAR.html)

[To configure NTP on supported devices](ai8ha35o31.html)

[To configure NTP on 1830 VWM OSU devices](ToConfigureNTPOnDevices-4901912D.html)

[To configure SCADA on a 7705 SAR](ai8ha35o39.html)

[To configure voice conference bridging on a 7705 SAR](vcbonasarau.html)

[To configure a 7705 SAR MW link](ai8ha35o4b.html)

[To configure a 7705 SAR MW link member](ai8ha35o4h.html)

[To configure 7705 SAR auxiliary alarm definitions](ai8ha35o4l.html)

[To manage an OmniSwitch running configuration](ai8ha35o4v.html)

[To configure OmniSwitch health monitoring](ai8ha35o4x.html)

[To configure a CCM on a 7950 XRS-20](ai8ha35o4y.html)

[To manage the internal fan on a 7210 SAS-D](ai8ha35o4z.html) 

[To enable fan speed monitoring on a 7x50 device](enable_fanspeedmonitoring.html)

[To configure a power supply tray](ai8ha35o41.html)

[To configure a power management zone](ai8ha35o43.html)

[To configure a PCM tray](config_PCMtray.html)

[To provision an APEQ](ai8ha35o44.html)

[To configure a variable power supply APEQ](ai8ha35o45.html)

[To restart an 1830 VWM shelf](ToRestartAnShelf-90A1AEFE.html)

[To configure optical protection switching on an 1830 VWM OPS shelf](ToConfigureOpticalProtectionSwitchi-A7D7AB76.html)

[To configure bi-directional protection switching on an 1830 VWM OPS shelf](bidirectprotectswitchau.html)

[To configure an OPS protection audit entity on an 1830 VWM OSU shelf](ToConfigureAPAEOnAnOSUShelf-A7D7B965.html)

[To activate or deactivate a PAE](ToActivateOrDeactivateAPAE-A7D89E60.html)

[Procedures for card and card slot object configuration](ai8ha35o46.html)

[To assign a card type](ai8ha35o47.html)

[To configure an Xiom-s card slot](xiomcardslotconfig.html)

[To assign a network queue policy to a forwarding plane](Net_Queue_on_FP_TRG.html)

[To assign an FP Resource policy to a forwarding plane](FP_Resource_on_FP_TRG.html)

[To configure a network ingress pool on a forwarding plane](Net_Ing_Pools_FP_TRG.html)

[To view the operational MC path management properties of a forwarding plane](MC_Path_FP_TRG.html)

[To configure egress WRED queue control on an XCM, IOM 3 or IMM forwarding plane](ai8ha35o48.html)

[To configure ingress policy accounting policer limits on a forwarding plane](Ing_Pol_Limit_on_FP_TRG.html)

[To configure IMPM on an XCM, 2 x XP MDA IOM 3, or IMM forwarding plane](ai8ha35o49.html)

[To configure an ingress queue group on a forwarding plane](ai8ha35o5a.html)

[To configure NE DDoS protection on a forwarding plane](TCnfgrNEDDSPrtctOnAFrwrdPln.html)

[To enable named pool mode](ai8ha35o5d.html)

[To enable Stable Pool Sizing](ai8ha35o5e.html)

[To enable Ingress Buffer Allocation](ai8ha35o5f.html)

[To initialize drop priority mode on card forwarding plane](ToInitializeDropPriorityModeOnCardForwardingPlane-AC.html)

[To select system resource profile policies for the 7210 SAS-R or 7210 SAS-S/Sx VC](ai8ha35o5g.html)

[To configure OmniSwitch stacks](ai8ha35o5h.html)

[To configure an OmniSwitch CPU temperature threshold](ai8ha35o5i.html)

[To configure a CPM](ai8ha35o5j.html)

[To configure a CPRI rate and channel management for a CDR channel on an 1830 VWM TLU or ITP card slot](ToConfigureACPRIRateForACDRChannel-3A1F1C17.html)

[To modify the SFP profile and SFP profile rate on the 1830 VWM](assign_cdr_channel.html)

[To upgrade a license path on an IOM-1, IOM5-e, and XIOM-s](upgradelicensepathIOM.html)

[Procedures for daughter card slot object configuration](ai8ha35o5k.html)

[To configure an MDA](ai8ha35o5l.html)

[To configure IMPM on an MDA](ai8ha35o5u.html)

[To upgrade a license path on an FP4 MDA](upgradelicensepathMDA.html)

[To specify an event action for a 7x50 MDA](specifyeventactionMDA.html)

[To view the operational multicast channel properties of an MDA](ai8ha35o5w.html)

[To configure a module card on a 7705 SAR-M/ME or 7705 SAR-H](ai8ha35o5x.html)

[To configure GNSS receiver functions on a 7705 SAR-Hm](GNSSreceiversarhmao.html)

[To perform a manual SIM switchover on a 7705 SAR-Hm](dualsimswitch_ks.html) 

[Procedures for bundle configuration](ai8ha35o56.html)

[To create an FR group bundle](ai8ha35o57.html)

[To modify an FR group bundle](ai8ha35o59.html)

[To create an IMA group bundle](ai8ha35o6a.html)

[To modify an IMA group bundle](ai8ha35o6e.html)

[To create an MLPPP bundle](ai8ha35o6f.html)

[To modify an MLPPP bundle](ai8ha35o6h.html)

[To configure an MLPPP bundle for multiclass service transmission](ai8ha35o6j.html)

[To configure an MLPPP bundle as a network interface on a channelized ASAP MDA](ai8ha35o6k.html)

[Procedures for extension shelf configuration](pr_shelf_ext-jw.html)

[To create a satellite shelf](create_esat_pr-jw.html)

[To configure satellite shelf uplink port topology](cfg_esat_uplink-jw.html)

[To configure flexible satellite port mapping for Ethernet satellites](cnfg_flexible_satellite_portmapping.html)

[To configure tunable optics for Ethernet satellites](cnfg_tunable_optics_satellite.html)

[To associate a port template on an Ethernet satellite shelf](cnfg_esat_associateporttemplate.html)

[To configure local forward on Ethernet satellite shelf](cnfg_esat_localforward.html)

[To enable transparent clock functionality on an Ethernet satellite](cnfg_esat_transparentclock.html)

[To perform a software upgrade on an extension shelf](upg_oes_soft-jw.html)

[Procedures for power shelf configuration](pr_powershelf.html)

[To configure power shelves](config_powershelf.html)

[To configure power modules](config_powermodule_ao.html)

[16\. Port and channel object configuration](ai8ha35owt.html)

[Configuring port and channel objects](ai8ha35owu.html)

[Overview](Overview-CnfgrPrtAndChnn.html)

[Digital diagnostics monitoring](ai8ha35oww.html)

[Remote fiber link monitoring in 1830 VWM devices](RFLMPortInOSUDevices-911EB7E6.html)

[Tagged and untagged VLAN ports](ai8ha35owx.html)

[Connection termination points for services and interfaces](ai8ha35ow1.html)

[Copying and moving SAPs](ai8ha35oxb.html)

[Configuring access SAP bandwidth CAC](ai8ha35oxbsl.html)

[SONET/SDH and TDM port encapsulation](ai8ha35oxc.html)

[SONET clear channel applications](ai8ha35oxd.html)

[TDM channelization and clear channel applications](ai8ha35oxg.html)

[ATM encapsulation](ai8ha35oxj.html)

[Workflow to manage port objects](ai8ha35ox4.html)

[SONET and SDH sub-channel applications and structure](ai8ha35oxn.html)

[Overview](Overview-SONETAndSDHSbCh.html)

[SONET sub-channel syntax](ai8ha35oxs.html)

[Comparison of SONET and SDH hierarchies](ai8ha35oxu.html)

[SDH AU-4 and AU-3 sub-channel applications](ai8ha35oxw.html)

[SDH TU3 payload](ai8ha35oxx.html)

[SDH E3 or DS3 payload](ai8ha35oxz.html)

[SDH TU11 and TU12 payloads](ai8ha35ox1.html)

[Workflow to manage channel objects](ai8ha35ox5.html)

[Procedures for port configuration](ai8ha35ox6.html)

[To configure 1830 VWM ports](ToConfigurePorts-3A94238E.html)

[To configure Ethernet LAN ports on the 1830 VWM OSU and 1830 VWM SMM](ToConfigureSMMPorts.html) 

[To configure connector ports and breakout ports](SR1brkoutport_ks.html)

[To configure Ethernet ports](ai8ha35ox7.html)

[To configure LLDP-MED](To-configure-LLDP-MED.html)

[To configure LLDP MED Network Policy](ToConfigureLLDPMEDNetworkPolicy.html)

[To configure a cellular port on a 7705 SAR-Hm](cellular_port_ks.html)

[To configure a WLAN port on a 7705 SAR-Hm](WLAN_port_accesspoint.html)

[To change the port mode](ai8ha35oyo.html)

[To migrate SAPs from access mode to hybrid mode](ai8ha35oys.html)

[To configure the NFM-P to retain non-default port MTU values](ai8ha35oyt.html)

[To copy or move L2 SAPs between ports](ai8ha35oyu.html)

[To copy or move L2 access interface SAPs between services](ai8ha35oyx.html)

[To move L3 SAPs within or between ports or LAGs on the same NE](ai8ha35oyy.html)

[To move L3 subscriber interface SAPs between ports on the same NE](ai8ha35oy0.html)

[To configure bandwidth CAC on an access SAP for services or a LAG](ai8ha35oyxsl.html)

[To add a queue group to an Ethernet port](ai8ha35oy3.html)

[To configure queue group scheduler overrides](QueueGrpSchedOverride_TRG.html)

[To configure SONET ports](ai8ha35ozc.html)

[To configure an HSMDA override](ai8ha35ozd.html)

[To configure TDM DS3 ports](ai8ha35oze.html)

[To configure serial ports](ai8ha35ozf.html)

[To configure PW ports](ai8ha35ozg.html)

[To configure a 7210 SAS-M channelized TDM DS1 or E1 port](ai8ha35ozh.html)

[To assign QoS policies to a 7210 SAS Ethernet port](ai8ha35ozi.html)

[To create a 7210 SAS SHG](ai8ha35ozo.html)

[To configure a virtual Ethernet port on a 7705 SAR 2-port ring MDA](ai8ha35ozr.html)

[To configure Ethernet Bandwidth Notification on a 7705 SAR Ethernet port](ethbandnotau.html)

[To configure PoE ports on a 7210 SAS](ai8ha35ozs.html)

[To enable or disable hardware timestamps for ports on the 7210 SAS](Timstamp_SAS_ports_TRG.html)

[To configure MAC or VLAN authentication](ToconfigureMACAuthentication.html)

[To configure PoE ports on a 7705 SAR](ai8ha35ozt.html)

[To configure GPS on a 7705 SAR](ai8ha35ozv.html)

[To configure a 7705 SAR ASAP channelized TDM port](ai8ha35ozw.html)

[To configure a channelized TDM DS1 or E1 port](ai8ha35ozx.html)

[To configure OmniSwitch Ethernet ports](ai8ha35ozy.html)

[To configure OmniSwitch PoE Ports](ai8ha35o0b.html)

[To create and configure Xconnect anchor ports](config_anchorports.html)

[To configure PXC loopback ports](c_PXC_port.html)

[Procedures for channel and framing link configuration](ai8ha35o0c.html)

[To configure SONET clear channels](ai8ha35o0d.html)

[To perform a bulk channel creation on ports that support multiple sub-channels](ai8ha35o0h.html)

[To configure SONET sub-channels](ai8ha35o0j.html)

[To configure SDH sub-channels](ai8ha35o0o.html)

[To create VT15 (TU11) or VT2 (TU12) sub-channels](ai8ha35o0s.html)

[To create TDM DS1 or E1 channels](ai8ha35o0x.html)

[To configure TDM DS1 or E1 channels](ai8ha35o0y.html)

[To create serial channels](ai8ha35o0z.html)

[To create TDM DS3 channels](ai8ha35o00.html)

[To configure TDM DS3 channels](ai8ha35o04.html)

[To configure a DS3/E3 channel as a network interface on a channelized ASAP MDA](ai8ha35o1h.html)

[To configure data framing on a 7705 SAR](dataframingSAR.html)

[To configure an L3 interface on a DS3/E3 channel on a channelized ASAP MDA](ai8ha35o1l.html)

[To configure a PVC](ai8ha35o1m.html)

[To create an ILMI link](ai8ha35o1n.html)

[To configure an ILMI link](ai8ha35o1p.html)

[To view the channels associated with a 1830 VWM TLU port](ToViewTheChannelsAssociatedWithATLU-3A2239A9.html)

[To retrieve 1830 VWM DDM data](ToRetrieveDDMData-9118F9AB.html)

[To configure an OSC port of an 1830 VWM OSU as a RFLM port](ToConfigureAnOSCPortOfAnOSUAsRFLM-911F42E1.html)

[To perform CPRI monitoring using 1830 VWM TLU 9M MON ports](ToPerformCPRIMonitoringUsingTLU-9MM-996758DA.html)

[To configure OTDR on 1830 VWM](OTDR.html)

[17\. Inventory management](ai8ha35oq6.html)

[Managing inventory](ai8ha35oq7.html)

[Overview](Overview-MngngInvnt.html)

[Sample inventory management workflow](ai8ha35orc.html)

[Workflow to manage inventory](ai8ha35ore.html)

[To list and sort equipment information](ai8ha35org.html)

[To save an inventory list](ai8ha35orl.html)

[To inventory the CLEI codes of NE objects](ai8ha35orn.html)

[To inventory the card software versions of one NE](ai8ha35orq.html)

[To inventory the port types of one NE](ai8ha35orr.html)

[To inventory the shelf data for one NE](ai8ha35ors.html)

[To generate a network-wide inventory of managed objects](netwkinventks.html)

[To collect inventory data for NE SLA audits](ai8ha35or4.html)

[To export a network inventory file for adaptor modules and license details](exportzipinventory.html)

[18\. Card migration](ai8ha35omj.html)

[Card migration management](ai8ha35omk.html)

[Overview](Overview-CrdMgrtnMngmn.html)

[Workflow to manage card migration](ai8ha35omn.html)

[To create a card migration event](ai8ha35omp.html)

[To execute a saved card migration event](ai8ha35omq.html)

[19\. TCA](ai8ha35o6l.html)

[TCA management using the NFM-P](ai8ha35o6m.html)

[Overview](Overview-TCAMngmnUsngThN.html)

[Workflow to configure TCA](ai8ha35o6p.html)

[To configure a custom profile TCA](ai8ha35o6s.html)

[To configure a TCA policy](ai8ha35o6t.html)

[To apply a TCA policy to objects using the object properties forms](ai8ha35o6y.html)

[20\. Bulk operations](ai8ha35ol5.html)

[Bulk operations using the NFM-P](ai8ha35ol6.html)

[Overview](Overview-BlkOprtnUsngThN.html)

[Workflow to manage bulk operations](ai8ha35ol7.html)

[To create a bulk change](ai8ha35ol9.html)

[To modify a bulk change](ai8ha35omf.html)

[To execute a bulk change](ai8ha35omg.html)

[To view executed batch information](ai8ha35omh.html)

[To stop one or more bulk changes](ai8ha35omi.html)

[21\. Serial raw sockets for IP transport services](socketiptransport.html)

[Creating serial raw sockets for IP transport services using the NFM-P](creatingsockettransport.html)

[Serial socket and IP transport services](SrlScktAndIPTrnspSrvcs.html)

[Workflow to configure serial raw sockets for IP transport services](workflowsocketiptransport.html)

[Serial IP transport using the Local Host Entity Manager](SrlIPTrnspUsngThLclHstEnttyMngr.html)

[Serial raw socket and IP transport procedures](SrlRwScktAndIPTrnspPrcdr.html)

[To create a socket profile](socketprofilesl.html)

[To configure a serial raw socket on a 7705 SAR](serialsocketau.html)

[To configure a global entry using the Local Host Entity Manager](configlocalhostmanagau.html)

[To modify a global entry](configlocalhostmanagau1.html)

[To configure IP transport on an IES site](iptransportau.html)

[To configure IP transport on a VPRN site](iptransportvprnau.html)

[Part III. NE maintenance](ai8ha35slq.html)

[22\. NE maintenance overview](ai8ha35o60.html)

[Maintaining NEs using the NFM-P ](ai8ha35o61.html)

[Overview](Overview-MntnnNEsUsngThN.html)

[To view an NE file system using an SSH file browser](ai8ha35o7b.html)

[To view the accounting statistics collection status of an NE](ai8ha35o7g.html)

[To configure an event log policy](event_log_ks.html)

[To view an NE file system using an FTP file browser](ai8ha35o66.html)

[To view NE trap metrics information](ai8ha35o7h.html)

[23\. NE backup and restore](ai8ha35o7i.html)

[NE backup and restore overview](ai8ha35o7j.html)

[NE backups and restores](NE-backups-and-restores.html)

[Backup policy configuration example](ai8ha35o7k.html)

[Workflow to perform NE backups and restores](ai8ha35o7m.html)

[NE backup and restore procedures](ai8ha35o7n.html)

[To configure a backup policy](ai8ha35o7o.html)

[To perform an on-demand backup, restore, or configuration save](ai8ha35o7r.html)

[To perform an on-demand OmniSwitch backup or configuration save](ai8ha35o7s.html)

[To restore an OmniSwitch configuration](ai8ha35o7y.html)

[To restore a device configuration other than the most recent](ai8ha35o70.html)

[To view the backup, restore, or configuration save status of an NE](ai8ha35o71.html)

[To export a device configuration backup](ai8ha35o73.html)

[To import a device configuration backup](ai8ha35o74.html)

[24\. NE configuration rollback](ai8ha35o75.html)

[NE configuration rollback overview](ai8ha35o76.html)

[Comparing configuration files](ai8ha35o77.html)

[Workflow to configure NE configuration rollback](ai8ha35o78.html)

[NE configuration rollback procedures](ai8ha35o79.html)

[To configure NE configuration rollback file storage](ai8ha35o8a.html)

[To create an NE configuration rollback rescue file](ai8ha35o8d.html)

[To create NE configuration rollback checkpoint files](ai8ha35o8e.html)

[To configure scheduled checkpoint file creation](ai8ha35o8f.html)

[To compare NE configuration rollback files](ai8ha35o8g.html)

[To revert to a previous NE configuration](ai8ha35o8h.html)

[To view NE configuration files](ai8ha35o8i.html)

[25\. NE deployment](ai8ha35o8j.html)

[Using the NFM-P to deploy NEs](ai8ha35o8k.html) 

[NE deployment overview](NE-deployment-overview-.html) 

[Sample deployment policy configuration](ai8ha35o8l.html)

[Workflow to configure and manage NE deployment](ai8ha35o8m.html)

[To configure the NFM-P deployment policy](ai8ha35o8o.html)

[To view and manage failed deployments](ai8ha35o8p.html)

[26\. NE software upgrades](ai8ha35o8r.html)

[NE software upgrade overview](ai8ha35o8s.html)

[Software upgrades](Software-upgrades.html)

[ISSUs](ISSUs.html)

[Reboot and reboot upgrade](ai8ha35o8t.html)

[NE software upgrade workflow and procedures](ai8ha35o8v.html)

[Workflow to manage NE software upgrades](ai8ha35o8u.html)

[To configure a software upgrade policy](ai8ha35o8w.html)

[To import device software files to the NFM-P](ai8ha35o80.html)

[To schedule an NE software upgrade](ai8ha35o85.html)

[To manage scheduled software upgrades](ai8ha35o86.html)

[To perform an ISSU or on-demand software upgrade](ai8ha35o87.html)

[To schedule an extension shelf software upgrade](ext-shelf-schd-jw.html)

[To perform an extension shelf on-demand software upgrade](ext-shelf-upd-jw.html)

[To upgrade 7705 SAR-Hm radio card firmware](upgradeSARHmfirmware.html)

[To create a software repository](ext-shelf-srep-jw.html)

[To perform an IOM, IMM, or XCM soft reset](ai8ha35o9b.html)

[To perform an IOM or XCM hard reboot](ai8ha35o9c.html)

[To upgrade the ISA-AA MDA software](ai8ha35o9d.html)

[To monitor the status of a software upgrade](ai8ha35o9f.html)

[To activate a device software image](ai8ha35o9g.html)

[To export a device software image from the NFM-P to a GUI client file system](ai8ha35o9h.html)

[To upgrade OS 6250SME and OS 6450 NE software licenses for an Ethernet (Metro) role](ai8ha35o9k.html)

[To perform an OmniSwitch on-demand software upgrade or ISSU](ai8ha35o9q.html)

[To perform an OS 6400, OS 6850E, or OS 6855 ISSU](ai8ha35o95.html)

[To certify or synchronize OmniSwitch software](ai8ha35o98.html)

[To perform an 1830 VWM on-demand software upgrade](ToPerformAnOn-demandSoftwareUpgrade-488B4B4D.html)

[Part IV. Network management](ai8ha35slr.html)

[27\. NE routing and forwarding](ai8ha35paa.html)

[NE routing and forwarding](ai8ha35pab.html)

[To configure a routing instance or a VRF instance](ai8ha35par.html)

[To configure a CPM virtual routing instance](vrtlrouteks.html) 

[To configure a cellular interface on a 7705 SAR-Hm](pdninterface_ks.html)

[To configure a local DHCPv4 server on a routing instance](ai8ha35pax.html)

[To configure a local DHCPv6 server on a routing instance](ai8ha35pa1.html)

[To perform a Force Partner Down action on a local DHCP server failover](ai8ha35pa4.html)

[To configure a RADIUS server on a routing instance](ai8ha35pa5.html)

[To configure a RADIUS proxy server on a routing instance](ai8ha35pa8.html)

[To configure a PCEP PCC](config_pcc_ks.html)

[To configure a PCE Association](To-configure-a-PCE-Association.html)

[To configure UDP relay, DHCP snooping, and DHCP Option 82 on OmniSwitch routing instances](ai8ha35pbc.html)

[To configure a static route on a routing instance](ai8ha35pbd.html)

[To configure GTP on a routing instance](PrConfigGtpRi-gs.html)

[To configure QoS for self-generated traffic on a routing instance](QoS_for_SGT_TRG.html)

[To configure LSP entries with indirect static routes](ai8ha35pbf.html)

[To create an L3 network interface on a routing instance](ai8ha35pbg.html)

[To configure L3 network interfaces](ai8ha35pbw.html)

[To create a network interface on a CPM virtual routing instance](interfonvrtks.html)

[To configure network interfaces on a CPM virtual routing instance](editinternonvrtks.html)

[To create a network domain](ai8ha35pbz.html)

[To associate a network interface or service tunnel with a network domain](ai8ha35pb0.html)

[To remove a network interface or service tunnel from a network domain](ai8ha35pb1.html)

[To list and view routing instances and child objects](ai8ha35pb3.html)

[To view and clear DHCP leases or prefixes assigned to a routing instance](ai8ha35pb4.html)

[To view DHCPv6 log events](ai8ha35pb5.html)

[To configure DHCP clients on SAR devices](TCnfgrDHCPClntsOnSARDvcs.html)

[To list MVPN Extranet objects for a NE](ai8ha35pb6.html)

[To display show router fp-tunnel information for a routing instance](ai8ha35pb7.html)

[To configure a Multi-Chassis shunt interface on a base routing instance or VPRN routing instance](TCnfgrAMltChsssShntIntrfOnABsRtng.html)

[To configure a Multi-Chassis shunting profile on a base routing instance or VPRN routing instance](ToConfigureAMulti-ChassisShuntingProfile.html)

[28\. Routing protocol configuration](ai8ha35pro.html)

[Routing protocol configuration overview](ai8ha35prp.html)

[Routing protocol configuration overview](RtngPrtclCnfgrOvrvw.html)

[Area-based routing considerations with protocol usage](ai8ha35prq.html)

[IPv6](ai8ha35prr.html)

[BFD](BFD.html)

[BGP](ai8ha35pru.html)

[BMP](bmp_topic_ks.html)

[RIP and RIPng](ai8ha35pry.html)

[LDP](ai8ha35prz.html)

[IS-IS](ai8ha35pr3.html)

[OSPFv2 and OSPv3](ai8ha35pr5.html)

[Segment routing](ai8ha35pr8.html)

[RSVP](ai8ha35pr9.html)

[L2TP](ai8ha35psb.html)

[PIM](ai8ha35psj.html)

[IGMP](ai8ha35pso.html)

[MSDP](ai8ha35psp.html)

[MLD](ai8ha35psr.html)

[Bridging](ai8ha35pss.html)

[WPP](ai8ha35pst.html)

[BIER](bier_ov_ks.html)

[IPSec](ipsec_routing_ov.html)

[Routing protocol configuration workflow and procedures](ai8ha35psu.html)

[Routing protocol configuration workflow](RtngPrtclCnfgrWrkfl.html)

[BFD and SBFD configuration workflow and procedures](bfd_section_ks.html)

[BFD and SBFD configuration overview](BFDAndSBFDCnfgrOvrvw.html)

[Workflow to configure BFD](bfd_workflow_ks.html)

[To configure a BFD template policy](ai8ha35ppn.html)

[To configure Seamless BFD](config_sbfd_ks.html) 

[BGP configuration workflow and procedures](ai8ha35ptb.html)

[BGP configuration workflow and procedures](BGP_workflow_proc_TRG.html)

[Workflow to configure BGP and MP-BGP](ai8ha35psv.html)

[To enable BGP on a routing instance](ai8ha35ptd.html)

[To configure a BGP confederation](ai8ha35ptf.html)

[To configure global-level BGP](ai8ha35pti.html)

[To configure peer-group-level BGP](ai8ha35ptm.html)

[To configure peer-level BGP](ai8ha35pts.html)

[To configure BGP SIDR prefix origin validation](ai8ha35ptx.html)

[To enable or disable BGP peering](ai8ha35pty.html)

[To create a BGP policy expression](pr_bgp_pol_exp-jw.html)

[To configure long-lived graceful restart on a BGP site](bgp_llgr.html)

[BMP configuration workflow and procedures](bmp_section_ks.html)

[BMP configuration overview](BMP-configuration-overview.html)

[Workflow to configure BMP](bmp_workflow_ks.html)

[To configure an NE as a BMP client](create_bmp_client_ks.html)

[To enable BMP](enable_bmp_ks.html)

[RIP and RIPng configuration workflow and procedures](ai8ha35ptz.html)

[RIP and RIPng configuration overview](RIPAndRIPngCnfgrOvrvw.html)

[RIP and RIPng configuration workflow](ai8ha35psw.html)

[To enable RIP or RIPng on a routing instance](ai8ha35pt0.html)

[To configure global-level RIP or RIPng](ai8ha35pt1.html)

[To configure group-level RIP or RIPng](ai8ha35pt7.html)

[To configure interface-level RIP or RIPng](ai8ha35pt8.html)

[LDP configuration workflow and procedures](ai8ha35pt9.html)

[LDP configuration overview](LDP-configuration-overview.html)

[Workflow to configure LDP](ai8ha35psx.html)

[To enable LDP on a routing instance](ai8ha35pua.html)

[To configure global-level LDP](ai8ha35pub.html)

[To configure an LDP interface](ai8ha35pue.html)

[To configure an LDP targeted peer](ai8ha35puf.html)

[To configure an LDP peer](ai8ha35puh.html)

[To configure ECMP for LDP routing](ai8ha35pui.html)

[To view the LDP session information](ai8ha35puo.html)

[IS-IS configuration workflow and procedures](ai8ha35put.html)

[IS-IS configuration overview](IS-IS-configuration-overview.html)

[Workflow to configure IS-IS](ai8ha35psz.html)

[To enable IS-IS on a routing instance](ai8ha35puv.html)

[To configure IS-IS on a routing instance](ai8ha35puw.html)

[To configure an IS-IS link group on a routing instance](ai8ha35pu1.html)

[To configure an IS-IS NET address](ai8ha35pu3.html)

[To configure an IS-IS interface](ai8ha35pu5.html)

[OSPF configuration workflow and procedures](ai8ha35pu8.html)

[OSPF configuration overview](OSPF_config_oview_TRG.html)

[Workflow to configure OSPFv2 and OSPFv3](ai8ha35ps0.html)

[To enable OSPF on a routing instance](ai8ha35pva.html)

[To create an OSPF area](ai8ha35pvc.html)

[To create an OSPF neighbor on an OmniSwitch](ai8ha35pve.html)

[To add a Layer 3 interface to an OSPF router](ai8ha35pvf.html)

[To create an OSPF area range](ai8ha35pvl.html)

[To create a virtual link between OSPF areas](ai8ha35pvo.html)

[To configure OSPF on a default routing instance or a VRF routing instance](ai8ha35pvt.html)

[To configure an IGP shortcut on an OSPF instance](IGP_OSPF_ks.html)

[To add a router to an OSPF area](ai8ha35pvy.html)

[To configure an OSPF interface](ToConfigureAnOSPFInterface.html)

[Segment routing configuration workflow and procedures](segment_routing_section.html)

[Workflow to configure segment routing](sr_workflow_ks.html)

[To create a segment routing policy](sr_policy_create.html)

[To enable SR policy support on a BGP site, peer, or peer group](sr_policy_enable.html)

[To configure IS-IS segment routing](ai8ha35pu0.html)

[To configure OSPF segment routing](OSPF_Segment_Routing_TRG.html)

[To create a segment routing tree](sr_tree_create_ks.html)

[To configure segment routing with IPv6](TCnfgrSgmntRtngWthIPv6.html)

[To configure IS-IS segment routing with IPv6](TCnfgrISISSgmntRtngWthIPv6.html)

[RSVP configuration workflow and procedures](ai8ha35pv0.html)

[Workflow to configure RSVP](ai8ha35ps1.html)

[To configure RSVP on a routing instance](ai8ha35pv1.html)

[To configure an RSVP interface](ai8ha35pv6.html)

[L2TP configuration workflow and procedures](ai8ha35pv7.html)

[L2TP configuration](L2TP-configuration.html)

[Workflow to configure L2TP](ai8ha35ps3.html)

[To configure L2TP on a routing instance](ai8ha35pv8.html)

[To update tunnel instance endpoints on an L2TP site](ai8ha35pwd.html)

[To view L2TP tunnels and tunnel endpoints](ai8ha35pwe.html)

[To view L2TP tunnel instance endpoints on a subscriber instance](ai8ha35pwf.html)

[To view L2TP sessions](ai8ha35pwg.html)

[To view PPP sessions](ai8ha35pwi.html)

[PIM configuration workflows and procedures](ai8ha35pwj.html)

[Workflow to configure PIM](ai8ha35ps4.html)

[Workflow to configure VRRP-aware PIM](vrrp_pim_workflow_ks.html)

[To enable PIM on a routing instance](ai8ha35pwk.html)

[To configure PIM on a routing instance](ai8ha35pwl.html)

[To create a PIM site on a VPRN routing instance](ai8ha35pwv.html)

[To configure Anycast PIM on a router](ai8ha35pw7.html)

[To create a PIM interface on a base routing instance or VPRN routing instance](ai8ha35pxi.html)

[IGMP configuration workflow and procedures](ai8ha35pxk.html)

[Workflow to configure IGMP](ai8ha35ps5.html)

[To enable IGMP on a routing instance](ai8ha35pxl.html)

[To configure an IGMP site on a router](ai8ha35pxm.html)

[To configure IGMP on an OmniSwitch](ai8ha35pxp.html)

[To configure an IGMP interface](ai8ha35pxq.html)

[To turn up or shut down an IGMP interface](ai8ha35pxt.html)

[To view IGMP multicast reporting statistics for an IGMP site](ai8ha35pxu.html)

[To view IGMP source statistics](ai8ha35pxv.html)

[MSDP configuration workflow and procedures](ai8ha35pxw.html)

[MSDP configuration overview](MSDP-configuration-overview.html)

[Workflow to configure MSDP](ai8ha35ps6.html)

[To enable MSDP on a routing instance](ai8ha35pxx.html)

[To configure global-level MSDP](ai8ha35pxy.html)

[To configure group-level MSDP](ai8ha35px1.html)

[To configure peer-level MSDP](ai8ha35px5.html)

[To configure group-peer-level MSDP](ai8ha35px9.html)

[To configure an MSDP source](ai8ha35pya.html)

[To enable or disable MSDP peering](ai8ha35pyc.html)

[MLD configuration workflow and procedures](ai8ha35pyd.html)

[MLD configuration overview](MLD-configuration-overview.html)

[Workflow to configure MLD](ai8ha35ps7.html)

[To enable MLD on a base routing instance](ai8ha35pye.html)

[To configure MLD on a base routing instance or VPRN routing instance](ai8ha35pyf.html)

[To configure an MLD interface on a base routing instance or VPRN routing instance](ai8ha35pyi.html)

[To configure an MLD interface on an IES L3 access interface](ai8ha35pyk.html)

[To configure an MLD group interface on a base routing instance or VPRN routing instance](ai8ha35pyl.html)

[To configure an MLD group interface on an IES site](ai8ha35pym.html)

[Bridging configuration workflow and procedures](ai8ha35pyn.html)

[Workflow to configure bridging on an OmniSwitch](ai8ha35ps8.html)

[To configure bridging on an OmniSwitch](ai8ha35pyo.html)

[To release a violated OmniSwitch LPS port](ai8ha35pyw.html)

[To add MAC address range entries to an OmniSwitch LPS port](add_LPS_range.html)

[To modify MAC address range entries in an OmniSwitch LPS port](modify_LPS_range.html)

[To Delete MAC address range from an OmniSwitch LPS port](delete_LPS_range.html)

[WPP configuration workflow and procedures](ai8ha35pyx.html)

[Workflow to configure WPP](ai8ha35pta.html)

[To create a web portal routing instance](ai8ha35pyy.html)

[BIER configuration workflow and procedures](bier_section_ks.html)

[Workflow to configure BIER](bier_workflow_ks.html)

[To configure a BIER template on a routing instance](bier_config.html)

[IPSec configuration workflow](IPSec-configuration-workflow-.html) 

[Workflow to configure IPSec](ipsec_vsr_workflow_ks.html) 

[29\. OpenFlow](ai8ha35pq3.html)

[OpenFlow overview](ai8ha35pq4.html)

[OpenFlow overview](OpenFlow-overview.html)

[OpenFlow switches](ai8ha35pq5.html)

[Configuration](ai8ha35pq7.html)

[Operation and management](ai8ha35pq8.html)

[OpenFlow configuration and management procedures](ai8ha35pre.html)

[OpenFlow configuration and management workflow](ai8ha35prd.html)

[To configure an OpenFlow switch](ai8ha35prf.html)

[To configure an OpenFlow flow table entry](ai8ha35prh.html)

[To display the OpenFlow controller channel status and SNMP statistics](ai8ha35prk.html)

[To display the ports and port SNMP statistics of an OpenFlow switch](ai8ha35prl.html)

[To display aggregate flow table statistics](ai8ha35prm.html)

[To display aggregate flow table entry statistics](ai8ha35prn.html)

[To list the OpenFlow bindings of an IP filter](TLstThOpnFlBndngOfAnIPFltr.html)

[30\. NAT](ai8ha35pp3.html)

[Network Address Translation](ai8ha35pp4.html)

[Workflow to configure NAT](ai8ha35pqb.html)

[To configure an ISA-NAT group](ai8ha35pqe.html)

[To configure an IPFIX export policy](ai8ha35pqi.html)

[To configure a NAT policy](ai8ha35pqj.html)

[To configure a NAT firewall policy](PrNATfirewallPolicy-gs.html)

[To configure a NAT prefix list](ProcNatPreixList.html)

[To configure a NAT classifier](ProcNatClassfier.html)

[To configure NAT on a routing instance](ai8ha35pqk.html)

[To configure static one-to-one NAT on a 7705 SAR base routing instance or VPRN routing instance](onetooneNAT.html)

[To configure an IPv6 firewall domain](Pr-FirewallDomain-gs.html)

[To configure a MAP-T domain](Pr-MapTdomain-gs.html)

[To start or stop a NAT address-pool drain operation](ai8ha35pqu.html)

[To configure a NAT deterministic script on a remote server](ai8ha35pqv.html)

[To configure statistics on an ISA-NAT group](ai8ha35pqw.html)

[To plot LSN subscriber host statistics](ai8ha35pqx.html)

[To view reserved IP address and reserved block information on an ISA-NAT group](ai8ha35pqy.html)

[To view ISA-NAT object information](ai8ha35pqz.html)

[31\. MPLS](ai8ha35pmy.html)

[MPLS overview](ai8ha35pmz.html)

[MPLS overview](MPLS-overview.html)

[LSPs](ai8ha35pm0.html)

[MPLS workflow and procedures](ai8ha35pni.html)

[Workflow to configure MPLS](ai8ha35pnh.html)

[Sample MPLS configuration](ai8ha35pnd.html)

[To enable MPLS on a routing instance](ai8ha35pnj.html)

[To configure an MPLS instance](ai8ha35pnk.html)

[To create an MPLS interface](ai8ha35pnn.html)

[To create an MPLS path](ai8ha35pns.html)

[To view an MPLS path](ai8ha35pnx.html)

[To create a static LSP](ai8ha35pny.html)

[To create a Dynamic LSP](ai8ha35pn0.html)

[To create a segment routing TE LSP](create_SR-TE-LSP.html) 

[To configure a Dynamic or segment routing TE LSP](config_dyn_sr_te_ks.html)

[To create a Dynamic or segment routing LSP from a tunnel template](ai8ha35poc.html)

[To list Dynamic or segment routing LSPs](ai8ha35pod.html)

[To view ping results on a BFD LSP session for a Dynamic LSP](ToViewPingResultsOnBFDSession-AC.html)

[To run an OAM validation test for a Dynamic or segment routing LSP](ai8ha35poe.html)

[To create a Point-to-Multipoint LSP](ai8ha35pof.html)

[To view an MVPN Point-to-Multipoint LSP object](ai8ha35poj.html)

[To create a Manual Bypass LSP](ai8ha35pok.html)

[To configure a Manual Bypass LSP](ai8ha35poo.html)

[To configure an LSP path](ai8ha35pop.html)

[To create an LSP path using a tunnel template](ai8ha35pou.html)

[To configure an LSP Path optimization policy](ai8ha35pox.html)

[To terminate an LSP Path optimization policy that is in progress](ai8ha35po8.html)

[To view LSP Path optimization policy results](ai8ha35po9.html)

[To view detour and bypass path information](ai8ha35ppa.html)

[To view exclude route object information](ai8ha35ppb.html)

[To create an LSP template MVPN policy](ai8ha35ppc.html)

[To view LSP templates for MVPN created using CLI](ai8ha35ppd.html)

[To view LSPs created by One-hop P2P and Mesh P2P templates](ai8ha35ppe.html)

[To list and view MPLS objects](ai8ha35ppf.html)

[To create an administrative LSP tag](admin_tag_create.html)

[To create an administrative tag policy](admin_tag_policy_create.html)

[To create a reserved label block](mpls_res_label_block.html)

[Workflow to collect segment routing TE LSP rate PM statistics](WFRateStat.html)

[32\. MPLS-TP](ai8ha35ppg.html)

[MPLS-TP overview](ai8ha35pph.html)

[MPLS-TP overview](MPLS-TP-overview.html)

[MPLS-TP workflow and procedures](ai8ha35ppl.html)

[Workflow to configure MPLS-TP](ai8ha35ppk.html)

[To enable MPLS-TP on a routing instance](ai8ha35ppm.html)

[To configure MPLS-TP on a routing instance](ai8ha35ppo.html)

[To create an MPLS-TP LSP](ai8ha35ppr.html)

[To create an MPLS-TP LSR cross-connect path](ai8ha35ppu.html)

[To create a bidirectional MPLS-TP LSP](ai8ha35ppx.html)

[33\. Service tunnels](ai8ha35pyz.html)

[Service tunnel overview](ai8ha35py0.html)

[Service tunnel overview](Service-tunnel-overview.html)

[Tunnel selection profiles](ovr_tsp-jw.html)

[IP/MPLS service tunnels](IPMPLS-service-tunnels.html)

[Ethernet G.8031 tunnels](ai8ha35py4.html)

[Ethernet G.8032 rings](Ethernet-G.8032-rings.html)

[Ethernet G.8032 rings](ai8ha35py6.html)

[L2TPv3 service tunnels](ai8ha35pzf.html)

[Configuring service tunnel workflows and procedures](ai8ha35pzj.html)

[Workflow to configure service tunnels](ai8ha35pzg.html)

[Workflow to configure Ethernet G.8032 rings](ai8ha35pzi.html)

[To create an IP/MPLS service tunnel](ai8ha35pzk.html)

[To configure a service tunnel](ai8ha35pz3.html)

[To configure an L2TPv3 service tunnel](ai8ha35pz4.html)

[To create an SDP using a tunnel template](ai8ha35pz5.html)

[To create a tunnel selection profile](ai8ha35pz6.html)

[To configure an Ethernet tunnel endpoint](ai8ha35pz7.html)

[To configure an Ethernet tunnel](ai8ha35p0a.html)

[To configure an Ethernet Ring Element](ai8ha35p0j.html)

[To configure an OmniSwitch Ethernet Ring Element](ai8ha35p0m.html)

[To create an Ethernet G.8032 ring](ai8ha35p0s.html)

[To create an Ethernet G.8032v2 ring on an OmniSwitch](TCrtAnEthrnG8032V2RngOnAnOmnSw.html)

[To configure a transit service on an Ethernet ring](ai8ha35p1c.html)

[To manually update data services on an Ethernet ring](EthRingUpdateData.html)

[To discover service tunnels](ai8ha35p1d.html)

[To discover flow-through services](ai8ha35p1e.html)

[To view and manage service tunnels and tunnel elements](ai8ha35p1f.html)

[To view the service tunnel topology](ai8ha35p1g.html)

[To run an OAM validation test on a service tunnel](ai8ha35p1h.html)

[To perform an Ethernet G.8032 ring audit](ai8ha35p1j.html)

[34\. IPsec](ai8ha35pga.html)

[Overview](ai8ha35pgb.html) 

[IPsec VPNs](ai8ha35pgf.html)

[Multichassis IPsec](ai8ha35pgm.html)

[Sample video wholesale IPsec configuration](ai8ha35pgn.html)

[Workflow to configure IPsec](Workflow-to-configure-IPsec.html)

[Workflow to configure IPsec VPNs](Workflow-to-configure-IPsec-VPNs.html)

[Workflow to enable BFD over a static LAN-to-LAN IPsec tunnel](WrkflTEnblBFDOvrASttcLANTLANIPscT.html)

[To configure an IPsec IKE policy](ai8ha35pgv.html)

[To configure an IKE transform policy](IKE_transform_ks.html)

[To configure an IPsec transform policy](ai8ha35pgy.html)

[To configure an IPsec static security association](ai8ha35pg0.html)

[To configure an IPsec tunnel template](ai8ha35pg1.html)

[To configure an IPsec security policy](ai8ha35pg5.html)

[To configure a RADIUS authentication policy](ai8ha35pha.html)

[To configure a RADIUS accounting policy](ai8ha35phb.html)

[To configure an IPsec traffic selector list](ai8ha35phc.html)

[T

[web_fetch content truncated: showing first 60000 of 152257 bytes. Full content saved to: C:\Users\elzoy\.grok\sessions\C%3A%5CUsers%5Celzoy%5CCode%5Cnsp-grok-2411\01a06e01-5cac-7511-bc2a-a0dd4373fd76\web_fetch\1.md. Use `read_file` with offsets and limits to read it in chunks.]

### Turn 17 (Assistant)
No hace falta que me pases toda la suite. El texto de las guías públicas de 24.11 ya lo puedo leer. Lo que **no** tengo, y sí necesito para replicar la app, es lo visual y el modelo de objetos.

Pasame **lote 1** primero. Con eso arrancamos. El resto puede esperar.

## Lote 1 — imprescindible (GUI + MPLS)

Son 3 cosas. Preferí **PDF** o **capturas**. El HTML a veces no trae las figuras.

| # | Documento | Qué extraer | Por qué |
|---|---|---|---|
| 1 | **NSP NFM-P Classic Management User Guide 24.11** (`3HE-20021-AAAC-TQZZA`) | Capítulos **1 a 4** completos, **con figuras**: GUI, workspaces, navigation tree, topology maps | Es el look & feel del cliente Java: menús, forms, árbol, mapas |
| 2 | El mismo User Guide | Capítulo **31 MPLS**, **32 MPLS-TP**, **33 Service tunnels** (overview + workflows + figuras de forms) | Es el dominio que vos querés gestionar |
| 3 | **Capturas de tu NFM-P real** (si tenés lab o cliente) | Ver lista abajo | Vale más que cualquier PDF: color, iconos, menús reales de 24.11 |

### Capturas que más me sirven (si podés)

Desde un cliente NFM-P 24.11, así como lo ves vos:

1. Ventana principal completa (menú + toolbar + árbol + mapa/forms + alarmas)
2. Menú `File / View / Manage / Application / Tools / Administration / Help` desplegado (o todos)
3. Árbol de navegación: vistas Equipment y Routing
4. Mapa de topología física (Equipment)
5. Mapa MPLS / Service Tunnel Topology
6. Un **list form** (ej. Manage → Equipment, o Manage → MPLS → Dynamic LSPs)
7. Un **configuration form** con pestañas (ej. properties de un 7750, o de un LSP)
8. Ventana de **alarmas** (Faults)
9. Equipment Manager / inventario de un NE (shelf → card → port)
10. Form “Create Dynamic LSP” o “Create Service Tunnel (SDP)”

Si no tenés GUI a mano, con el PDF del User Guide (caps 1–4 + 31–33) alcanza para el esqueleto.

## Lote 2 — después, cuando definamos módulos

No los busques todavía. Los pido cuando toque cada módulo:

| Documento | Cuándo |
|---|---|
| **CPAM User Guide 24.11** — caps Topology + MPLS topology | Mapas IGP/OSPF/ISIS/MPLS con highlight de LSPs |
| **XML API Developer Guide 24.11** (`3HE-20022`) — overview + inventory + MPLS + services | Modelo de objetos (`equipment`, `mpls`, `service`, `fm`) |
| **Portal** `network.developer.nokia.com/learn/24_11/` — índice de la página + APIs NFM-P REST (`managedobjects`, `equipment`, `mpls`, `fm`) | Endpoints reales 24.11 |
| **Statistics Management Guide** | Si hacemos stats/gráficos |
| **NSP User Guide 24.11** (la GUI **web** de NSP, no la Java) | Solo si querés mix NSP web + NFM-P clásico |

## Lo que no hace falta

Installation, Planning, Security Hardening, CLM, Wavence, Analytics Report Catalog, System Administrator (salvo users/roles si más adelante hay login).

## Cómo pasármelo

Lo que mejor funciona acá:

- **PDF** del User Guide (aunque sea solo caps 1–4 y 31–33)
- **PNG/JPG** de las capturas
- Si el PDF es enorme, recortes de esas secciones

No hace falta zip de toda la documentación Nokia.

Cuando tengas el lote 1, lo leemos y te digo el alcance de la réplica web (pantallas y flujos) antes de codear.

### Turn 18 (Human)
<user_query>
C:\Users\elzoy\Downloads\User_Guide_Issue_1.pdf
C:\Users\elzoy\Downloads\NSP_System_Administrator_Guide_Issue_11.pdf
C:\Users\elzoy\Downloads\Statistics_Management_Guide_Issue_1.pdf

Algo que es importante quiero que la interfaz del usuario sea un CLI hecho en python no replicar la actual, me gustaria que el usuario haga el login con sus credenciales y quede en un shell que le permita navegar por consola. Puede ser una interfaz similar a la de Grok 4.6
</user_query>

### Turn 19 (Assistant)
Cambio de enfoque: no replicamos la GUI Java, sino un CLI en Python con login y un shell de navegación. Voy a leer los PDFs y la interfaz de Grok para armar algo coherente.
[tool_request: list_dir]
- target_directory: C:\Users\elzoy\Code\nsp-grok-2411
[tool_request: list_dir]
- target_directory: C:\Users\elzoy\.grok\docs\user-guide
[tool_request: read_file]
- target_file: C:\Users\elzoy\Downloads\User_Guide_Issue_1.pdf
- format: text
- pages: 1-8
[tool_request: read_file]
- target_file: C:\Users\elzoy\Downloads\NSP_System_Administrator_Guide_Issue_11.pdf
- format: text
- pages: 1-8
[tool_request: read_file]
- target_file: C:\Users\elzoy\Downloads\Statistics_Management_Guide_Issue_1.pdf
- format: text
- pages: 1-8

### Turn 20 (Function)
[tool_response]
- C:\Users\elzoy\Code\nsp-grok-2411/


### Turn 21 (Function)
[tool_response]
- C:\Users\elzoy\.grok\docs\user-guide/
  - 01-getting-started.md
  - 02-authentication.md
  - 03-keyboard-shortcuts.md
  - 04-slash-commands.md
  - 05-configuration.md
  - 06-theming.md
  - 07-mcp-servers.md
  - 08-skills.md
  - 09-plugins.md
  - 10-hooks.md
  - 11-custom-models.md
  - 12-project-rules.md
  - 13-memory.md
  - 14-headless-mode.md
  - 15-agent-mode.md
  - 16-subagents.md
  - 17-sessions.md
  - 18-sandbox.md
  - 19-plan-mode.md
  - 20-background-tasks.md
  - 21-terminal-support.md
  - 22-permissions-and-safety.md
  - 23-dashboard.md
  - 24-monitoring-usage.md
  - 25-status-line.md
  - 26-config-reference.md
  - 27-grok-clone.md

### Turn 22 (Function)
[tool_response]
1→--- Page 1 ---
2→NSP
3→Network Services Platform
4→Network Functions Manager - Packet (NFM-P)
5→Release 24.11
6→
7→
8→Statistics Management Guide
9→
10→3HE-20019-AAAC-TQZZA
11→IssueDecember 1
12→ 2024
13→© 2024 Nokia.
14→Use subject to Terms available at: www.nokia.com/terms
15→--- Page 2 ---
16→NFM-P
17→
18→
19→Legal notice
20→
21→Nokia is committed to diversity and inclusion. We are continuously reviewing our customer documentation and consulting with standards
22→bodies to ensure that terminology is inclusive and aligned with the industry. Our future customer documentation will be updated accordingly.
23→
24→Nokia proprietary and confidential information, which may not be distributed or
25→of Nokia.
26→for use by Nokia’s customers (“You”/”Your”) in connection with a product purchased
27→         of Companies. Use this document as agreed. You agree to notify Nokia of
28→you elect to use this document for any purpose(s) for which it is not intended,
29→may make or actions You may take will be based upon Your independent judgment
30→to make changes to this document without notice. At all times, the controlling
31→may be modified.
32→KIND, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
33→         RELIABILITY, TITLE, NON-INFRINGEMENT, MERCHANTABILITY OR FITNESS
34→         RELATION TO THE CONTENT OF THIS DOCUMENT. IN NO EVENT WILL
35→BUT NOT LIMITED TO SPECIAL, DIRECT, INDIRECT, INCIDENTAL OR
36→LIMITED TO LOSS OF PROFIT, REVENUE, BUSINESS INTERRUPTION, BUSINESS
37→THE USE OF THIS DOCUMENT OR THE INFORMATION IN IT, EVEN IN THE
38→         DOCUMENT OR ITS CONTENT.
39→Nokia is a registered trademark of Nokia Corporation. Other product names
40→         owners.
41→This document includes 
42→   
43→ 
44→ 
45→       disclosed to any third parties without
46→the prior written consent 
47→
48→This document is intended 
49→ 
50→     
51→ or licensed from any
52→company within Nokia Group 
53→     
54→         any errors you may find in this
55→document; however, should 
56→   
57→     
58→ You understand and warrant that
59→any determinations You 
60→ 
61→       
62→   and analysis of the content of
63→this document.
64→
65→Nokia reserves the right 
66→     
67→         version is the one available on
68→Nokia’s site.
69→
70→No part of this document 
71→
72→NO WARRANTY OF ANY 
73→ 
74→ 
75→     
76→ ANY WARRANTY OF
77→AVAILABILITY, ACCURACY, 
78→   
79→ 
80→     FOR A PARTICULAR
81→PURPOSE, IS MADE IN 
82→ 
83→     
84→       NOKIA BE LIABLE FOR ANY
85→DAMAGES, INCLUDING 
86→     
87→ 
88→   CONSEQUENTIAL OR ANY LOSSES,
89→SUCH AS BUT NOT 
90→ 
91→ 
92→ 
93→ 
94→ OPPORTUNITY OR DATA
95→THAT MAY ARISE FROM 
96→   
97→       CASE OF ERRORS IN OR
98→OMISSIONS FROM THIS 
99→   
100→
101→Copyright and trademark: 
102→   
103→       mentioned in this document may be
104→trademarks of their respective 
105→
106→© 2024 Nokia.
107→
108→
109→© 2024 
110→Release 24.11
111→           
112→ 2024
113→2
114→3HE-20019-AAAC-TQZZA
115→Issue 1
116→--- Page 3 ---
117→Contents
118→
119→
120→Contents
121→
122→About this document ............................................................................................................................................7
123→
124→Part I: Statistics overview ....................................................................................................................................9
125→
126→1 Statistics management................................................................................................................................11
127→1.1 Statistics management in the NFM-P................................................................................................ 11
128→1.2 NFM-P statistics types....................................................................................................................... 13
129→1.3 NFM-P statistics scalability................................................................................................................ 15
130→1.4 NFM-P statistics and OSS applications............................................................................................. 16
131→
132→Part II: Statistics collection configuration ........................................................................................................17
133→
134→2 Statistics collection.....................................................................................................................................19
135→2.1 Statistics collection in the NFM-P...................................................................................................... 19
136→2.2 To create and manage custom statistics aggregators....................................................................... 23
137→2.3 Statistics policies............................................................................................................................... 24
138→
139→3 Performance statistics collection ...............................................................................................................29
140→3.1 Collecting performance statistics ...................................................................................................... 29
141→3.2 Workflow for performance statistics collection .................................................................................. 30
142→3.3 To create or modify an NE MIB statistics policy using a top-down method....................................... 31
143→3.4 To modify an NE MIB statistics policy using a bottom-up method..................................................... 32
144→3.5 To create or modify a specific MIB statistics policy using a top-down method.................................. 33
145→3.6 To create or modify a specific MIB statistics policy using a bottom-up method ................................ 35
146→3.7 To assign the default 1830 VWM OSU performance management policy to 1830 devices ..............36
147→3.8 To configure polling for a MIB statistics class.................................................................................... 37
148→3.9 To configure a statistics policy for MIB statistics ............................................................................... 38
149→3.10 To delete performance statistics records........................................................................................... 38
150→
151→4 Accounting statistics ...................................................................................................................................41
152→4.1 Accounting statistics collection.......................................................................................................... 41
153→4.2 To create and manage periodic accounting statistics calculations.................................................... 44
154→4.3 Workflow for accounting statistics collection ..................................................................................... 45
155→4.4 To configure a file policy.................................................................................................................... 47
156→4.5 To configure an accounting policy ..................................................................................................... 48
157→4.6 To configure a statistics policy for accounting statistics on a SAP or an SDP................................... 50
158→4.7 To configure a statistics policy for accounting statistics on a network interface................................ 52
159→4.8 To configure a statistics policy for accounting statistics on a subscriber........................................... 53
160→
161→
162→© 2024 
163→ 
164→           
165→ 2024 1
166→3
167→--- Page 4 ---
168→  2024
169→
170→
171→Contents
172→
173→
174→ To configure a statistics policy for AA accounting statistics on a subscriber ..................................... 54
175→4.10 To configure a statistics policy for an AA accounting statistics application........................................ 55
176→4.11 To configure a statistics policy for an AA accounting statistics application group ............................. 56
177→4.12 To configure a statistics policy for an AA accounting statistics protocol ............................................ 57
178→4.13 To configure ingress and egress accounting policies for an LSP...................................................... 58
179→4.14 To delete accounting statistics records ............................................................................................. 60
180→
181→5 Flow statistics collection .............................................................................................................................61
182→5.1 Flow statistics collection in the NFM-P.............................................................................................. 61
183→5.2 Workflow to configure flow statistics collection.................................................................................. 62
184→5.3 Workflow to configure AA Cflowd special study statistics collection.................................................. 64
185→5.4 To configure flow statistics aggregation ............................................................................................ 64
186→5.5 To set upload targets and policies..................................................................................................... 69
187→5.6 To configure the transfer of results files ............................................................................................ 71
188→5.7 To configure AA filters........................................................................................................................ 73
189→5.8 To configure an AA Cflowd special-study policy ................................................................................ 75
190→5.9 To configure AA subnet summarization filters ................................................................................... 78
191→5.10 To configure the AA flow data persistence ........................................................................................ 80
192→5.11 To specify the NEs for flow statistics collection ................................................................................. 81
193→5.12 To extract an NFM-P network data snapshot .................................................................................... 82
194→5.13 To export IPDR statistics files to a different format............................................................................ 83
195→
196→6 Server performance statistics .....................................................................................................................87
197→6.1 Server performance statistics collection............................................................................................ 87
198→6.2 Workflow for server performance statistics collection ....................................................................... 87
199→6.3 To configure a statistics policy for server performance statistics ...................................................... 87
200→6.4 To configure a statistics collection policy for server performance statistics ...................................... 88
201→6.5 To delete server performance statistics records................................................................................ 89
202→
203→Part III: Statistics presentation ..........................................................................................................................91
204→
205→7 Statistics presentation .................................................................................................................................93
206→7.1 Statistics presentation in the NFM-P................................................................................................. 93
207→
208→8 Viewing statistics.........................................................................................................................................97
209→8.1 Viewing statistics in the NFM-P......................................................................................................... 97
210→8.2 Workflow for viewing statistics........................................................................................................... 97
211→8.3 To view on-demand statistics ............................................................................................................ 98
212→8.4 To view statistics for a set of objects ................................................................................................. 99
213→8.5 To view network accounting statistics ............................................................................................. 100
214→
215→
216→     
217→© 2024 
218→   
219→4
220→ 1
221→--- Page 5 ---
222→Contents
223→
224→
225→ 
226→
227→
228→ To
229→
230→
231→ 2024
232→
233→
234→ view performance ........................................................................................................ 101
235→8.7 To view server performance statistics ............................................................................................. 102
236→8.8 To view service accounting statistics............................................................................................... 103
237→8.9 To view subscriber accounting statistics ......................................................................................... 104
238→8.10 To view per-subscriber AA accounting statistics.............................................................................. 105
239→8.11 To view AA accounting statistics for an application ......................................................................... 106
240→8.12 To view AA accounting statistics for an application group ............................................................... 107
241→8.13 To view AA accounting statistics for a protocol................................................................................ 109
242→
243→9 Graphing statistics.....................................................................................................................................111
244→9.1 Graphing statistics overview............................................................................................................ 111
245→9.2 Workflow for graphing statistics....................................................................................................... 116
246→9.3 To create a statistics graph.............................................................................................................. 116
247→9.4 To modify a statistics graph............................................................................................................. 121
248→9.5 To plot utilization statistics............................................................................................................... 122
249→9.6 To create a customized plotter profile ............................................................................................. 123
250→9.7 To plot statistics using a plotter profile ............................................................................................ 124
251→9.8 To manage plotter profiles............................................................................................................... 124
252→
253→Part IV: Statistics content ................................................................................................................................127
254→
255→10 Statistics record format .............................................................................................................................129
256→10.1 Statistics record format in the NFM-P ............................................................................................. 129
257→10.2 Performance statistics..................................................................................................................... 129
258→10.3 Accounting statistics........................................................................................................................ 131
259→10.4 Server performance statistics.......................................................................................................... 136
260→10.5 Nokia internal statistics ................................................................................................................... 147
261→
262→
263→     
264→© 2024 
265→   
266→ 1
267→5
268→--- Page 6 ---
269→Contents
270→
271→                 © 2024 Nokia.
272→Use subject to Terms available at: www.nokia.com/terms
273→                                  3HE-20019-AAAC-TQZZA
274→   
275→ 
276→ 
277→  2024
278→6
279→ 1
280→--- Page 7 ---
281→About
282→
283→
284→About
285→
286→
287→ this document
288→
289→
290→ this document
291→Purpose
292→The NSP NFM-P Statistics Management Guide describes statistics management using the NFM-P.
293→
294→
295→Scope
296→
297→Supported performance and accounting statistics are searchable in the Statistics Search Tool.
298→
299→
300→Thefunctions scope that of canthis bedocument accomplished is limited from to thethe NFM-PNFM-P. Java Many GUI configuration, are also delivered monitoring, in NSP.and assurance Readers
301→
302→
303→Safety
304→
305→
306→ofmore this efficient NFM-P and guide sophisticated should familiarize features themselves for network with and the service capabilities management. of the NSP, which often offer
307→
308→
309→ information
310→Forwhere your risks safety, of damage this document to personnel, contains equipment, safety statements. and operation Safety may statements exist. Failure are given to follow at points the
311→
312→
313→Document
314→
315→directions in a safety statement may result in serious consequences.
316→
317→ support
318→
319→Customer documentation and product support URLs:
320→• Documentation Center
321→• Technical support
322→
323→How to comment
324→Please send your feedback to documentation.feedback@nokia.com.
325→
326→
327→© 2024 
328→ 
329→           
330→ 2024 1
331→7
332→--- Page 8 ---
333→About this document
334→
335→                 © 2024 Nokia.
336→Use subject to Terms available at: www.nokia.com/terms
337→                                  3HE-20019-AAAC-TQZZA
338→   
339→ 
340→ 
341→  2024
342→8
343→ 1

### Turn 23 (Function)
[tool_response]
1→--- Page 1 ---
2→NSP
3→Network Services Platform
4→Release 24.11
5→
6→
7→System Administrator Guide
8→
9→3HE-20030-AAAC-TQZZA
10→IssueMay 2026 11
11→
12→© 2026 Nokia.
13→Use subject to Terms available at: www.nokia.com/terms
14→--- Page 2 ---
15→NSP
16→
17→
18→Legal notice
19→
20→Nokia is committed to diversity and inclusion. We are continuously reviewing our customer documentation and consulting with standards
21→bodies to ensure that terminology is inclusive and aligned with the industry. Our future customer documentation will be updated accordingly.
22→
23→Nokia proprietary and confidential information, which may not be distributed or
24→of Nokia.
25→for use by Nokia’s customers (“You”/”Your”) in connection with a product purchased
26→         of Companies. Use this document as agreed. You agree to notify Nokia of
27→you elect to use this document for any purpose(s) for which it is not intended,
28→may make or actions You may take will be based upon Your independent judgment
29→to make changes to this document without notice. At all times, the controlling
30→may be modified.
31→KIND, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
32→         RELIABILITY, TITLE, NON-INFRINGEMENT, MERCHANTABILITY OR FITNESS
33→         RELATION TO THE CONTENT OF THIS DOCUMENT. IN NO EVENT WILL
34→BUT NOT LIMITED TO SPECIAL, DIRECT, INDIRECT, INCIDENTAL OR
35→LIMITED TO LOSS OF PROFIT, REVENUE, BUSINESS INTERRUPTION, BUSINESS
36→THE USE OF THIS DOCUMENT OR THE INFORMATION IN IT, EVEN IN THE
37→         DOCUMENT OR ITS CONTENT.
38→Nokia is a registered trademark of Nokia Corporation. Other product names
39→         owners.
40→This document includes 
41→   
42→ 
43→ 
44→       disclosed to any third parties without
45→the prior written consent 
46→
47→This document is intended 
48→ 
49→     
50→ or licensed from any
51→company within Nokia Group 
52→     
53→         any errors you may find in this
54→document; however, should 
55→   
56→     
57→ You understand and warrant that
58→any determinations You 
59→ 
60→       
61→   and analysis of the content of
62→this document.
63→
64→Nokia reserves the right 
65→     
66→         version is the one available on
67→Nokia’s site.
68→
69→No part of this document 
70→
71→NO WARRANTY OF ANY 
72→ 
73→ 
74→     
75→ ANY WARRANTY OF
76→AVAILABILITY, ACCURACY, 
77→   
78→ 
79→     FOR A PARTICULAR
80→PURPOSE, IS MADE IN 
81→ 
82→     
83→       NOKIA BE LIABLE FOR ANY
84→DAMAGES, INCLUDING 
85→     
86→ 
87→   CONSEQUENTIAL OR ANY LOSSES,
88→SUCH AS BUT NOT 
89→ 
90→ 
91→ 
92→ 
93→ OPPORTUNITY OR DATA
94→THAT MAY ARISE FROM 
95→   
96→       CASE OF ERRORS IN OR
97→OMISSIONS FROM THIS 
98→   
99→
100→Copyright and trademark: 
101→   
102→       mentioned in this document may be
103→trademarks of their respective 
104→
105→© 2026 Nokia.
106→
107→
108→© 2026 
109→Release 24.11
110→           
111→ 2026
112→2
113→3HE-20030-AAAC-TQZZA
114→Issue 11
115→--- Page 3 ---
116→Contents
117→
118→
119→Contents
120→
121→About this document
122→
123→Part I: NSP administration
124→
125→1 NSP administration
126→1.1 What
127→1.2 How
128→1.3 How
129→
130→2 NSP access
131→2.1 What
132→2.2 How
133→2.3 How
134→2.4 How
135→2.5 How
136→2.6 How
137→2.7 How
138→
139→3 Map layout
140→3.1 What
141→3.2 Workflow:
142→3.3 Workflow:
143→3.4 How
144→3.5 How
145→3.6 How
146→3.7 How
147→3.8 How
148→3.9 How
149→3.10 How
150→3.11 How
151→3.12 How
152→3.13 How
153→3.14 How
154→3.15 How
155→3.16 How
156→3.17 How
157→3.18 What
158→
159→
160→  2026 11
161→
162→
163→..........................................................................................................................................17
164→
165→ basics .....................................................................................................................19
166→
167→ overview ......................................................................................................................21
168→ does NSP administration involve? ......................................................................................... 21
169→ do I receive product and documentation alerts?..................................................................... 21
170→ do I view technical-support alerts? ......................................................................................... 22
171→
172→ and UI administration .............................................................................................................25
173→ is NSP access administration? .............................................................................................. 25
174→ do I enable single-address DR NSP system access?............................................................. 27
175→ do I configure NSP system settings? ...................................................................................... 28
176→ do I configure alarm-severity colors?...................................................................................... 29
177→ do I configure linked URLs?.................................................................................................... 30
178→ do I configure event logging?.................................................................................................. 31
179→ do I configure an e-mail server for notifications? .................................................................... 32
180→
181→....................................................................................................................................................35
182→ is the Map Layout? ................................................................................................................ 35
183→ create and configure a physical map layout ................................................................... 40
184→ create and configure an IGP map layout........................................................................ 40
185→ do I create a physical map layout? ......................................................................................... 41
186→ do I create an IGP map layout? .............................................................................................. 42
187→ do I create a region for a physical map layout? ...................................................................... 43
188→ do I create a region for an IGP map layout? ........................................................................... 44
189→ do I place a region on the map layout?................................................................................... 45
190→ do I create a zone in the map layout?..................................................................................... 46
191→ do I associate NEs or routers with a region? .......................................................................... 47
192→ do I enable GEO positioning for NEs and routers?................................................................. 48
193→ do I rename a layout? ............................................................................................................. 49
194→ do I select and move map objects? ........................................................................................ 50
195→ do I move an object to a specific GEO location? .................................................................... 50
196→ do I search for objects in the map layout? .............................................................................. 51
197→ do I cancel un-deployed changes to the map layout? ............................................................ 52
198→ do I reset warning messages?................................................................................................ 52
199→ are best practices when using the Map Layout? ................................................................... 53
200→
201→
202→© 2026 
203→           
204→3
205→--- Page 4 ---
206→  2026
207→
208→
209→Contents
210→
211→
212→4 Resource pool management .......................................................................................................................55
213→4.1 How are resource pools used with programmable functions? ........................................................ 55
214→4.2 How do I search for a resource pool? ............................................................................................. 55
215→4.3 How do I view summary information for a resource pool? .............................................................. 56
216→4.4 How do I configure an IP address pool? ......................................................................................... 57
217→4.5 Why use IPv4 subnet re-purposing?............................................................................................... 58
218→4.6 How do I configure a string pool? ................................................................................................... 58
219→4.7 How do I configure an RD-RT pool? ............................................................................................... 59
220→4.8 How do I configure a Numeric pool?............................................................................................... 60
221→4.9 What are threshold policies?........................................................................................................... 61
222→4.10 How do I configure a threshold policy? ........................................................................................... 62
223→4.11 How do I reserve resources? .......................................................................................................... 63
224→4.12 How do I release a resource? ......................................................................................................... 64
225→4.13 How do I commit a resource? ......................................................................................................... 65
226→
227→5 NSP File Server ............................................................................................................................................67
228→5.1 What is the NSP File Server? ......................................................................................................... 67
229→5.2 Configuring file purge policies......................................................................................................... 67
230→5.3 How do I use the NSP File Server? ................................................................................................ 68
231→5.4 How do I configure file purge policies? ........................................................................................... 72
232→
233→Part II: NSP security administration ..................................................................................................................75
234→
235→6 SELinux administration...............................................................................................................................77
236→6.1 Overview ......................................................................................................................................... 77
237→Deploying SELinux ......................................................................................................................................78
238→6.2 What is SELinux?............................................................................................................................ 78
239→6.3 How do I enable SELinux on an NSP deployer VM? ...................................................................... 79
240→6.4 How do I enable SELinux in an NSP cluster? ................................................................................. 81
241→SELinux for Classic Management ..............................................................................................................85
242→6.5 What does enabling NFM-P SELinux involve? ............................................................................... 85
243→6.6 How do I enable SELinux on the NFM-P? ...................................................................................... 85
244→6.7 How do I enable SELinux enforcing mode for the NFM-P? ............................................................ 90
245→SELinux troubleshooting ............................................................................................................................93
246→6.8 What does NSP SELinux troubleshooting involve? ........................................................................ 93
247→6.9 How do I switch between SELinux modes on NSP system components?...................................... 93
248→6.10 How do I troubleshoot SELinux on NSP system components? ...................................................... 95
249→6.11 How do I troubleshoot SELinux on the NFM-P? ............................................................................. 97
250→
251→
252→© 2026 
253→           
254→4
255→ 11
256→--- Page 5 ---
257→Contents
258→
259→
260→7 TLS administration
261→7.1 Overview
262→What is NSP
263→7.2 NSP
264→7.3 Managing
265→7.4 Managing
266→NSP Kubernetes
267→7.5 How
268→7.6 How
269→NSP cluster
270→7.7 How
271→7.8 How
272→7.9 How
273→7.10 How
274→7.11 How
275→7.12 How
276→7.13 How
277→7.14 How
278→NSP component
279→7.15 How
280→7.16 How
281→7.17 How
282→7.18 How
283→7.19 How
284→
285→8 NSP user 
286→Local user
287→8.1 What
288→8.2 What
289→8.3 How
290→8.4 How
291→8.5 How
292→8.6 What
293→8.7 How
294→8.8 How
295→8.9 How
296→8.10 How
297→
298→
299→  2026 11
300→
301→
302→.....................................................................................................................................101
303→ ....................................................................................................................................... 101
304→ TLS administration? ............................................................................................................103
305→ TLS administration overview................................................................................................. 103
306→ Kubernetes infrastructure TLS ..................................................................................... 104
307→ NSP system TLS .......................................................................................................... 105
308→ TLS administration procedures ...................................................................................106
309→ do I update the K3s certificate for an NSP deployer VM?..................................................... 106
310→ do I update the Kubernetes registry TLS certificate?............................................................ 107
311→ TLS administration procedures ...........................................................................................109
312→ do I list the NSP Kubernetes secrets? .................................................................................. 109
313→ do I view the Kubernetes secret content?............................................................................. 109
314→ do I update the NSP issuer TLS artifacts? ............................................................................ 111
315→ do I update the custom NSP server TLS artifacts? ............................................................... 114
316→ do I add an NSP Kubernetes secret?.................................................................................... 117
317→ do I recreate the NSP Kubernetes secrets?.......................................................................... 119
318→ do I back up the NSP Kubernetes secrets? .......................................................................... 125
319→ do I restore the NSP Kubernetes secrets? ........................................................................... 126
320→ TLS configuration ..........................................................................................................128
321→ do I configure an NSP auxiliary database to request the NSP TLS certificate? ................... 128
322→ do I configure an NFM-P main server to request the NSP TLS certificate?.......................... 129
323→ do I configure an NFM-P auxiliary server to request the NSP TLS certificate? .................... 132
324→ do I enable TLS for NFM-P XML API clients? ....................................................................... 135
325→ do I disable TLS for NFM-P XML API clients? ...................................................................... 138
326→
327→security ......................................................................................................................................141
328→ management............................................................................................................................141
329→ is user management? .......................................................................................................... 141
330→ are the NSP user management requirements and restrictions?.......................................... 142
331→ do I create an NSP local user? ............................................................................................. 143
332→ do I import users and groups from NFM-P? ......................................................................... 144
333→ do I set global user session limits? ....................................................................................... 146
334→ are the user password policies? .......................................................................................... 148
335→ do I set global user password requirements? ....................................................................... 149
336→ do I modify a user account?.................................................................................................. 150
337→ do I suspend a local user account? ...................................................................................... 151
338→ do I configure user account event notifications?................................................................... 151
339→
340→
341→© 2026 
342→           
343→5
344→--- Page 6 ---
345→  2026
346→
347→
348→Contents
349→
350→
351→ User Access Control ..........................................................................................................................153
352→8.11 What is User Access Control? ...................................................................................................... 153
353→8.12 Workflow: Configure User Access Control .................................................................................... 155
354→8.13 How do I configure alarm access using roles? ............................................................................. 156
355→8.14 How do I configure a role? ............................................................................................................ 158
356→8.15 How do I set network resource access levels? ............................................................................. 161
357→8.16 How do I configure a user group?................................................................................................. 162
358→8.17 How do I enable User Access Control? ........................................................................................ 163
359→8.18 What are NSP operator roles and responsibilities? ...................................................................... 164
360→8.19 How do I update the NSP TLS certificate for LDAPS remote authentication? .............................. 165
361→User session management and logging ..................................................................................................167
362→8.20 What is user session management?............................................................................................. 167
363→8.21 How do I terminate user sessions?............................................................................................... 167
364→8.22 How do I send a message to active users? .................................................................................. 168
365→8.23 How do I view user events? .......................................................................................................... 169
366→8.24 How do I filter the event log view? ................................................................................................ 170
367→8.25 How do I apply or clear my advanced filters? ............................................................................... 171
368→8.26 How do I modify my advanced filters? .......................................................................................... 171
369→8.27 How do I set the User Activity Log to auto-refresh?...................................................................... 172
370→8.28 How do I set limits for log event retention? ................................................................................... 173
371→8.29 How do I export activity log events? ............................................................................................. 174
372→Network resource groups ..........................................................................................................................176
373→8.30 What are group directories and resource groups?........................................................................ 176
374→8.31 Workflow: create group directories and resource groups.............................................................. 176
375→8.32 How do I create a group directory?............................................................................................... 177
376→8.33 How do I configure a resource group?.......................................................................................... 177
377→8.34 How do I associate a resource group with a group directory? ...................................................... 179
378→8.35 How do I search for a management object? ................................................................................. 179
379→
380→9 Classic management security ...................................................................................................................181
381→Securing NFM-P system access ...............................................................................................................181
382→9.1 What is NFM-P system security? .................................................................................................. 181
383→9.2 How do I change an NFM-P main database password in a standalone system? ......................... 181
384→9.3 How do I change an NFM-P main database password in a redundant system? .......................... 184
385→9.4 How do I update the supported NFM-P TLS versions and ciphers? ............................................. 189
386→
387→
388→© 2026 
389→           
390→6
391→ 11
392→--- Page 7 ---
393→Contents
394→
395→
396→ 2026
397→
398→
399→NFM-P
400→
401→
402→ 
403→
404→
405→ user security..................................................................................................................................197
406→9.5 What is NFM-P user security? ...................................................................................................... 197
407→9.6 How do I manage NFM-P user accounts and groups? ................................................................. 198
408→9.7 What is user activity logging? ....................................................................................................... 202
409→9.8 How do I configure sample span rule?.......................................................................................... 207
410→9.9 Workflow: configure and manage NFM-P user security................................................................ 208
411→9.10 How do I reserve an admin account login?................................................................................... 210
412→9.11 How do I create a scope of command role?.................................................................................. 211
413→9.12 How do I create a scope of command profile?.............................................................................. 212
414→9.13 How do I create a span of control? ............................................................................................... 213
415→9.14 How do I create a span of control profile? .................................................................................... 214
416→9.15 How do I create a span rule? ........................................................................................................ 214
417→9.16 How do I create an NFM-P user group? ....................................................................................... 215
418→9.17 How do I add or remove workspaces for a user group? ............................................................... 216
419→9.18 How do I create an NFM-P user account? .................................................................................... 218
420→9.19 How do I copy an NFM-P user account? ...................................................................................... 219
421→9.20 How do I configure global user account and password expiry?.................................................... 220
422→9.21 How do I configure the GUI client inactivity timeout?.................................................................... 221
423→9.22 How do I configure the minimum allowable user name length?.................................................... 221
424→9.23 How do I configure authentication failure actions? ....................................................................... 222
425→9.24 How do I configure suspended account actions? ......................................................................... 222
426→9.25 How do I configure automated E-mail notification?....................................................................... 223
427→9.26 How do I list inactive user accounts?............................................................................................ 224
428→9.27 How do I suspend or reinstate an NFM-P user account? ............................................................. 224
429→9.28 How do I change an NFM-P user password? ............................................................................... 225
430→9.29 How do I update the admin-user password for NSP XML API access?........................................ 226
431→9.30 How do I disable an NFM-P user password?................................................................................ 227
432→9.31 How do I change the password of the current NFM-P user? ........................................................ 228
433→9.32 How do I export the local tab preferences of one or more users? ................................................ 228
434→9.33 How do I assign local tab preferences to users? .......................................................................... 229
435→9.34 How do I send a broadcast message to GUI clients? ................................................................... 230
436→9.35 How do I view and manage the active GUI client sessions? ........................................................ 230
437→9.36 How do I disconnect an XML API JMS client connection or remove a durable subscription? 231 ......
438→9.37 How do I view the user activity log?.............................................................................................. 232
439→9.38 How do I view the user activity associated with an object? .......................................................... 234
440→9.39 How do I change the maximum number of concurrent NFM-P admin operator positions?........... 234
441→9.40 How do I configure the number of allowed client sessions for a client delegate server?.............. 236
442→
443→
444→     
445→© 2026 
446→   
447→ 11
448→7
449→--- Page 8 ---
450→Contents
451→
452→
453→ How do I change the NFM-P Task Manager settings?.................................................................. 236
454→
455→
456→275
457→
458→
459→9.42 How do I export all workspaces and local tab preferences?......................................................... 238
460→9.43 How do I import workspaces and local tab preferences? ............................................................. 238
461→
462→10 Classic management NE security .............................................................................................................241
463→10.1 What is NFM-P NE security? ........................................................................................................ 241
464→10.2 What are RADIUS, TACACS+, and LDAP? .................................................................................. 242
465→10.3 What is device SSH security?....................................................................................................... 243
466→10.4 How do I restore support for disabled NE SSH algorithms? ......................................................... 243
467→10.5 What are CPM filters and traffic management? ............................................................................ 246
468→10.6 What is DoS protection? ............................................................................................................... 247
469→10.7 What is DDoS protection?............................................................................................................. 248
470→10.8 What is IP security? ...................................................................................................................... 250
471→10.9 HSM .............................................................................................................................................. 250
472→10.10 Workflow: manage NE user and device security........................................................................... 251
473→10.11 How do I configure a MAF? .......................................................................................................... 253
474→10.12 How do I configure a CPM filter? .................................................................................................. 254
475→10.13 How do I configure an NE DoS protection policy? ........................................................................ 257
476→10.14 How do I view NE DoS protection violations?............................................................................... 258
477→10.15 How do I configure an NE DDoS protection policy? ..................................................................... 259
478→10.16 How do I configure NE TLS client authentication?........................................................................ 261
479→10.17 How do I configure NE TLS server authentication? ...................................................................... 263
480→10.18 How do I configure TLS server group list? .................................................................................... 265
481→10.19 How do I configure TLS client group list?...................................................................................... 266
482→10.20 How do I configure TLS server signature list? .............................................................................. 266
483→10.21 How do I configure TLS client signature list? ................................................................................ 267
484→10.22 How do I configure a site user profile?.......................................................................................... 268
485→10.23 How do I configure a user account on a managed device? .......................................................... 269
486→10.24 How do I configure an NE password policy? ................................................................................ 270
487→10.25 How do I configure an LDAP site authentication policy?............................................................... 271
488→10.26 How do I configure an NE RADIUS authentication policy?........................................................... 272
489→10.27 How do I configure an NE TACACS+ authentication policy? ........................................................ 273
490→10.28 How do I configure an OmniSwitch RADIUS, TACACS+, or LDAP security authentication
491→policy?...........................................................................................................................................
492→10.29 How do I configure device system security settings? ................................................................... 275
493→10.30 How do I configure and manage PKI site security on an NE? ...................................................... 278
494→10.31 How do I configure a PKI certificate authority profile? .................................................................. 282
495→
496→
497→© 2026 
498→  2026
499→           
500→8
501→ 11

### Turn 24 (Function)
[tool_response]
1→--- Page 1 ---
2→NSP
3→Network Services Platform
4→Network Functions Manager - Packet (NFM-P)
5→Release 24.11
6→
7→
8→Classic Management User Guide
9→
10→3HE-20021-AAAC-TQZZA
11→IssueDecember 1
12→ 2024
13→© 2024 Nokia.
14→Use subject to Terms available at: www.nokia.com/terms
15→--- Page 2 ---
16→NFM-P
17→
18→
19→Legal notice
20→
21→Nokia is committed to diversity and inclusion. We are continuously reviewing our customer documentation and consulting with standards
22→bodies to ensure that terminology is inclusive and aligned with the industry. Our future customer documentation will be updated accordingly.
23→
24→Nokia proprietary and confidential information, which may not be distributed or
25→of Nokia.
26→for use by Nokia’s customers (“You”/”Your”) in connection with a product purchased
27→         of Companies. Use this document as agreed. You agree to notify Nokia of
28→you elect to use this document for any purpose(s) for which it is not intended,
29→may make or actions You may take will be based upon Your independent judgment
30→to make changes to this document without notice. At all times, the controlling
31→may be modified.
32→KIND, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
33→         RELIABILITY, TITLE, NON-INFRINGEMENT, MERCHANTABILITY OR FITNESS
34→         RELATION TO THE CONTENT OF THIS DOCUMENT. IN NO EVENT WILL
35→BUT NOT LIMITED TO SPECIAL, DIRECT, INDIRECT, INCIDENTAL OR
36→LIMITED TO LOSS OF PROFIT, REVENUE, BUSINESS INTERRUPTION, BUSINESS
37→THE USE OF THIS DOCUMENT OR THE INFORMATION IN IT, EVEN IN THE
38→         DOCUMENT OR ITS CONTENT.
39→Nokia is a registered trademark of Nokia Corporation. Other product names
40→         owners.
41→This document includes 
42→   
43→ 
44→ 
45→       disclosed to any third parties without
46→the prior written consent 
47→
48→This document is intended 
49→ 
50→     
51→ or licensed from any
52→company within Nokia Group 
53→     
54→         any errors you may find in this
55→document; however, should 
56→   
57→     
58→ You understand and warrant that
59→any determinations You 
60→ 
61→       
62→   and analysis of the content of
63→this document.
64→
65→Nokia reserves the right 
66→     
67→         version is the one available on
68→Nokia’s site.
69→
70→No part of this document 
71→
72→NO WARRANTY OF ANY 
73→ 
74→ 
75→     
76→ ANY WARRANTY OF
77→AVAILABILITY, ACCURACY, 
78→   
79→ 
80→     FOR A PARTICULAR
81→PURPOSE, IS MADE IN 
82→ 
83→     
84→       NOKIA BE LIABLE FOR ANY
85→DAMAGES, INCLUDING 
86→     
87→ 
88→   CONSEQUENTIAL OR ANY LOSSES,
89→SUCH AS BUT NOT 
90→ 
91→ 
92→ 
93→ 
94→ OPPORTUNITY OR DATA
95→THAT MAY ARISE FROM 
96→   
97→       CASE OF ERRORS IN OR
98→OMISSIONS FROM THIS 
99→   
100→
101→Copyright and trademark: 
102→   
103→       mentioned in this document may be
104→trademarks of their respective 
105→
106→© 2024 Nokia.
107→
108→
109→© 2024 
110→Release 24.11
111→           
112→ 2024
113→2
114→3HE-20021-AAAC-TQZZA
115→Issue 1
116→--- Page 3 ---
117→Contents
118→
119→
120→Contents
121→
122→About this document ..........................................................................................................................................73
123→
124→Part I: Getting started .........................................................................................................................................75
125→
126→1 NFM-P GUI....................................................................................................................................................77
127→GUI overview ................................................................................................................................................77
128→1.1 GUI workspace elements .................................................................................................................. 77
129→1.2 GUI customization............................................................................................................................. 78
130→1.3 Additional GUI operations ................................................................................................................. 80
131→NFM-P forms.................................................................................................................................................82
132→1.4 Forms overview................................................................................................................................. 82
133→1.5 List forms........................................................................................................................................... 83
134→1.6 Configuration forms........................................................................................................................... 84
135→NFM-P searches ...........................................................................................................................................92
136→1.7 Search overview................................................................................................................................ 92
137→1.8 Searching tips ................................................................................................................................... 95
138→Procedures for opening and closing the GUI ............................................................................................98
139→1.9 To open a single-user GUI client configured for one NFM-P system ................................................ 98
140→1.10 To open a single-user GUI client configured for multiple NFM-P systems ...................................... 100
141→1.11 To open the NFM-P GUI through a client delegate server .............................................................. 103
142→1.12 To close the NFM-P GUI ................................................................................................................. 104
143→Procedures for using the GUI ...................................................................................................................105
144→1.13 To manage the display of windows and forms ................................................................................ 105
145→1.14 To save or open a set of forms for quick access ............................................................................. 106
146→1.15 To manage a window or form as an external window ..................................................................... 107
147→1.16 To send a text message to other NFM-P users............................................................................... 108
148→1.17 To use configuration forms to configure or view parameters........................................................... 109
149→1.18 To manage configuration forms with built-in navigation trees.......................................................... 110
150→1.19 To modify multiple objects at one time (multi-edit)........................................................................... 111
151→1.20 To use the NFM-P clipboard............................................................................................................ 112
152→1.21 To monitor the NFM-P Task Manager.............................................................................................. 114
153→1.22 To save listed information to a file ................................................................................................... 115
154→Procedures for configuring user preferences .........................................................................................116
155→1.23 To configure NFM-P user preferences............................................................................................. 116
156→1.24 To set local tab preferences for configuration forms........................................................................ 118
157→
158→
159→© 2024 
160→ 
161→           
162→ 2024 1
163→3
164→--- Page 4 ---
165→  2024
166→
167→
168→Contents
169→
170→
171→ To temporarily display hidden tabs on property forms..................................................................... 119
172→1.26 To export local tab preferences ....................................................................................................... 120
173→1.27 To import local tab preferences ....................................................................................................... 121
174→1.28 To configure the current client time zone ........................................................................................ 122
175→1.29 To manage the display of listed information .................................................................................... 122
176→Procedures for searching ..........................................................................................................................127
177→1.30 To perform a simple search from an object list form ....................................................................... 127
178→1.31 To perform an advanced search from an object list form ................................................................ 128
179→1.32 To perform a search by specifying endpoints.................................................................................. 131
180→1.33 To save search filters ...................................................................................................................... 132
181→1.34 To use a saved search filter ............................................................................................................ 133
182→1.35 To delete a saved search filter ........................................................................................................ 134
183→1.36 To copy an advanced search filter................................................................................................... 134
184→1.37 To locate an attribute on a configuration form ................................................................................. 135
185→1.38 To filter object types ........................................................................................................................ 136
186→1.39 To filter using span of control .......................................................................................................... 136
187→1.40 To configure and save equipment group filters ............................................................................... 138
188→1.41 To use a saved equipment group filter ............................................................................................ 139
189→
190→2 NFM-P custom workspaces ......................................................................................................................141
191→NFM-P custom workspaces overview ......................................................................................................141
192→2.1 Workspace customization ............................................................................................................... 141
193→2.2 Workflow to administer NFM-P custom workspaces ....................................................................... 142
194→2.3 Workflow to customize NFM-P workspaces .................................................................................... 142
195→2.4 Workflow to share workspaces........................................................................................................ 143
196→NFM-P GUI custom workspace procedures ............................................................................................145
197→2.5 Overview ......................................................................................................................................... 145
198→2.6 To create a new custom workspace ................................................................................................ 145
199→2.7 To modify an existing workspace .................................................................................................... 146
200→2.8 To customize window layouts.......................................................................................................... 147
201→2.9 To configure tab preferences........................................................................................................... 147
202→2.10 To customize menus ....................................................................................................................... 148
203→2.11 To customize toolbars ..................................................................................................................... 150
204→2.12 To customize tree labels.................................................................................................................. 152
205→2.13 To customize list forms.................................................................................................................... 153
206→2.14 To configure the workspace selector............................................................................................... 155
207→2.15 To apply a different workspace using the workspace selector ........................................................ 156
208→
209→
210→     
211→© 2024 
212→   
213→4
214→ 1
215→--- Page 5 ---
216→Contents
217→
218→
219→   delete a custom workspace........................................................................................................ 157
220→2.17 To export custom workspaces......................................................................................................... 157
221→2.18 To import a workspace .................................................................................................................... 158
222→2.19 To add new menu items to a custom workspace of an earlier NFM-P release ............................... 159
223→
224→3 NFM-P navigation tree ...............................................................................................................................161
225→NFM-P navigation tree...............................................................................................................................161
226→3.1 Overview ......................................................................................................................................... 161
227→3.2 Icons and labels .............................................................................................................................. 162
228→3.3 Equipment groups ........................................................................................................................... 163
229→3.4 Navigation tree toolbar .................................................................................................................... 163
230→3.5 Contextual menus ........................................................................................................................... 164
231→3.6 Basic navigation tree procedures.................................................................................................... 164
232→3.7 To locate objects in the navigation tree ........................................................................................... 165
233→3.8 To change the root object of a navigation tree ................................................................................ 166
234→3.9 To manage NEs in equipment groups on the navigation tree ......................................................... 167
235→
236→4 Topology map management ......................................................................................................................169
237→4.1 Topology map types ........................................................................................................................ 169
238→4.2 Working with topology maps ........................................................................................................... 176
239→4.3 To open a map from the NFM-P main menu ................................................................................... 178
240→4.4 To open a service topology map ..................................................................................................... 178
241→4.5 To open an MPLS provisioned path map from the MPLS Path form............................................... 179
242→4.6 To open a dynamic LSP path map from the LSP Path form............................................................ 179
243→4.7 To open a dynamic LSP cross-connect topology map .................................................................... 180
244→4.8 To use OAM diagnostic functions on service topology and composite service flat topology181 maps.
245→4.9 To modify a service from the topology view .................................................................................... 182
246→4.10 To create a physical link .................................................................................................................. 183
247→4.11 To create a radio link ....................................................................................................................... 187
248→
249→5 NFM-P-based schedules ............................................................................................................................189
250→Schedules overview...................................................................................................................................189
251→5.1 Overview ......................................................................................................................................... 189
252→5.2 Time zones and time stamps .......................................................................................................... 189
253→5.3 NFM-P-based schedules................................................................................................................. 190
254→5.4 Workflow to create and manage NFM-P-based schedules............................................................. 191
255→NFM-P-based schedule procedures.........................................................................................................193
256→5.5 Overview ......................................................................................................................................... 193
257→5.6 To configure an NFM-P-based schedule......................................................................................... 193
258→
259→
260→© 2024 
261→ 
262→           
263→ 2024 1
264→5
265→--- Page 6 ---
266→  2024
267→
268→
269→Contents
270→
271→
272→   associate a task with an NFM-P-based schedule ...................................................................... 194
273→5.8 To view scheduled tasks associated with an NFM-P-based schedule ............................................ 195
274→5.9 To assign a different user account to an NFM-P-based scheduled task ......................................... 195
275→5.10 To turn up or shut down an NFM-P-based scheduled task ............................................................. 196
276→5.11 To immediately execute an NFM-P-based scheduled task ............................................................. 197
277→5.12 To view the current status of an NFM-P-based scheduled task ...................................................... 197
278→5.13 To modify a scheduled task on an NFM-P schedule ....................................................................... 198
279→
280→Part II: Device management .............................................................................................................................199
281→
282→6 Device support...........................................................................................................................................201
283→6.1 Device support overview ................................................................................................................. 201
284→6.2 Sample workflow to configure and manage devices ....................................................................... 202
285→6.3 1830 VWM ...................................................................................................................................... 207
286→6.4 210 WBX ......................................................................................................................................... 215
287→6.5 7210 SAS ........................................................................................................................................ 216
288→6.6 7250 IXR ......................................................................................................................................... 220
289→6.7 7450 ESS ........................................................................................................................................ 221
290→6.8 7705 SAR........................................................................................................................................ 221
291→6.9 7750 SR .......................................................................................................................................... 226
292→6.10 7850 VSG/VSA ............................................................................................................................... 227
293→6.11 7950 XRS........................................................................................................................................ 227
294→6.12 Generic NEs.................................................................................................................................... 229
295→6.13 OmniSwitch ..................................................................................................................................... 230
296→6.14 Wavence SM and Wavence SA ...................................................................................................... 231
297→
298→7 Device management using drivers ...........................................................................................................233
299→7.1 Overview ......................................................................................................................................... 233
300→7.2 Driver framework capabilities .......................................................................................................... 233
301→7.3 Driver availability ............................................................................................................................. 234
302→7.4 Driver installation and upgrade ....................................................................................................... 235
303→7.5 View installed drivers on the NFM-P ............................................................................................... 235
304→7.6 View the automatically created Generic NE profile ......................................................................... 236
305→7.7 View the automatically created alarm catalog................................................................................. 236
306→
307→8 Device commissioning and management ................................................................................................239
308→Device commissioning ..............................................................................................................................239
309→8.1 Overview ......................................................................................................................................... 239
310→8.2 Device-specific commissioning information .................................................................................... 241
311→
312→
313→     
314→© 2024 
315→   
316→6
317→ 1
318→--- Page 7 ---
319→Contents
320→
321→
322→ Workflow commission Nokia devices .......................................................................................... 244
323→GNE commissioning ..................................................................................................................................246
324→8.4 Overview ......................................................................................................................................... 246
325→8.5 Configuring user-defined alarms for GNEs ..................................................................................... 247
326→8.6 Workflow to commission GNEs....................................................................................................... 250
327→Procedures for device commissioning ....................................................................................................251
328→8.7 To commission a device for NFM-P management........................................................................... 251
329→8.8 To commission an OmniSwitch for NFM-P management................................................................ 254
330→8.9 To configure the NFM-P SNMP trap listener ................................................................................... 258
331→8.10 To configure polling for a 7250 IXR, 7450 ESS, 7705 SAR, 7750 SR, 7950 XRS, VSR, or Wavence
332→SM...................................................................................................................................................260
333→8.11 To configure polling for a 7210 SAS................................................................................................ 262
334→8.12 To configure polling for a 7705 SAR-Hm......................................................................................... 264
335→8.13 To edit polling settings for multiple devices ..................................................................................... 265
336→Procedures for GNE commissioning .......................................................................................................266
337→8.14 To prepare a GNE for NFM-P management.................................................................................... 266
338→8.15 To configure an alternate EMS for a specific GNE.......................................................................... 268
339→8.16 To modify a GNE profile .................................................................................................................. 268
340→8.17 To create a GNE alarm catalog ....................................................................................................... 269
341→8.18 To create a transform function for a GNE alarm catalog ................................................................. 273
342→8.19 To add an alarm mapping to a GNE alarm catalog ......................................................................... 274
343→8.20 To delete a GNE alarm catalog ....................................................................................................... 274
344→
345→9 Device discovery ........................................................................................................................................277
346→Discovering devices using the NFM-P .....................................................................................................277
347→9.1 Overview ......................................................................................................................................... 277
348→9.2 Device SNMP management............................................................................................................ 278
349→9.3 Device management states............................................................................................................. 279
350→9.4 Using multiple management interfaces ........................................................................................... 282
351→9.5 Post-discovery actions on discovered NEs ..................................................................................... 282
352→9.6 Configuring SSH security on devices.............................................................................................. 283
353→9.7 Mediation and event notification policies......................................................................................... 284
354→9.8 NE resynchronization ...................................................................................................................... 286
355→9.9 Server resource management......................................................................................................... 287
356→9.10 Workflow for device discovery......................................................................................................... 288
357→
358→
359→© 2024 
360→ 
361→           
362→ 2024 1
363→7
364→--- Page 8 ---
365→Contents
366→
367→
368→Procedures
369→9.11 To
370→9.12 To
371→9.13 To
372→9.14 To
373→9.15 To
374→9.16 To
375→9.17 To
376→9.18 To
377→9.19 To
378→9.20 To
379→9.21 To
380→9.22 To
381→9.23 To
382→9.24 To
383→9.25 To
384→9.26 To
385→9.27 To
386→9.28 To
387→9.29 To
388→9.30 To
389→9.31 To
390→9.32 To
391→9.33 To
392→9.34 To
393→9.35 To
394→9.36 To
395→9.37 To
396→
397→10 Device CLI
398→Managing
399→10.1 Overview
400→10.2 Workflow
401→10.3 To
402→10.4 To
403→
404→
405→8
406→
407→
408→ for device discovery ..............................................................................................................291
409→ enable SNMPv3 management of a device ................................................................................. 291
410→ enable SNMPv3 management and discover an 1830 VWM device........................................... 294
411→ configure the AIM mediation and discovery for management of the VSR-I................................ 298
412→ enable or disable SNMP streaming on an NE............................................................................ 299
413→ verify that SSH2 is enabled on a device..................................................................................... 300
414→ enable SSH host key persistence on a device ........................................................................... 301
415→ configure device mediation......................................................................................................... 301
416→ assign an event notification policy to an NE............................................................................... 305
417→ configure a management network .............................................................................................. 306
418→ configure an additional management interface on a main server............................................... 307
419→ configure an additional management interface on an auxiliary server ....................................... 308
420→ configure a post-discovery action............................................................................................... 309
421→ configure a discovery rule .......................................................................................................... 310
422→ enable, disable, or delete a discovery rule ................................................................................. 313
423→ view the post-discovery action execution status ........................................................................ 314
424→ manage a post-discovery action failure on an NE...................................................................... 315
425→ manage, suspend, or unmanage a device ................................................................................. 316
426→ associate a device with a discovery rule .................................................................................... 317
427→ change from SNMPv2 to SNMPv3 management of a device..................................................... 318
428→ switch from non-secure to secure mediation.............................................................................. 319
429→ specify which management address the NFM-P uses to remanage a device............................ 321
430→ rescan the network for a device according to a discovery rule................................................... 322
431→ partially or fully resynchronize NEs with the NFM-P database................................................... 322
432→ manually accept a mismatched SSH host key ........................................................................... 323
433→ view the SSH2 host keys to identify active and mismatched keys ............................................. 324
434→ list and save SNMP MIB information.......................................................................................... 324
435→ delete a device from the managed network ............................................................................... 325
436→
437→ sessions ..................................................................................................................................327
438→ device CLI sessions using the NFM-P ....................................................................................327
439→ ......................................................................................................................................... 327
440→ to use an NFM-P CLI....................................................................................................... 328
441→ configure the NFM-P CLI console preferences .......................................................................... 328
442→ open and close an NFM-P device CLI session........................................................................... 329
443→
444→
445→© 2024 
446→ 
447→           
448→ 2024 1

### Turn 25 (Assistant)
[tool_request: read_file]
- target_file: C:\Users\elzoy\.grok\docs\user-guide\01-getting-started.md
- limit: 80
[tool_request: read_file]
- target_file: C:\Users\elzoy\.grok\docs\user-guide\04-slash-commands.md
- limit: 80
[tool_request: read_file]
- target_file: C:\Users\elzoy\.grok\docs\user-guide\25-status-line.md
- limit: 80
[tool_request: read_file]
- target_file: C:\Users\elzoy\.grok\docs\user-guide\03-keyboard-shortcuts.md
- limit: 60
[tool_request: read_file]
- target_file: C:\Users\elzoy\Downloads\User_Guide_Issue_1.pdf
- format: text
- pages: 73-90

### Turn 26 (Function)
[tool_response]
1→# Getting Started

Grok Build is a terminal-based AI coding assistant from SpaceXAI. It runs as a TUI (Terminal User Interface) that understands your codebase, executes shell commands, edits files, searches the web, and manages tasks.

You can use it interactively as a full-screen TUI, run it headlessly for scripting and CI/CD, or integrate it into editors via the Agent Client Protocol (ACP).

---

## Installation
10→
Install the latest stable release (macOS, Linux, or Windows via Git Bash):

```bash
curl -fsSL https://x.ai/cli/install.sh | bash
```

Install a specific version:

```bash
20→curl -fsSL https://x.ai/cli/install.sh | bash -s 0.1.42
```

On **Windows (PowerShell)**, use the native PowerShell installer:

```powershell
irm https://x.ai/cli/install.ps1 | iex
```

Install a specific version:
30→
```powershell
$env:GROK_VERSION="0.1.42"; irm https://x.ai/cli/install.ps1 | iex
```

The PowerShell installer automatically adds `%USERPROFILE%\.grok\bin` to your User PATH. Alternatively, install via [Git for Windows](https://gitforwindows.org/) (Git Bash) or MSYS2 using the bash script above. WSL users get the Linux binary automatically.

Verify the installation:

```bash
40→grok --version
```

Update to the latest version at any time:

```bash
grok update
```

To fetch a repository through Grove (NFS on macOS, FUSE on Linux) after
50→`[clone] enabled = true` in Grove config:

```bash
grok clone <url> [dir]
```

The default is a depth-1 checkout of the selected branch. Pass `--full-history`
for a complete clone. See [grok clone](27-grok-clone.md).

---
60→
## First Launch

Start Grok by running:

```bash
grok
```

On first launch, Grok opens your browser to authenticate with grok.com. After you sign in, Grok stores your credentials in `~/.grok/auth.json`, where they persist across sessions. Grok refreshes your credentials automatically and prompts you to sign in again when they can no longer be renewed.
70→
If you prefer API key authentication (e.g., for CI/CD or environments without a browser), set the `XAI_API_KEY` environment variable instead:

```bash
export XAI_API_KEY="xai-..."
grok
```

See [Authentication](02-authentication.md) for the full set of auth options including OIDC, external auth providers, and device code flow.

80→---

### Turn 27 (Function)
[tool_response]
1→# Slash Commands

Type `/` in the prompt to open the command menu. It fuzzy-matches as you type, and picking a command runs it immediately.

Commands come from two places: **shell builtins**, handled by the agent backend (xai-grok-shell), and **pager builtins**, handled by the pager frontend (xai-grok-pager). Both show up in the same menu, and any enabled skill with `user-invocable: true` appears there too. If a skill reuses a built-in name such as `login`, the built-in keeps `/login` and the skill stays available as `/plugin-name:login` — the menu badges both so the collision is visible.

Every command below lists its aliases where it has them. A few commands only appear when a feature or session state enables them; those cases are called out inline. The menu is also filtered by render mode — see [`/minimal` and `/fullscreen`](#minimal-and-fullscreen).

---
10→
## Session Management

### `/new`

Start a fresh session and clear the current conversation. Alias: `/clear`.

### `/resume`

Open the session picker to reload a previous session from disk.
20→
### `/dashboard`

Open the [Agent Dashboard](23-dashboard.md): live roster of top-level sessions in this pager (peek, reply, dispatch, pin, rename, stop, attach). Aliases: `/agents-dashboard`, `/sessions`.

Not `/config-agents` (alias `/agents`), which manages agent *definitions* and personas. Hidden in minimal mode; disable with `GROK_AGENT_DASHBOARD=0` or `[dashboard].enabled = false`.

### `/compact [context]`

Compress conversation history to reclaim context-window space. Pass a note to tell Grok what to keep:
30→
```
/compact
/compact keep the auth implementation details
```

Grok also auto-compacts once the context window hits 85% (tune it with `[session] auto_compact_threshold_percent`).

### `/context`

40→Show how the context window is being used: a category breakdown (system prompt, messages, reasoning and overhead, free space) plus informational rows for tool definitions, the skills listing, and MCP server announcements with their estimated token cost.

### `/session-info`

Show session details — auth method, model, turn count, and context usage. Aliases: `/status`, `/info`. Click a value or drag to select and copy; `c` copies the session ID and `y` copies the whole block.

### `/fork`

Branch the current session into a new agent, keeping history up to this point.

50→### `/rewind` (alias: `/undo`)

Roll the conversation back to an earlier turn and discard everything after it. `/undo` is the same command.

### `/copy`

Copy the most recent response's source markdown to the clipboard. Pass a number to copy the Nth-latest response instead, or a file path to write the text to a file rather than the clipboard (handy over SSH, where the local clipboard is often unreachable).

```
/copy
60→/copy 2
/copy out.txt
/copy 2 ~/exports/last-reply.md
```

Every copy is also written to a backup file — `~/.grok/last-copy.txt` by default, or `GROK_COPY_FILE` if set. Confirmed copies toast briefly (e.g. `Copied!`). Unverified OSC 52 deliveries and clipboard-unreachable fallbacks name the backup path so you can recover the text.

### `/export`

Export the conversation to a file or the clipboard.
70→
### `/quit`

Quit the application. Alias: `/exit`.

### `/home`

Leave the current session and return to the welcome screen. Alias: `/welcome`.

### `/delete`
80→

### Turn 28 (Function)
[tool_response]
1→# Keyboard Shortcuts

Reference for key bindings in the Grok Build TUI. Bindings are built in and cannot currently be remapped.

---

## Input Modes

Grok has two input modes that control how you navigate the scrollback:
10→
- **Simple mode** (default): Arrow keys for navigation, `Shift+Arrow` for turn navigation, `Space` to focus the prompt, and any letter key auto-focuses the prompt.
- **Vim mode** (opt-in): `j`/`k` for navigation, `H`/`L` for turn navigation, `J`/`K` for response navigation, `h`/`l` for fold, `e`/`E` for expand/collapse, and `i`/`Tab`/`Space` to focus the prompt.

Simple mode is active by default. To switch to Vim mode, set `vim_mode = true` under `[ui]` in `~/.grok/config.toml`, or toggle it at runtime with `/vim-mode`. See [Configuration](05-configuration.md) for details.

The tables below document bindings for both modes. The "Key" column shows the Vim-mode binding, and the "Alt Key" column shows the equivalent in simple mode (arrow keys, etc.).

> **Vim-mode required**: Single-letter and `Shift+letter` bindings in the
> **Scrollback** context (`j/k`, `h/l`, `g/G`, `L/H`, `y/Y`, `o/O`, `r`,
20→> `x`, `e/E`, and the `i` insert-mode alt) require `[ui].vim_mode = true`
> in `~/.grok/config.toml` (or `/vim-mode` to toggle). Arrow keys, `Tab`,
> `Esc`, `Space`, `PageUp/Down`, and every `Ctrl+letter` shortcut work in
> both modes.

---

## Navigation (Scrollback Focused)

Move through conversation entries in the scrollback pane.
30→
| Key | Alt Key | Action |
|-----|---------|--------|
| `j` | `Down` | Select next entry |
| `k` | `Up` | Select previous entry |
| `⇧L` | `Shift+Right` | Jump to next turn (user prompt) |
| `⇧H` | `Shift+Left` | Jump to previous turn (user prompt) |
| `⇧J` | | Jump to next assistant response |
| `⇧K` | | Jump to previous assistant response |
| `g` | | Go to top of scrollback |
40→| `⇧G` | | Go to bottom of scrollback |
| `Ctrl+K` | | Scroll up one line (without changing selection) |
| `Ctrl+J` | | Scroll down one line (without changing selection) |
| `PageUp` | | Scroll up one page (selection moves to the top of the viewport) |
| `PageDown` | | Scroll down one page (selection moves to the bottom of the viewport) |
| `Ctrl+U` | | Scroll up half page |
| `Ctrl+D` (`Shift+D` in VSCode) | | Scroll down half page |

`PageUp` and `PageDown` also scroll the conversation while the ordinary prompt
is focused, without moving focus or changing the draft. An active prompt
50→history, `@` file search, slash menu, or completion dropdown keeps the keys for
its own navigation.

---

## View (Scrollback Focused)

Control how entries are displayed in the scrollback.

| Key | Alt Key | Action |
60→|-----|---------|--------|

### Turn 29 (Function)
[tool_response]
1→# Status Line

An optional row at the bottom of the pager — above the shortcuts bar in the full screen, under the prompt's info row in minimal mode — and disabled by default. It shows live session context, such as the model, context-window usage, cost, directory, and git worktree, or the output of any script you configure. Opt in with `[ui.status_line]` in `~/.grok/config.toml`.

## Set up

### Built-in

```toml
10→[ui.status_line]
type = "builtin"
items = ["cwd", "model", "context"]   # default when omitted
```

This renders, for example, `grok-shell-status-line │ Grok 4.5 │ 12% ctx`. Items appear in the order you list them, and long ones are elided with `…`: the directory and session name at 40 columns, the model at 30.

| Item | Shows |
| --- | --- |
| `cwd` | Current directory (basename) |
20→| `model` | Model display name |
| `context` | Context-window percent, amber at the auto-compaction threshold or at 80% when the agent reports none |
| `cost` | Session cost, hidden below $0.005 so it never shows a misleading `$0.00` |
| `turn-timer` | Elapsed time of the running turn, from one second in |
| `session-name` | Session name, when set |

### Command

Point `command` at a script. Grok pipes [JSON](#available-data) to it on stdin and shows its stdout. A `~/` prefix expands to your home directory.

30→```toml
[ui.status_line]
type = "command"
command = "~/.grok/statusline.sh"
```

Field names and nesting follow the common status line convention, so a ported script usually needs a small edit rather than a rewrite. Anything the table below does not list is not sent.

### Disabled

40→`type = "disabled"`, the default, shows nothing; `off`, `none`, and `hidden` are accepted as spellings of `disabled`.

### Options

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `type` | string | `disabled` | `builtin`, `command`, or `disabled`. |
| `items` | array | `["cwd", "model", "context"]` | Built-in segments, in order. |
| `command` | string | none | Script for `type = "command"`. |
| `padding` | integer | `0` | Horizontal spacing, in characters per side, capped at 16. A padding wide enough to leave no columns reserves the row but paints nothing in it. |
50→| `refresh_interval` | integer | unset | `command` rows only, in seconds, 1 to 86,400. Re-runs the script this often even when nothing changed, so an idle session can still surface a change — an incident page, a CI status. Unset keeps the row event-driven. The run it schedules carries `"trigger": "refresh_interval"`, and its failures keep the last output rather than painting an error (see [Refresh runs](#refresh-runs)). A script that calls a network should prefer a longer interval and read a cache on `state` runs. |

## How it works

- **Refresh.** The row updates when the session state changes (session start, turn end, a model or effort switch, a HEAD move, a compaction, a client attaching) and continuously while a turn runs, not on a timer. An idle session does not re-run your script, so a clock in it will not tick on its own — unless you set `refresh_interval`, which adds a timer on top of all of the above. These updates are debounced at a fixed 300 ms, so a busy turn cannot run your script every frame; a change that must show at once (a resize, a new snapshot, switching agents) waits only 100 ms. A run already going is never cancelled: the next change waits for it to finish. Grok reads `[ui.status_line]` at startup, so changes to it take effect at the next launch.
- **Output.** Each line you print becomes one line of the row, up to five, and each is cut at 1024 characters, counting the ANSI escapes themselves, so a heavily coloured row has less room for text. A short terminal takes fewer, dropping the surplus from the bottom. ANSI colors are honored; every other escape (cursor motion, line erase, carriage-return overwrite) is dropped. OSC 8 hyperlinks are honored for `http`, `https` and `mailto` targets, and any other target renders as plain text. Stdout past 64 KiB is truncated and the script is stopped. A script that succeeds and prints nothing takes the row away rather than falling back to the built-in segments, so a script that prints only sometimes moves the transcript by a line as it comes and goes.
- **Sizing.** Grok sets `COLUMNS` and `LINES` to the row your output fills, not to the window: the pane's padding and your `padding` are already deducted. `tput` reports these too, since it reads them when stdout is not a terminal. `LINES` is what the row currently fills rather than what it may grow to, so it reads `1` until you print more; the ceiling is five whatever it says. Before the row has painted once, and on a frame with no room for it, the size is the last one the row painted at, or 80x1 if it never has.
- **Shell.** `command` is a shell command line, so `jq -r '…'` and pipes work as written; a path is run directly when it names an executable, and through `sh -c` otherwise, which is what runs a script whose `#!` line is missing or wrong. Quote a path containing spaces as you would at a prompt. Each run is a fresh process, so an edit to the script file applies on the next run.
- **Background work does not survive.** Whatever a script leaves running is killed when the run ends, on every path: a clean exit, a timeout, or too much output. The run ends when your script exits, so anything a background job prints after that is lost.
- **Environment.** Scripts run in the session's working directory, then the repository root, then the pager's own, whichever is a local path first, with a 10 second timeout, after which the row shows `[status line: timed out]`. `COLUMNS` and `LINES` describe the row the script fills, not the window. No shell rc files run (`BASH_ENV` and `ENV` are cleared), and `GIT_OPTIONAL_LOCKS=0`. Pagers and editors are neutralized the same way the rest of Grok neutralizes them, so a `git` or `gh` call inside your script will not block waiting for one.
60→- **Input.** The JSON payload is written to stdin with a trailing newline, so `read -r line` and `input=$(cat)` both work.

## Refresh runs

Set `refresh_interval` on a `command` row and the script also re-runs on a timer, so an incident page or a CI status can reach the row while the session sits idle:

```toml
[ui.status_line]
type = "command"
command = "~/.grok/statusline.sh"
70→refresh_interval = 300   # seconds
```

- **The payload says why the script ran.** A run that answers the timer carries `"trigger": "refresh_interval"` — a state change landing while a timer fire is owed rides that run — and a run with no fire owed carries `"trigger": "state"`. Hit the network on `refresh_interval` and read a cache on `state`, or a busy turn — which re-runs the script continuously — becomes a request storm against whatever the script calls.
- **The payload is the last one Grok sent.** A timer run re-runs your script with the payload from the last state change, so its session numbers — cost, context, tokens — are as of that change, not of the fire. Only what your script fetches itself is fresh.
- **Refresh failures keep the last output.** Once your script has answered — printed a row, or deliberately nothing — a timer run that fails or times out leaves the row exactly as it was, whether that is the last output or a failure a state run had already painted, and writes the failure to `~/.grok/logs/unified.jsonl`, so a flaky endpoint does not paint an error over a quiet night. Three consecutive refresh failures mean the script itself is broken, and the error shows after all; a refresh failure before the script has answered anything — a fresh session, or right after switching agents — also paints at once, since there is nothing to keep. A run triggered by session state still reports its failure at once, as ever.
- **Missed fires coalesce.** While the row is hidden (a fullscreen subagent view, the welcome screen) or a run already holds the slot, the fire waits and the row is owed one run when it can have it — never a burst for the fires a suspend or a long turn skipped. The timer keeps its cadence whatever your script's runtime: a fire that comes due while a run is still going is carried to the next run rather than stacked behind it.
- **The timer belongs to the mode that runs a script.** `refresh_interval` under `builtin` schedules nothing and is reported through `grok inspect`; under `disabled` it is off with everything else.

## Available data
80→

### Turn 30 (Function)
[tool_response]
1→--- Page 73 ---
2→Purpose
3→
4→
5→About this document
6→
7→
8→About this document
9→
10→The NSP NFM-P Classic Management User Guide provides information about using the NFM-P to
11→manage service-aware IP/MPLS networks, including GUI operations, device and network
12→
13→
14→Scope
15→
16→management, and policy and service management.
17→
18→
19→The scope of this document is limited to the NFM-P, which can accomplish many configuration,
20→monitoring, and assurance functions.
21→
22→Document organization
23→
24→This guide contains the following volumes:
25→• Getting started—contains general NFM-P information including the following:
26→− a system overview
27→− basic GUI operation instructions
28→− workspace customization and GUI/topology map management
29→• Device management—contains information about device functions that are not directly related to
30→networking, including the following:
31→− device support
32→− device commissioning and management, and device discovery
33→− working with network objects and device object configuration on logical groups, shelf and
34→cards objects, and port and channel objects
35→− NFM-P device and equipment management functions such as inventory management, TCA,
36→and bulk operations
37→• NE maintenance—contains information about the functions that facilitate the maintenance of
38→managed NEs, including the following:
39→− when to deploy NE configuration changes and how to configure them
40→− backing up device configurations on demand, or using a schedule, and restoring device
41→configurations
42→− upgrade device software on demand, or using a schedule, and how perform device
43→configuration rollback
44→− monitor and troubleshoot operations in progress and how to browse NE file systems
45→• Network management—contains information about network functions including the following:
46→− general routing and forwarding object configuration
47→− protocol-specific configuration
48→− traffic management using MPLS, MPLS TP, and service tunnels
49→− NE redundancy
50→• Policy define rules management—contains that govern how network information traffic about is handled configuring and and prioritized applying NFM-P policies that
51→
52→• Service management—contains information about configuring and managing customer services.
53→
54→
55→© 2024 
56→ 
57→           
58→ 2024 1
59→73
60→--- Page 74 ---
61→  2024
62→
63→
64→About this document
65→
66→
67→• Serviceand SLA assurance—contains verification including information the following: about the proactive detection of service degradation
68→
69→− service verification using the STM and specific OAM diagnostic tests
70→− networkingperformance troubleshooting monitoring
71→ activities including fault detection/verificatio/isolation and
72→
73→− root-cause analysis audits of services and physical links
74→− service throughput configuration
75→
76→Safety information
77→Forwhere your risks safety, of damage this document to personnel, contains equipment, safety statements. and operation Safety may statements exist. Failure are given to follow at points the
78→directions in a safety statement may result in serious consequences.
79→
80→Document support
81→
82→Customer documentation and product support URLs:
83→• Documentation Center
84→• Technical support
85→
86→How to comment
87→Please send your feedback to documentation.feedback@nokia.com.
88→
89→
90→     
91→© 2024 
92→   
93→74
94→ 1
95→--- Page 75 ---
96→Getting started
97→
98→
99→Overview
100→
101→Part I: Getting started
102→
103→
104→Purpose
105→Thisand schedules.part provides information about the NFM-P user interface, workspaces, navigation tree, map,
106→
107→
108→Contents
109→
110→Chapter 1, NFM-P GUI
111→77
112→
113→Chapter 2, NFM-P custom workspaces
114→141
115→
116→Chapter 3, NFM-P navigation tree
117→161
118→
119→Chapter 4, Topology map management
120→169
121→
122→Chapter 5, NFM-P-based schedules
123→189
124→
125→
126→   2024
127→     
128→© 2024 
129→   
130→ 1
131→75
132→--- Page 76 ---
133→Getting started
134→
135→                 © 2024 Nokia.
136→Use subject to Terms available at: www.nokia.com/terms
137→                                  3HE-20021-AAAC-TQZZA
138→   
139→ 
140→ 
141→  2024
142→76
143→ 1
144→--- Page 77 ---
145→ GUI
146→
147→
148→1 GUI
149→
150→GUI overview
151→
152→1.1 GUI workspace elements
153→
154→1.1.1 Overview
155→The GUI on an NFM-P client station allows you to use a standard keyboard and point-and-click
156→operations to perform device, network, policy and service management functions. The GUI
157→simplifies operations such as service configuration, OAM, security, statistics, and other functions by
158→allowing point-and-click selection and intuitive data entry, rather than using a CLI. Multiple NFM-P
159→GUI clients can connect to an NFM-P server.
160→
161→The main GUI window displays standard workspace elements such as a menu bar, toolbar, taskbar,
162→and status bar.
163→
164→1.1.2 Navigation tree
165→The navigation tree lists the managed equipment, services, protocols, and other objects that are
166→configured on the network. By expanding the tree, you can navigate to and select network objects
167→for configuration or to view information. You can open up to five navigation tree windows at one
168→time.
169→
170→See Chapter 3, “NFM-P navigation tree” for more information about the navigation tree.
171→
172→1.1.3 Topology map
173→The topology map provides a view of network elements and connections. You can arrange
174→elements on the map and create equipment groups to suit your requirements. You can select map
175→objects and use contextual menus for configuration or to view information. You can open multiple
176→topology map windows at one time.
177→
178→See Chapter 4, “Topology map management” for more information about the topology map.
179→
180→1.1.4 Windows and forms
181→The NFM-P displays forms in response to menu options or other on-screen selections. Forms are
182→typically used to configure parameters and to view information. Forms allow configurations, display
183→lists and searches, and provide other options; see“NFM-P forms” (p. 82)in this chapter.
184→
185→All currently open windows and forms, except external windows, are represented by icons on the
186→NFM-P taskbar. All currently open windows and forms, including external windows, are listed in the
187→Window menu of the NFM-P main menu.
188→
189→The NFM-P GUI provides floating windows and forms that you can move, resize, hide, and bring to
190→the foreground to optimize the workspace. For information about managing the display of windows
191→and forms, see 1.13 “To manage the display of windows and forms” (p. .105) A window or form in
192→the GUI can be moved out of the main workspace and managed as an external window on a
193→second monitor; see 1.15 “To manage a window or form as an external window” (p.. 107)
194→
195→
196→© 2024 
197→ 
198→           
199→ 2024 1
200→77
201→--- Page 78 ---
202→ GUI
203→GUI overviewGUI customization
204→
205→
206→Messages, warnings, dialogs, and other information appear in pop-up windows in the GUI, but are
207→not managed as floating windows.
208→
209→1.1.5 Main menu bar
210→The main menu bar contains menus and submenus that allow you to navigate to the forms required
211→to perform many NFM-P functions. The available menu items vary depending on licensing and the
212→scope of command role of the current user.
213→
214→1.1.6 Toolbar
215→The toolbar contains icons that allow you to quickly access windows and forms. The icons represent
216→menus or menu items in the NFM-P main menu. When a button represents a menu, the button
217→displays the name of the menu. Clicking the button opens a drop-down of the associated menu
218→items. When an icon represents a menu item with no submenu items, clicking the icon opens the
219→associated form or window. You can set user preferences to show or hide the toolbar; 1.23 see “To
220→configure NFM-P user preferences” (p. 116). You can customize the toolbar as part of a custom
221→workspace; see 2.11 “To customize toolbars” (p. 150).
222→
223→1.1.7 NFM-P objects
224→The term “object” in the NFM-P typically refers to an entity on the network, such as an NE, card,
225→port, routing instance, or any other physical or logical object that is displayed in the navigation tree
226→or map. The term “object” can also refer to entities in the NFM-P, such as policies, tests, or other
227→objects that are displayed in lists or on configuration forms.
228→
229→1.1.8 Contextual menus
230→Contextual menus appear when you right-click certain objects or areas in the GUI; for example, in
231→the navigation tree and topology map. Contextual menus allow you to perform actions that are
232→specific to the object or area.
233→
234→1.1.9 Tooltips
235→The NFM-P provides tooltips to identify many icons, buttons, fields and other GUI elements. When
236→you mouse over these elements, information is displayed.
237→
238→1.2 GUI customization
239→
240→1.2.1 Custom workspaces
241→The NFM-P supports custom workspaces that allow you to configure and arrange workspace
242→elements to suit your operational requirements. You can save and select custom workspaces and
243→update saved workspaces after an NFM-P upgrade. You must have the required scope of command
244→permissions to customize workspaces. Permissions for workspaces are set by a system
245→administrator. See Chapter 2, “NFM-P custom workspaces” for more information about custom
246→workspaces.
247→
248→
249→© 2024 
250→ 
251→           
252→ 2024
253→78
254→ 1
255→--- Page 79 ---
256→ GUI
257→GUI overviewGUI customization
258→
259→
260→1.2.2 Span of control
261→The GUI displays objects and allows object configuration based on the span of control of the user
262→and user preferences. By default, the GUI displays the objects that are included in the View Access
263→and Edit Access spans of the current user. To reduce the number of objects displayed, you can
264→configure user preferences to show only the objects in the Edit Access span of control of the user;
265→see 1.23 “To configure NFM-P user preferences” (p. 116). The user preferences setting affects the
266→display of objects in the GUI. You can temporarily override the user preferences setting when you
267→configure filters to search lists; see1.39 “To filter using span of control” (p. 136).
268→
269→For more information about span of control, see the section on creating a span of control in the
270→NSP System Administrator Guide .
271→
272→1.2.3 User preferences
273→The NFM-P allows you to configure workspace elements and functions to suit your operational
274→requirements. You can set many preferences using the User Preferences form accessed from the
275→main menu. User preferences are specific to a particular user; the settings are associated with the
276→user ID and are applied to the system when that user is logged in.1.23 See “To configure NFM-P
277→user preferences” (p. 116) for more information about user preferences.
278→
279→You can set tab preferences to show or hide tabs on forms; 1.24 see “To set local tab preferences
280→for configuration forms” (p. 118). You can also configure custom workspaces; seeChapter 2,
281→“NFM-P custom workspaces” .
282→
283→1.2.4 Tab preferences
284→Some NFM-P property forms contain numerous tabs, which you can display, hide, and arrange in a
285→preferred sequence according to your operational requirements. On some forms, tabs are hidden
286→by default. You can temporarily display hidden tabs, and you can configure and save your tab
287→display preferences; see 1.24 “To set local tab preferences for configuration forms” (p. and118)
288→1.25 “To temporarily display hidden tabs on property forms” (p. .119)
289→
290→You can configure a workspace to use local tab preferences or custom tab preferences. Local tab
291→preferences are configured using the tab selector and are saved for a specific user. When your
292→current workspace uses local tab preferences, saved local tab preferences become the default that
293→is displayed when a form opens. Custom tab preferences are saved as part of the workspace, and
294→are not user-specific. See 2.9 “To configure tab preferences” (p. 147).
295→
296→Local tab preferences can be exported and shared; see1.26 “To export local tab preferences”
297→(p. 120) and 1.27 “To import local tab preferences” (p. 121).
298→
299→Andefine administrator the default can local configure behavior system for hidden preferences tabs. See to enablethe section or disable on system tab preferences preferences and to
300→
301→configuration procedures in the NSP System Administrator Guide .
302→
303→1.2.5 Localized language support
304→Theinternationalization, GUI supports localizeddisplays GUIlanguage text in display. a specified Localized language. language The display, localized also language known settingas
305→
306→appliestechnical to support most GUI for moreobjects, information except system about componentslocalized language and database support. objects. Contact Nokia
307→
308→
309→© 2024 
310→ 
311→           
312→ 2024 1
313→79
314→--- Page 80 ---
315→ GUI
316→GUI overviewAdditional GUI operations
317→
318→
319→Note: The supports localized language settings using predefined strings, and does not
320→translate data different languages.
321→The XML API does not support language localization.
322→
323→1.3 Additional GUI operations
324→
325→1.3.1 Shortcut keys and accessibility
326→
327→The NFM-P supports shortcut keys to enable operation by keyboard alone, without a mouse or
328→pointer. The following keyboard shortcuts are available:
329→• Standard Java-based shortcuts. The NFM-P supports many conventional keyboard shortcuts for
330→accessibility and convenience.
331→• Mnemonics. You can use mnemonics to open menu items and access forms. To open a menu
332→item, simultaneously press Alt- key, where key is the underlined letter of the menu item. For
333→example, when the main menu is displayed, pressing Alt-P opens the Policies menu. The menu
334→item must be displayed for the mnemonic to work.
335→• Keyboard shortcuts for specific NFM-P functions.
336→
337→The following table describes some of the keyboard shortcuts for specific functions in the NFM-P.
338→For multiple keystrokes, a hyphen means that the keys are pressed simultaneously.
339→
340→Keyboard shortcut Description
341→
342→Ctrl-A
343→Selects all GUI client sessions on the Select
344→Sessions form
345→Selects all objects on the topology map
346→
347→Ctrl-C
348→Stops a command, when using the command
349→window
350→
351→Ctrl-F
352→Opens the “Find Attribute in” form when a
353→property form is the active GUI element
354→Opensnavigation or closestree is the the search active GUIpanel element when the
355→
356→
357→Ctrl-O
358→Opens a directory and lists its contents, when
359→a directory is selected in an NE file system
360→
361→Ctrl-T
362→Opens the tab selector dropdown on a
363→property form
364→
365→Ctrl-Shift-A
366→Temporarily displays all hidden tabs on a
367→property form
368→
369→F3 and Shift-F3 When
370→ search results for the navigation tree
371→produce multiple matching objects, the F3 key
372→selectsprevious the matching next object. object. Shift-F3 returns to the
373→
374→
375→© 2024 
376→ 
377→           
378→ 2024
379→80
380→ 1
381→--- Page 81 ---
382→ GUI
383→GUI overviewAdditional GUI operations
384→
385→
386→1.3.2 clipboard
387→Asfunction well asthat the copies standard property clipboard form identifiers.functions for A propertycopying text,form theidentifier NFM-P is providesa unique a internal clipboard address
388→that the NFM-P assigns to a property form.
389→Identifierscontextual aremenu. copied You to can the use clipboard the clipboard using the to open Clipboard forms, icon send or identifiersthe Copy toto otherClipboard users, option and in a
390→
391→configure search filters.
392→For more information about the NFM-P clipboard, see1.20 “To use the NFM-P clipboard” (p. 112).
393→
394→1.3.3 Broadcast messages
395→YouNFM-P. can This send is messages useful for tosending other selectedmaintenance NFM-P and users similar or notifications to all active to users other logged users. into the
396→
397→When you receive a message, you can click Reply to respond to the sender.
398→Messages are uniquely identified with the Client ID number of the sender.
399→Seemessage the procedures to GUI clients on sendingin the NSP a System text message Administrator to other Guide NFM-Pfor more users information. and sending a broadcast
400→
401→
402→1.3.4 Task manager
403→Themonitors task the manager following allows operations: you to monitor the progress of operational tasks. The task manager
404→
405→• all write operations that are performed from the GUI; for example, when you click Apply or OK
406→• all write operations that are performed using the XML API
407→• some read operations; for example, when you click Resync or Collect All
408→See 1.21 “To monitor the NFM-P Task Manager” (p. 114)for more information.
409→An NFM-P administrator can change the task manager settings. See the procedure to change the
410→NFM-P Task Manager settings in the NSP System Administrator Guide .
411→You can also send the tasks displayed in the Task Manager to a file using the findToFile method.
412→See “Inventory retrieval methods” in the NSP NFM-P XML API Developer Guide for more
413→information.
414→
415→
416→© 2024 
417→ 
418→           
419→ 2024 1
420→81
421→--- Page 82 ---
422→ GUI forms
423→Forms overview
424→
425→
426→ forms
427→
428→1.4 Forms overview
429→
430→1.4.1 Types of forms
431→The NFM-P displays forms in response to menu options or other on-screen selections. Forms
432→display lists or allow you to view and configure properties. Some forms display other information.
433→
434→The GUI displays the following form types:
435→• list forms
436→• configuration forms
437→• step forms
438→• property forms
439→• problems encountered forms
440→• other forms such as messages, warnings, or dialog boxes. These forms are also sometimes
441→referred to as windows.
442→
443→See Figure 1-1, “List form” (p. 83)and Figure 1-4, “Service configuration form with built-in tree”
444→(p. 88) for examples of NFM-P forms.
445→
446→Forms can be sized, positioned, and managed using standard OS functions and NFM-P display
447→features; see 1.13 “To manage the display of windows and forms” (p. 105). A form can be displayed
448→anywhere in the GUI. A newly opened form is displayed in the foreground. You can do the following:
449→• organize forms according to your preferences
450→• compare information on multiple open forms
451→• navigate quickly to another open form
452→• save a set of open forms and reopen them later with one operation, to provide quick access to
453→forms that you use often; see1.14 “To save or open a set of forms for quick access” (p.. 106)
454→
455→Forms are identified by a titlebar at the top. The displayed form name is the name specified during
456→object creation. If the object is not named, a default name is used. When a form is minimized to the
457→taskbar, a tool tip on the taskbar icon of the form displays the title bar information. The Window
458→menu on the main menu lists all open forms.
459→
460→Forms typically contain tabs, buttons, fields, and other elements that you can click to perform
461→actions, depending on the form type. When these elements are not available or not applicable, they
462→are dimmed.
463→
464→1.4.2 More Actions button
465→Buttons that perform various functions appear at the bottom of configuration forms and on the right
466→side of list forms. When a form is resized to a smaller size, or when there are too many buttons to fit
467→in the available space, some of the buttons are consolidated into a More Actions button. The
468→consolidated buttons are available as menu items when you click More Actions; Figure see 1-1,
469→“List form” (p. 83)and Figure 1-4, “Service configuration form with built-in tree” (p. .88)
470→
471→
472→© 2024 
473→ 
474→           
475→ 2024
476→82
477→ 1
478→--- Page 83 ---
479→ GUI forms
480→List forms
481→
482→
483→ List forms
484→
485→1.5.1 General information
486→A list form displays a list of objects in response to a menu option, tab, or other on-screen selection.
487→Figure 1-1, “List form” (p. 82)shows the features of a list form.
488→
489→Some list forms populate automatically; for others, you must click Search to see results.
490→
491→Figure 1-1 List form
492→
493→
494→1.5.2 Using list forms
495→Some list forms contain an object type drop-down that allows you to select the type of objects in the
496→list. When an object type drop-down menu contains more than ten items, you can apply a filter to
497→reduce the number of drop-down items; see1.38 “To filter object types” (p. 136). You can
498→customize the object drop-down and select the default object type in a custom workspace; see
499→2.13 “To customize list forms” (p. 153).
500→
501→Objects on a list form are displayed in table format. The column headings correspond to the
502→attributes (parameters) for the object, for example, the Customer ID for a service. The column
503→headings vary depending on the object type. Each object in the list is displayed in a row, showing
504→the values for the attributes of the object. On some forms, the first column on the left displays a
505→deployment icon for an item, when required; see11.1.2 “Object deployment status” (p. 334)in
506→Chapter 11, “Working with network objects” .
507→
508→Objects are displayed based on the span of control of a user and user preferences.
509→See 1.2.2 “Span of control” (p. 79)in this chapter.
510→
511→List forms can contain many objects, in some cases hundreds or thousands. You can reduce the
512→number of items in a list using search filters; “NFM-Psee searches” (p. 92)in this chapter. Most list
513→forms display the time at which the last search was performed on the form.
514→
515→
516→© 2024 
517→ 
518→           
519→ 2024 1
520→83
521→--- Page 84 ---
522→ GUI forms
523→Configuration forms
524→
525→
526→List forms typically display a column of buttons along the right side. On some list forms, not all
527→buttons are displayed, but you can access them using the More Actions button. 1.4.2 See “More
528→Actions button” (p. 82)in this section.
529→
530→Many list forms contain a Customize button that allows you to quickly make changes to the list form
531→default settings in a custom workspace. See2.13 “To customize list forms” (p. 153)for more
532→information.
533→
534→The NFM-P provides features that allow you to manage the display of listed results and to set and
535→save your display configuration. See1.8.4 “Managing search results and lists” (p. 97)in this
536→chapter, and 1.29 “To manage the display of listed information” (p. 122). You can also save the
537→results to a file; see1.22 “To save listed information to a file” (p. 115).
538→
539→You can set the following user preferences for list forms:
540→• number of items per page
541→• object display based on user span of control
542→• default file extension for saving listed information
543→
544→See 1.23 “To configure NFM-P user preferences” (p. 116)for more information about user
545→preferences.
546→
547→1.6 Configuration forms
548→
549→1.6.1 General information
550→Configuration forms allow you to create and modify NFM-P objects and to view information about
551→objects; see 1.17 “To use configuration forms to configure or view parameters” (p. .109)Figure 1-4,
552→“Service configuration form with built-in tree” (p. 88)describes the main features of a configuration
553→form in the NFM-P.
554→
555→When you first create an object in the NFM-P, you use a configuration form to enter values for the
556→parameters that define the object. For example, when you create a service, you use a service
557→configuration form; when you create a policy, you use a policy configuration form. After object
558→creation, the form associated with the object is typically called a property form. 1.6.12 See “Property
559→forms” (p. 89)in this section.
560→
561→You can set user preferences to suppress warnings and messages for configuration forms; see
562→1.23 “To configure NFM-P user preferences” (p. 116).
563→
564→1.6.2 Step forms
565→Some configuration activities lead the operator through a series of forms, each of which represents
566→a step in the configuration process. Such a form is called a step form. You must click Next to
567→proceed to the next step. The following figure shows the first step in a step form sequence. When
568→the configuration sequence is complete, you must click Finish to commit the changes.
569→
570→
571→© 2024 
572→ 
573→           
574→ 2024
575→84
576→ 1
577→--- Page 85 ---
578→ GUI forms
579→Configuration forms
580→
581→
582→Figure 1-2 Step form
583→
584→
585→Some steps open a new step form. You must complete the steps in the new form before you can
586→return to the previous form. After you click Finish on the new form, the previous form reappears.
587→
588→1.6.3 Tabs
589→Configuration forms typically display tabs. You can use the tabs to open related forms for additional
590→configurations or to open lists or view other information, such as deployment or fault status.
591→Property forms allow you to show or hide tabs to suit your requirements, and to set preferences for
592→tab display; see 1.2.4 “Tab preferences” (p. 79).
593→
594→1.6.4 Collapsible panels
595→Configuration forms are often subdivided into specific information areas using panels. Panels are
596→framed by border lines, with a title bar at the top that identifies the panel. Panels can be collapsed
597→to hide areas that are not of interest, or expanded to display all information on a tab or form; see
598→1.17 “To use configuration forms to configure or view parameters” (p.. 109)
599→
600→When a configuration form closes, the current state of the panel is saved for that object type. When
601→a user opens a configuration form, the last saved state of the panel is displayed.
602→
603→1.6.5 Parameters
604→When you create or modify an object, you typically configure parameters, sometimes referred to as
605→attributes. Parameter settings define the properties of an object. Some parameters are read-only,
606→and cannot be configured. Configurable parameters typically display a white field, check box, or
607→drop down arrow. Mandatory fields are yellow. Read-only parameter values display in a grey field.
608→
609→
610→© 2024 
611→ 
612→           
613→ 2024 1
614→85
615→--- Page 86 ---
616→ GUI forms
617→Configuration forms
618→
619→
620→Non-applicable parameters are dimmed. See “To use configuration forms configure or view
621→parameters” (p. 109)for more information about parameters.
622→
623→1.6.6 Saving configurations
624→When you complete a configuration, you can click OK, Apply, or other buttons to save the
625→configured values. When you click the OK button, the information is saved and the form closes.
626→When you click the Apply button, the information is saved and the form remains open to allow you
627→to perform additional actions. See1.17 “To use configuration forms to configure or view parameters”
628→(p. 109) for more information.
629→
630→1.6.7 Warning and confirmation messages
631→When you save configuration changes or close a form, the NFM-P typically displays a warning or
632→confirmation message. You must acknowledge the message. Not all configurations require
633→confirmation.
634→
635→When you save changes for a child object configuration form that was launched from a parent
636→object form, the NFM-P displays a warning that the changes are not committed until the parent
637→object form (called the containing window) is also saved. You must acknowledge the warning. You
638→can set user preferences to suppress containing window warnings; 1.23see “To configure NFM-P
639→user preferences” (p. 116). If you then attempt to close the parent form without saving it first, the
640→NFM-P displays a warning, regardless of the user preferences setting.
641→
642→1.6.8 Indicators and icons
643→Indicators and icons inform you of activity that is in progress or requires attention, and can appear
644→and disappear depending on the activity that is occurring in the NFM-P, as shown in the following
645→figure.
646→
647→
648→© 2024 
649→ 
650→           
651→ 2024
652→86
653→ 1
654→--- Page 87 ---
655→ GUI forms
656→Configuration forms
657→
658→
659→Figure 1-3 Indicators and icons
660→
661→A field on this tab requires information update
662→A deployment is inprogress or failed alarms are raisedOne or more
663→
664→
665→Deploymenticons
666→
667→
668→22870
669→
670→
671→A yellow asterisk icon on a tab or panel title bar indicates that a field contains incorrect data, or that
672→a mandatory field requires data.
673→
674→A warning indicator appears on the Deployment tab when a configuration change is not fully
675→deployed to an NE.
676→Whenan object a deployment properties form,is in progressand beside or affectedhas failed, objects a deployment in the navigation icon appears tree, andbeside in listparameters forms. See on
677→
678→11.1.2 “Object deployment status” (p. 334)in Chapter 11, “Working with network objects” for more
679→information.
680→
681→1.6.9 Action buttons
682→Configuration forms typically have a row of action buttons along the bottom. The available buttons
683→vary depending on the form. The Find icon is available on all configuration forms, and allows you to
684→
685→form”quickly (p. locate 135) . aOn specific some configurationtab, panel, or forms, parameter; not all see1.37
686→ buttons
687→ “To locate
688→ are displayed,
689→ an attribute
690→ but
691→ 
692→ 
693→on
694→you
695→ a
696→ can
697→ configuration
698→ access them
699→using the More Actions button. See1.4.2 “More Actions button” (p. 82)in this section.
700→
701→1.6.10 Configuration forms with built-in navigation trees
702→Servicestree. For andexample, NEs typicallywhen you require create configuration a service, you at several configure levels parameters of the service at the orservice, equipment site, andobject
703→
704→interface levels. NEs require configuration at the device, shelf, card, and port levels; Chapter see
705→11, “Working with network objects” .
706→
707→
708→© 2024 
709→ 
710→           
711→ 2024 1
712→87
713→--- Page 88 ---
714→  GUIforms
715→Configuration forms
716→
717→
718→ service configuration and NE property forms display a navigation tree on the left side of the
719→form, which provides quick access service and NE objects. Other object types also display
720→navigation trees in configuration or property forms. See“NFM-P navigation tree” (p. 161) for
721→information about using navigation trees. Objects in the tree provide access to configuration forms
722→using contextual menus.
723→
724→Service navigation trees for VPLS, I-VPLS, B-VPLS, MVPLS, IES, and VPRNs display a maximum
725→of 50 access interfaces, SAPs, MSAPs, subscriber SAPs, and spoke and mesh SDP bindings at a
726→time.which When the SAPs this limitor access is reached, interfaces you arecan listedclick onto openthe message a tab with beside the fullthe listcontaining of objects. object under
727→
728→
729→Figure 1-4 Service configuration form with built-in tree
730→
731→Click object
732→Active tab
733→to access
734→Orange lock Locked tab highlighted
735→configuration
736→Click object type
737→indicates
738→Click X
739→form
740→to access listing
741→Select object a change
742→to close Drop-down list
743→of objects
744→from list on the tab
745→tab of all open tabs
746→Double arrowindicates thatnumber of opentabs exceedswindow width
747→
748→
749→Click to access More Actions menu to view hidden options
750→21805
751→
752→
753→Whenyou select you anotherfirst open object a configuration in the tree, form a form with for a built-inthe selected navigation object tree, replaces the form the isunlocked unlocked. form When of
754→theform previous for each object. object You is displayed can lock asforms a tab to inkeep the them main open configuration when you form. select additional objects. The
755→
756→You can undock tabs to detach them from the main configuration form. Undocked tabs are
757→displayed as separate forms and are managed like other standard form in the NFM-P. You cannot
758→undock Create forms, tabs for object type lists, or tabs with unsaved changes.
759→
760→
761→© 2024 
762→ 
763→           
764→ 2024
765→88
766→ 1
767→--- Page 89 ---
768→ GUI forms
769→Configuration forms
770→
771→
772→See 1.18 “To manage configuration forms with built-in navigation trees” (p. for110) more
773→information about managing configuration forms with built-in navigation trees.
774→
775→1.6.11 Modifying configuration forms with built-in navigation trees
776→When you modify a docked configuration form, it becomes locked. The lock icon appears in orange
777→until the changes are saved. An orange lock icon indicates unsaved changes on the form. You
778→cannot undock tabs with orange lock icons. When you save the changes, the form remains locked
779→but the icon is no longer orange.
780→
781→If you attempt to close a modified configuration form that contains unsaved changes, a message
782→prompts you to specify whether to discard the changes or return to the display. If you attempt to
783→close a modified configuration form that has related forms with unsaved modifications, the message
784→lists the forms that have unsaved changes.
785→
786→For service configuration forms, if an object is added to the service configuration, the new object
787→appears in the built-in navigation tree and the configuration form is displayed with the orange lock
788→icon. The icon remains orange until the modifications are saved or discarded.
789→
790→For NE property forms, if an object is added from the navigation tree, the change will be made
791→immediately. However, if a change, such as adding or removing an object, is made to an equipment
792→configuration form, the change will be reflected on the form immediately, but it will not be reflected
793→on the navigation tree until the OK, Apply, or Apply Tab button is clicked.
794→
795→Note: Changes implemented by pressing the OK or Apply buttons affect all tabs in the form.
796→For some configuration forms, you can click the Apply Tab button to save changes for the
797→current object-level tab and related objects. A message lists the affected objects.
798→
799→If you save a set of forms for quick access when child forms are displayed as tabs in a parent form,
800→all of the child tabs are saved as separate forms. When you reopen the forms, the child tabs are
801→displayed as separate forms. See1.14 “To save or open a set of forms for quick access” (p.. 106)
802→
803→1.6.12 Property forms
804→Configuration forms for objects that already exist in the NFM-P (NEs for example) are typically
805→called property forms. You can access property forms by using contextual menus, the Properties
806→button on list forms, or by double-clicking on objects in the navigation tree that have no child
807→objects.
808→
809→A property form has a property form identifier that you can copy to the clipboard and paste for
810→various functions; see 1.20 “To use the NFM-P clipboard” (p. 112).
811→
812→Most property forms contain tabs that provide specific information. The Deployment tab allows you
813→to monitor the deployment status of an object; see11.1.2 “Object deployment status” (p. 334)in
814→Chapter 11, “Working with network objects” .
815→
816→1.6.13 NE sessions
817→You can open a CLI window using the Telnet Session or SSH Session button on NE property forms.
818→You can access the NE file system using the File Browser button. These options are also available
819→using the contextual menu for NE objects in the navigation tree.
820→
821→
822→© 2024 
823→ 
824→           
825→ 2024 1
826→89
827→--- Page 90 ---
828→ GUI forms
829→Configuration forms
830→
831→
832→1.6.14 User Activity button
833→The User Activity button opens a form that lists the recent NFM-P user actions performed on the
834→object. See the section on user activity logging in NSP the System Administrator Guide for more
835→information.
836→
837→1.6.15 Resync button
838→The Resync button on a property form resynchronizes the data in the NFM-P with the current state
839→of the corresponding object. The NFM-P requests the configuration from the object and updates the
840→NFM-P network model accordingly. Resynchronization does not affect the contents of the historical
841→statistics database.
842→
843→1.6.16 Turn Up and Shut Down buttons
844→The Turn Up and Shut Down buttons on some property forms provide a convenient method for
845→changing the administrative state of an object. When you click the Turn Up or Shut Down buttons,
846→the change is effected immediately. When you modify the Administrative State parameter, the
847→change is not effected until you click the OK or Apply button for the form.
848→
849→1.6.17 Multi-edit property forms
850→The NFM-P provides a multi-edit function that allows you to select multiple objects at one time for
851→editing of specific properties. The objects must be of the same type (for example, services must all
852→be VPRN, not a mixture of VPRN and other service types).
853→
854→Changes for the selected objects are entered on a Multiple Instances (Edit) property form. When
855→the objects selected for multi-edit are configured with differing parameter values, the NFM-P
856→typically alerts you by displaying multi-value fields or drop-downs for the parameters whose values
857→differ. Multi-value fields and drop-downs are identified by triple borders along the top and right side;
858→see Figure 1-5, “Multi-value property form” (p. 91). Both configurable and read-only parameters
859→may display as multi-value properties.
860→
861→You can modify configurable multi-value fields. When a value is entered in a multi-value field, the
862→value is propagated to all selected objects in the multi-edit group, and the parameter no longer
863→displays as a multi-value property. See1.19 “To modify multiple objects at one time (multi-edit)”
864→(p. 111)for more information.
865→
866→The NFM-P also provides a bulk operations function; seeChapter 20, “Bulk operations” .
867→
868→
869→© 2024 
870→ 
871→           
872→ 2024
873→90
874→ 1

### Turn 31 (Assistant)
[tool_request: read_file]
- target_file: C:\Users\elzoy\Downloads\NSP_System_Administrator_Guide_Issue_11.pdf
- format: text
- pages: 141-160
[tool_request: read_file]
- target_file: C:\Users\elzoy\Downloads\User_Guide_Issue_1.pdf
- format: text
- pages: 161-175
[tool_request: todo_write]
- todos: [{"id":"1","content":"Diseñar modelo de datos NFM-P (NEs, MPLS, servicios, alarmas, usuarios)","status":"in_progress"},{"id":"2","content":"Implementar auth (login, roles, span of control, sesión)","status":"pending"},{"id":"3","content":"Shell Grok-like: prompt, slash commands, status line, navegación","status":"pending"},{"id":"4","content":"Comandos de dominio: equipment, mpls, services, alarms, stats","status":"pending"},{"id":"5","content":"README + requirements + demo lab y verificar el CLI","status":"pending"}]
- merge: false

### Turn 32 (Function)
[tool_response]
- [in_progress] 1: Diseñar modelo de datos NFM-P (NEs, MPLS, servicios, alarmas, usuarios)
- [pending] 2: Implementar auth (login, roles, span of control, sesión)
- [pending] 3: Shell Grok-like: prompt, slash commands, status line, navegación
- [pending] 4: Comandos de dominio: equipment, mpls, services, alarms, stats
- [pending] 5: README + requirements + demo lab y verificar el CLI


### Turn 33 (Function)
[tool_response]
1→--- Page 141 ---
2→NSP user security
3→
4→
5→8 user security
6→
7→Local user management
8→
9→8.1 What is user management?
10→
11→8.1.1 Local user management
12→The NSP uses Keycloak-based OAUTH2 user authentication, which supports locally defined users
13→for NSP access. If the NSP is integrated with NFM-P, you can also import the NFM-P users to the
14→NSP local user database. Remote authentication agents are also supported.
15→
16→Note: The NSP does not support case-sensitive user names; local and remote user names
17→are saved in lowercase. User name entry at sign-in is case-insensitive.
18→NSP Users and Security supports up to 5000 users, except where noted.
19→
20→For all local and remote users, the Users and Security GUI lists information that includes the
21→authentication source, the user creation time, and the most recent login time.
22→
23→Local user accounts can be used for machine-to-machine interaction, rather than creating user
24→accounts in your corporate user database. They also provide a backup mechanism for cases where
25→NSP cannot communicate with the corporate user database.
26→
27→Note: The NSP does not support case-sensitive usernames; local and remote usernames are
28→saved in lowercase. Username entry at sign-in is case-insensitive.
29→
30→8.1.2 Remote user management
31→NSP supports remote LDAP (including Active Directory), RADIUS, and TACACS authentication
32→servers.
33→
34→With remote user management, the NSP first attempts to verify login attempts against the local user
35→database. If the user account is not found locally, NSP searches the remote authentication servers
36→(LDAP first, followed by RADIUS or TACACS). If a user account is found in an authentication
37→source (local or remote) but fails the password check, the authentication attempt stops and does
38→not continue to any other authentication sources.
39→
40→If NSP is configured for remote user authentication with an Active Directory server, the AD users
41→also appear as local accounts in the NSP database. However, AD users are bulk imported to NSP
42→at system startup. The bulk import of AD users into NSP is automatic and cannot be avoided, but
43→customers can manage the scope of the import by defining user and group filters so that only the
44→intended AD users for access to NSP are auto-imported.
45→
46→Note: NSP Users and Security supports a maximum combined total of 1000 local and remote
47→users when Active Directory is configured.
48→
49→
50→© 2026 
51→ 
52→           
53→ 2026 11
54→141
55→--- Page 142 ---
56→NSP user securityLocal user managementWhat are the user management requirements and restrictions?
57→
58→
59→ Whatrestrictions? are the user management requirements and
60→
61→
62→8.2.1 Remote user accounts in NSP
63→Remote users have a local account instance created in the NSP database. The remote user
64→accounts appear in Users and Security, Users list, flagged as remote users. Remote users continue
65→to use their login credentials, as defined on the remote server. System administrators can edit
66→certain fields of a remote user local account instance, including first and last name, description and
67→email address; see 8.8 “How do I modify a user account?” (p. 150). Remote users are subject to the
68→same global user session limits as locally defined NSP users.
69→
70→Active Directory
71→
72→If NSP is configured for remote user authentication with an Active Directory server, the AD users
73→also appear as local accounts in the NSP database. However, AD users are bulk imported to NSP
74→at system startup. The bulk import of AD users into NSP is automatic and cannot be avoided, but
75→customers can manage the scope of the import by defining remote NSP users with a unique
76→distinguished name on the AD server, and limiting the user search scope to that DN only. Refer to
77→the userDn and searchScope parameters in the NSP Installation and Upgrade Guide .
78→
79→LDAP, RADIUS, and TACACS
80→
81→As LDAP, RADIUS, and TACACS users log in to NSP, a local account instance is created in the
82→NSP database. Only the remote users that have logged into NSP appear as local instances of those
83→user accounts in Users and Security.
84→
85→8.2.2 E-mail verification
86→After you enable the Verify Email setting, each local and remote NSP user with a configured e-mail
87→address—not just new users—must complete a verification process. During a subsequent login
88→attempt, the sign-in page directs the operator to open a verification e-mail and click on the enclosed
89→link to complete the process.
90→
91→After the verification, the user account is tagged as ‘email verified’, and no further verification is
92→required, even if the e-mail address changes.
93→
94→Note: In order to acquire an API access token, an OSS user that has an e-mail address must
95→first complete the e-mail verification process by signing in to the NSP UI.
96→
97→8.2.3 Forgotten passwords
98→The NSP sign-in page has a Forgot Password option. If a user clicks this option, they are prompted
99→for their username. A message "You should receive an e-mail shortly ..." appears on the sign-in
100→page. In order to ensure that the Forgot Password option works for local users, configure all local
101→user accounts with e-mail addresses. The Forgot Password feature functions only for local NSP
102→users; remote users cannot reset a password through NSP.
103→
104→
105→© 2026 
106→ 
107→           
108→ 2026
109→142
110→ 11
111→--- Page 143 ---
112→NSP user securityLocal user management I create an local user?
113→
114→
115→8.2.4 User account lockout messaging
116→The NSP provides the ability to automatically send an e-mail message to users whose accounts
117→have been locked. A user receives an e-mail when they are temporarily or permanently locked out
118→through Brute Force Detection protection mechanisms. Local user accounts must be configured
119→with an e-mail address to be sent lockout messages.
120→Theconfigure lockout an e-mail e-mail function server for is enablednotifications?” through (p. the .32) You NSP can system specify settings; the Subject2.7 see “How line do and I body text
121→for the e-mail message.
122→
123→Note: Lockout messages are not sent to users whose accounts have been set to Suspended
124→status by an administrator. That is a separate function.
125→
126→8.3 How do I create an NSP local user?
127→
128→8.3.1 Purpose
129→Thismanaged procedure through describes external how databases. to create a local NSP user account. It does not apply to users
130→
131→
132→Note: NSP Users and Security supports up to 5000 users.
133→
134→8.3.2 Steps
135→
136→1
137→Open Users and Security .
138→
139→2
140→Select Users from the drop-down list on the toolbar.
141→
142→3
143→Click Create User.
144→
145→4
146→InIdentification the Create section. User form, TheUsername specify userand identificationUser Group informationfields are mandatory. for the account in the
147→
148→
149→Note: Any uppercase characters in the username are saved as lowercase.
150→The Username value:
151→• can be 1 to 40 characters long
152→• cannot include a space
153→• cannot have a leading or trailing space
154→• can include only the following special characters:
155→− @ (at sign)
156→− - (hyphen)
157→
158→
159→© 2026 
160→ 
161→           
162→ 2026 11
163→143
164→--- Page 144 ---
165→NSP user securityLocal user management I import users and groups from NFM-P?
166→
167→
168→− _ (underscore)
169→− . (period)
170→
171→5
172→Select a user group for the user from the User Group drop-down list.
173→If no user groups are available, you will need to create one; 8.16 see “How do I configure a user
174→group?” (p. 162) .
175→
176→6
177→
178→In the Password section, specify and confirm a password for the user account.
179→         Note: The NSP does not support case-sensitive usernames; local and remote usernames
180→         are saved in lowercase. Username entry at sign-in is case-insensitive.
181→• If you want this password to be temporary, enableForcethe User to Change Password
182→         option. The new user will be forced to change their password when they first login to
183→• Enable theShow Password option to see the password characters as you type them.
184→• Click on thePassword Requirements link to view a list of minimum security requirements
185→for the password.
186→       
187→   
188→   
189→
190→     
191→ 
192→     
193→   
194→       
195→     
196→   
197→ 
198→ 
199→       
200→   
201→     NSP.
202→     
203→     
204→     
205→   
206→ 
207→     
208→ 
209→   
210→
211→7
212→Click Create.
213→
214→8
215→Insame an nameNSP deployment as the NSP that user includes group; theotherwise, NFM-P, the the NSP NFM-P user requires cannot: a user group with the
216→
217→• Open an NFM-P client.
218→• View NSP GUI alarms that quote NFM-P as the source.
219→• Open some NSP GUI fault-management views.
220→Ifthe your same NSP name deployment as the NSP includes user the group, NFM-P, perform and9.16 the“How NFM-P do I create does not an haveNFM-P a useruser group?”group with
221→
222→(p. 215) .
223→
224→END OF STEPS
225→
226→8.4 How do I import users and groups from NFM-P?
227→
228→8.4.1 Purpose
229→NFM-P users must be imported to the NSP local user database. The Import function migrates all
230→user accounts and user groups from your NFM-P user database into NSP. The imported users
231→become local NSP users. The imported user groups can be assigned roles that provide the users in
232→the groups access to NSP functions and resources.
233→
234→Note: NSP Users and Security supports up to 5000 users.
235→
236→
237→© 2026 
238→ 
239→           
240→ 2026
241→144
242→ 11
243→--- Page 145 ---
244→NSP user securityLocal user management I import users and groups from NFM-P?
245→
246→
247→Imported NFM-P users require new passwords. Users that have an e-mail address receive a
248→random password by e-mail. Users without an e-mail address are assigned a global default
249→password set by the administrator. Each imported user must change the password during the first
250→login attempt after the import. It is recommended that the NFM-P system administrator assign
251→e-mail addresses to users before the import in order to ensure the greatest security.
252→
253→Before importing NFM-P users, consider the following requirements and limitations:
254→• If you intend to use e-mail notification of new user passwords, you must ensure that the NSP
255→e-mail server is configured in the NSP system settings. If the e-mail server is not reachable to
256→NSP and some NFM-P users have e-mail addresses configured, the NFM-P user import will not
257→complete successfully.
258→The user import process depends on how the user list with e-mail addresses is created in the
259→NSP system. If the e-mail sending fails for the first user with an e-mail address, the remaining
260→users with email addresses are not imported.
261→• If NFM-P is configured with remote identity providers, those identity providers must be
262→configured in nsp.sso section of nsp-config.yml.
263→• The NFM-P user parameters imported to NSP are: user name, description, user group, account
264→state, and e-mail address.
265→• All NFM-P user IDs are converted to lowercase upon import. If two NFM-P user IDs are identical
266→except for case, only one of them is imported. You must clean up any duplicate user IDs in
267→NFM-P prior to import to ensure that all users are imported.
268→• NSP user groups are case sensitive, as are NFM-P user groups. When NFM-P user groups are
269→imported to NSP, they keep uppercase and lowercase characters. For example, if NFM-P has
270→user groups GROUP1, Group1 and group1, all three are imported into NSP.
271→• Any NFM-P user names that conflict with existing NSP local users are not imported and do not
272→cause any change to local users.
273→• To ensure that only necessary users are included in the migration, clean up your NFM-P user
274→database before importing to NSP.
275→• NFM-P remote users are not imported into NSP (remote users include NSP, LDAP, RADIUS, and
276→TACACS users that have access to the NFM-P GUI.)
277→• NSP authentication does not support local and remote user authentication for the same user ID.
278→To preserve the use of a remote user ID, the local user ID must be changed to a unique value.
279→
280→8.4.2 Steps
281→
282→1
283→Open Users and Security .
284→
285→2
286→Select Users from the drop-down list on the toolbar.
287→
288→3
289→Click More Actions, Import NFM-P Users and Groups .
290→
291→
292→© 2026 
293→ 
294→           
295→ 2026 11
296→145
297→--- Page 146 ---
298→NSP user securityLocal user management I set global user session limits?
299→
300→
301→4
302→Inpassword the Temporary for all imported Password users. for Imported Users form, specify and confirm a global temporary
303→
304→The global temporary password is only applied to imported users with no e-mail address.
305→
306→5
307→Click OK.
308→TheGroups imported view. users are listed in the Users view. The imported user groups are listed in the User
309→
310→
311→6
312→The NFM-P imported users can now log in to NSP. All imported users will be required to change
313→their password during first login. NFM-P users that have an e-mail address must check their
314→e-mail for their random login password.
315→
316→Note: In the event that the import fails for certain users or user groups, you can
317→investigate /opt/nsp/os/tomcat/logs/AccessControlApi.log
318→ problems in the nspos-tomcat pod logfile at:
319→
320→
321→END OF STEPS
322→
323→8.4.3 Post-import considerations
324→
325→After importing users from NFM-P, be aware of the following requirements and limitations:
326→• Anassigned imported to a NFM-P role with user administrative group that had privileges Administrator in NSP. scope of command in NFM-P must be
327→
328→• NFM-Ptransactions XML with SOAP NFM-P. OSS users must remain in NFM-P after import to perform XML SOAP OSS
329→
330→• Non-NFM-Pimport to NSP. XML SOAP OSS users that are imported to NSP can be deleted from NFM-P after
331→
332→• NFM-Pscope of user control groups profiles. must exist in NFM-P to define user access permissions through span and
333→
334→• New NFM-P XML SOAP OSS users must be created.
335→
336→8.5 How do I set global user session limits?
337→
338→8.5.1 Purpose
339→Yousessions can configureper user, limitsand so for on. NSP These user configurations sessions such are as set maximum globally inactivity and apply time, to allmaximum users. TheyGUI
340→
341→cannot be configured per user.
342→
343→8.5.2 Steps
344→
345→1
346→
347→
348→© 2026 
349→ 
350→           
351→ 2026
352→146
353→ 11
354→--- Page 147 ---
355→NSP user securityLocal user management I set global user session limits?
356→
357→
358→Open Users and Security .
359→
360→2
361→Click More Actions, Settings.
362→
363→3
364→In the Users and Security Settings form, click Session Settings.
365→
366→4
367→Configure user session limits in any of the following ways:
368→
369→   
370→   
371→   
372→   
373→       
374→   
375→   
376→ 
377→ 
378→     
379→ 
380→
381→
382→Maximum Session Time The absolute maximum length of a user session (in
383→minutes) before the user is automatically logged out of
384→NSP.
385→
386→       Maximum Time to Complete The maximum time allowed (in minutes) for an NSP
387→Login Steps login sequence that involves multiple steps; for example,
388→                                  if the user must change their password during login.
389→
390→    The maximum toMaximumTimetoComplete time allowed (in minutes) for a user
391→    complete login.Login an NSP
392→
393→1UISessionInactivityTimeout The number of minutes of user session inactivity before
394→                             the user is automatically logged out of NSP. GUI activity
395→                             in an NSP session includes any mouse movement,
396→                             mouse clicks, or typing in an NSP GUI window.
397→ 
398→ 
399→     
400→ 
401→ 
402→ 
403→       
404→         
405→
406→MaximumUser 2
407→ UI Sessions Per The maximum number of simultaneous GUI sessions
408→per user account.
409→Whensessions this per parameter user is unlimited.is set to zero, the number of
410→
411→
412→MaximumUser
413→ OSS Sessions Per Theper user maximum account. number of simultaneous OSS sessions
414→
415→When this parameter is set to zero, the number of
416→sessions per user is unlimited.
417→
418→OSS Access Token Lifespan The number of minutes before an OSS access token
419→expires.
420→
421→Notes:
422→1. Some NSP UI views are in continuous communication while in use, and a user session does not
423→become idle as long as the user has that view open, such as when viewing an alarm list.
424→2. If a user login attempt exceeds the Maximum UI Sessions Per User limit, the sign-in page
425→displays an error message. If you increase the parameter value to allow more sessions per user,
426→refreshing the sign-in page with the error message opens a session using the previously entered
427→credentials.
428→
429→
430→© 2026 
431→ 
432→           
433→ 2026 11
434→147
435→--- Page 148 ---
436→NSP user security
437→
438→
439→5
440→
441→
442→Local user managementWhat are the user password policies?
443→
444→
445→Click Save.
446→
447→END OF STEPS
448→
449→
450→8.6.1 Introduction
451→
452→8.6 What are the user password policies?
453→
454→
455→When an operator attempts to sign in to the NSP and a password change is required, the new
456→
457→following table.
458→password must conform to the password policy of the authenticating agent, as described in the
459→
460→
461→Authenticating
462→
463→NSP
464→
465→ agent Requirement
466→
467→User password complexity rules are configurable; the following are the
468→default rules.An NSP local-user password must:
469→• have at least ten characters
470→• not be the same as the previous three passwords
471→• include at least one of the following special characters
472→( ) ? ~ ! @ # $ % & * _ +
473→• include at least one lowercase character
474→• include at least one uppercase character
475→• include at least one digit
476→• not be the username
477→• not equal the e-mail address
478→
479→NFM-P
480→When an NFM-P-authenticated user is prompted to change their
481→password during an NSP login attempt, the new password must
482→conform to the NFM-P password requirements. See“NFM-P user
483→security” (p. 197) for the NFM-P password requirements and
484→expiration policy.
485→
486→WS-NOC
487→When a WS-NOC-authenticated user is prompted to change their
488→password during an NSP login attempt, the password must conform to
489→theCommon WS-NOC Functions password section requirements, of the WS-NOC Administration Guide which are described in .the
490→
491→
492→LDAP,TACACS+ RADIUS and Aattempt. password-change If a password policy change is not is applied required, during the user an NSP must user contact login the
493→systemTACACS+ administrator password requirements.for information about the LDAP, RADIUS, or
494→
495→
496→© 2026 
497→ 
498→           
499→ 2026
500→148
501→ 11
502→--- Page 149 ---
503→NSP user securityLocal user management I set global user password requirements?
504→
505→
506→     I set global user password requirements?
507→
508→8.7.1 Purpose
509→Thepassword password contents policy and defines length, global and expirypassword and requirements reuse limits. for The local password NSP user policy accounts, settings including apply only
510→toexternal local NSPdatabases. user accounts. The password policy does not apply to users managed through
511→
512→
513→8.7.2 Steps
514→
515→1
516→Open Users and Security .
517→
518→2
519→Click More Actions, Settings.
520→
521→3
522→In the Users and Security Settings form, click Password Policy.
523→
524→4
525→Configure user password requirements in any of the following ways:
526→
527→Not Recently Used
528→Specifies the number of unique password that must be
529→used before the current password can be used again.
530→
531→Password Expiry
532→Specifies the number of days a password can be used
533→before it expires.
534→
535→Special Characters
536→Specifies the minimum number of special characters that
537→must be used in the password.
538→Allowable special characters are: ()@#$%&!*_+~
539→
540→ 
541→   
542→   
543→ 
544→   
545→
546→ 
547→   
548→   
549→ 
550→   
551→
552→
553→ 
554→   
555→   
556→   
557→
558→Minimum Length Specifies the minimum number of characters that must
559→                 be used in the password.
560→
561→Digits Specifies the minimum number of numerical characters
562→        that must be used in the password.
563→
564→Uppercase Characters Specifies the minimum number of uppercase characters
565→                       that must be used in the password.
566→
567→Lowercase Characters Specifies the minimum number of lowercase characters
568→                       that must be used in the password.
569→ 
570→   
571→ 
572→ 
573→   
574→
575→Must Not Be Username Enable this option to prevent the account username from
576→being used as a password.
577→
578→Must Not Be Email Address Enablefrom being this usedoption as to a prevent password. the account e-mail address
579→
580→
581→© 2026 
582→ 
583→           
584→ 2026 11
585→149
586→--- Page 150 ---
587→NSP user securityLocal user management I modify a user account?
588→
589→
590→5
591→Click Save.
592→
593→END OF STEPS
594→
595→8.8 How do I modify a user account?
596→
597→8.8.1 Purpose
598→
599→Use this procedure to make changes to local and remote user account parameters:
600→• You can modify all aspects of a local user account, except for the username. You can also
601→change a user’s password or compel the user to change their password.
602→• You can modify select parameters on remote user accounts. You cannot change the username
603→or password on a remote user account, nor can you compel a password change.
604→
605→8.8.2 Steps
606→
607→1
608→Open Users and Security .
609→
610→2
611→Select Users from the drop-down list on the toolbar.
612→
613→3
614→In the Users list, select the user account you want to modify.
615→
616→4
617→On the user account item, click Table Row Actions , Edit User.
618→
619→5
620→
621→On the Update User form, make changes to the following parameters:
622→• Change the user’s First Name, Last Name, or theirDescription text.
623→• Set theAccount State parameter to Active|Suspended.
624→• Assign the user to a different User Group.
625→• Change the user Email Address.
626→• Enable theForce User To Change Password option to compel the user to set a new
627→password at their next NSP login.
628→• To change the user’s password yourself, turn on Change the Password toggle to make the
629→user account Password fields editable. Specify and confirm a new password.
630→
631→
632→© 2026 
633→ 
634→           
635→ 2026
636→150
637→ 11
638→--- Page 151 ---
639→NSP user securityLocal user management I suspend a local user account?
640→
641→
642→6
643→Click Update.
644→
645→END OF STEPS
646→
647→8.9 How do I suspend a local user account?
648→
649→8.9.1 Purpose
650→You can temporarily suspend an NSP local user account. After suspension, the user will lose
651→access to the NSP system after they logout and login again.
652→
653→8.9.2 Steps
654→
655→1
656→Open Users and Security .
657→
658→2
659→Select Users from the drop-down list on the toolbar.
660→
661→3
662→In the Users list, select the user account you want to suspend.
663→
664→4
665→On the user account item, click Table Row Actions , Edit User.
666→
667→5
668→On the Update User form, set the Account State parameter to Suspended.
669→
670→6
671→Click Update.
672→
673→END OF STEPS
674→
675→8.10 How do I configure user account event notifications?
676→
677→8.10.1 Purpose
678→
679→You can configure policies to send e-mail notifications to users for the following events:
680→• user account verification
681→• user account forgotten password reset URL
682→• user account lockout
683→• user account imports from NFM-P
684→
685→
686→© 2026 
687→ 
688→           
689→ 2026 11
690→151
691→--- Page 152 ---
692→NSP user securityLocal user management I configure user account event notifications?
693→
694→
695→For each and event body. type, you can enable or disable e-mail event notifications, and specify the message
696→
697→
698→8.10.2 Steps
699→
700→1
701→Open Users and Security .
702→
703→2
704→Click More Actions, Settings.
705→
706→3
707→In the Users and Security Settings form, click Account Verification and Recovery .
708→
709→4
710→
711→Configure e-mail notifications under any of the following functional areas:
712→1. Under Verify Email, enable notifications to send messages to new users to verify their
713→           e-mail address. You can type a custom subject line and message body or use the
714→2. Under Forgot Password, enable notifications to send a message with a password change
715→           URL to users. You can type a custom subject line and message body or use the
716→3. Under Account Lock, enable notifications to send messages to locked-out users, telling
717→           them how to regain access to NSP. You can type a custom subject line and message
718→or use the defaults.
719→4. Under Import NFMP Users, you can type a custom subject line and message body or
720→the defaults.
721→The default message body informs NFM-P users that they now have a user account
722→           NSP,and provides a temporary password for their account.
723→The user must have an e-mail address configured on their NFM-P account to receive
724→           message.
725→   
726→         
727→   
728→           
729→       
730→         defaults.
731→ 
732→   
733→         
734→ 
735→   
736→             defaults.
737→   
738→   
739→     
740→                   body
741→   
742→       
743→         use
744→ 
745→         
746→           with
747→       
748→ 
749→         
750→   
751→     this
752→
753→
754→5
755→Click Save.
756→
757→END OF STEPS
758→
759→
760→© 2026 
761→ 
762→           
763→ 2026
764→152
765→ 11
766→--- Page 153 ---
767→NSP user securityNSP User Access ControlWhat is User Access Control?
768→
769→
770→ User Access Control
771→
772→8.11 What is User Access Control?
773→
774→8.11.1 Overview
775→User Access Control (UAC) defines what commands a user can perform in an NSP system and
776→what objects those commands can be performed on. NSP UAC is defined through role definitions
777→that are assigned to user groups, and each user is associated with one user group.
778→
779→In an NSP deployment, UAC applies to a user when accessing NSP function. NSP users that
780→access NFM-P or WSNOC will have access determined by what is configured for that user group in
781→NFM-P or WSNOC applications. (eg. An NSP user accessing NFM-P will have access to the
782→NFM-P scope and span profiles that belong to the user’s NFM-P user group).
783→
784→NSP User Access Control is disabled by default, meaning that users can access any NSP function
785→that is not restricted by a specific user group requirement. Users that belong to the admin user
786→group can access all function, including admin-only functions. Users that do not belong to the admin
787→user group can access all non-admin applications. A user that does not belong to the admin user
788→group but has a system administrator role privilege will not be able to access admin-only functions.
789→
790→When NSP UAC is enabled, the role definitions belonging to an NSP user group determine the NSP
791→functions and commands a user can access, and which network objects the user can access.
792→
793→In CLM deployments, UAC applies to CLM users.
794→
795→When UAC is enabled, access is assigned at the NSP level and applies across the NSP GUI. Users
796→will see their specified NSP access permissions enforced when they login to NSP. The user access
797→configuration specified in NSP is enforced in place ofany pre-existing access control setup (from
798→NFM-P or WS-NOC). Local NSP user access to NSP resources is always controlled through NSP,
799→regardless of whether UAC is enabled or not.
800→
801→As a network evolves, an NSP administrator must create or modify user groups, roles, and resource
802→groups to provide the required user access to NSP functions. Be aware of functional crossdependencies.
803→
804→When UAC is enabled, it controls user access to NSP functions independently of the user
805→management systems in NFM-P or WS-NOC.
806→
807→UAC does not apply to WS-NOC or NFM-P GUI or OSS client sessions if pre-existing user access
808→control mechanisms are in use. If you maintain your NSP user accounts in an NFM-P user
809→database, all NFM-P functions related to user lifecycle management, such as password expiry time
810→or failed-login lockout, also affect NSP user access. Local NSP user accounts are configured for
811→UAC and lifecycle management entirely within the NSP.
812→
813→
814→© 2026 
815→ 
816→           
817→ 2026 11
818→153
819→--- Page 154 ---
820→NSP user securityNSP User Access ControlWhat is User Access Control?
821→
822→
823→Figure 8-1 User Access Control architecture
824→
825→
826→User
827→belongs to
828→UserGroup
829→assigned to AnalyticsGroup
830→
831→
832→Role has 
833→Resource
834→NSP Objects
835→assigned to
836→assigned to
837→belong to
838→permissions
839→Group
840→NEs, Ports,
841→(r, w, x)
842→Services, etc.
843→
844→
845→assigned to NSP GUIComponent
846→
847→37372
848→
849→
850→8.11.2 Roles
851→A role object specifies which resources and NSP functions its associated user groups can access.
852→Network resource access is assigned to a role through resource groups, while functional access
853→and Analytics resource access are specified directly on a role object.
854→
855→NSP administrator role
856→
857→A predefined NSP administrator role, user group, and admin user account are automatically created
858→during NSP system installation and cannot be modified. The admin user has full access to all NSP
859→functions and resources, and can define the roles and resource groups that are assigned to user
860→groups. The admin user can create additional roles with the Administrator designation, which carries
861→the same unlimited functional and resource access.
862→
863→8.11.3 User groups
864→A user group associates a group of NSP users with one or more roles, thereby enabling user
865→access to functional areas and resources. Administrators create user groups and assign roles to
866→them, according to the type of network activities the user group is meant to perform. When a role is
867→assigned to a user group, all users within the group have the same access to resources and
868→functions, as specified on the role. A user group can be assigned multiple roles to allow broader
869→access rights for its users.
870→
871→Individual NSP users can be created by external authentication sources (NFM-P, LDAP, RADIUS,
872→TACACS) where users are assigned to corresponding user groups. In order for the members of a
873→user group to have access to NSP resources and functions, the user group name returned by the
874→authentication source must exactly match a corresponding user group name in NSP.
875→
876→Local NSP users and user groups can also be created in the NSP.
877→
878→Users requiring WS-NOC access require a user group assignment that maps to a predefined WS-
879→NOC role; for information, see To map external user groups to predefined WS-NOC roles in the
880→NSP Installation and Upgrade Guide .
881→
882→
883→© 2026 
884→ 
885→           
886→ 2026
887→154
888→ 11
889→--- Page 155 ---
890→NSP user securityNSP User Access ControlWorkflow: Configure User Access Control
891→
892→
893→8.11.4 Resource groups
894→A resource group is a collection of network equipment or services which can be assigned to a role.
895→The role is assigned to a user group, thereby granting the user group access to the network
896→resources in the resource group. Resource groups are defined in Map Layouts and Groups.
897→
898→8.12 Workflow: Configure User Access Control
899→
900→8.12.1 Purpose
901→This workflow describes the recommended order of tasks to configure UAC across NSP. The
902→sequence of tasks outlined here is especially recommended if you are setting up UAC in NSP for
903→the first time. Once you have UAC deployed in NSP, you can configure your user groups, roles, and
904→resource groups in any order.
905→
906→8.12.2 Steps
907→
908→Prerequisite: create group directories and resource groups
909→
910→1
911→         
912→   
913→   
914→         
915→       
916→ rights
917→
918→ 
919→       
920→
921→     
922→
923→2
924→
925→If you intend to use NSP Analytics reporting, you must fully configure Analytics before you
926→        configure Analytics resource access in your roles. You cannot configure resource access
927→role if Analytics is not enabled in the NSP configuration.
928→Create roles
929→
930→You create group directories and resource groups in Map Layouts and Groups. Resource
931→groups (of NEs, ports, LAGs, or services) are applied to role objects to grant user access
932→                                   8.32 “How do I create dotonetworkresources.See a group directory?” (p. 177)and 8.33 “How
933→I configure a resource group?” (p. 177)
934→Optional: configure Analytics reporting
935→ 
936→   
937→ 
938→   
939→       to
940→       
941→           on a
942→ 
943→         
944→
945→ 
946→
947→3
948→Create roles according to the type of tasks your user groups will be performing, and the types of
949→resources they will need to access. A role object specifies access rights to specific NSP
950→functions and resources; ee8.14 “How do I configure a role?” (p. 158)
951→
952→Import or create users and user groups
953→
954→4
955→
956→Choose one of the following options:
957→• Create local NSP users; see8.3 “How do I create an NSP local user?” (p. .143)
958→
959→
960→© 2026 
961→ 
962→           
963→ 2026 11
964→155
965→--- Page 156 ---
966→NSP user securityNSP User Access Control I configure alarm access using roles?
967→
968→
969→• If you have a user access control configuration from NFM-P, it is strongly recommended that
970→you import your users and user groups from NFM-P. This ensures that all of your existing
971→users are included in the new access control setup, and helps ensure a seamless transition
972→from the NFM-P; see8.4 “How do I import users and groups from NFM-P?” (p. . 144)
973→• If you are configuring user access control for a remote authentication source, create new
974→user groups; see 8.16 “How do I configure a user group?” (p. 162).
975→
976→Enable UAC
977→
978→5
979→
980→Note: enforced When when you they enable login UAC to NSP. in NSP, The individual user access users configuration will see their you specified create are access enforced rights
981→
982→in place ofany previous access-control setup, except in the NFM-P and WS-NOC, which
983→eachcontrolled employ through local NSP,user management.regardless of whetherLocal NSP UAC user is enabledaccess to or NSP not. resources is always
984→
985→Onceenable you UAC; have see 8.17 configured and reviewed your user groups and their associated roles, you can
986→ “How do I enable User Access Control?” (p. 163)
987→
988→Update LDAP TLS certificate
989→
990→6
991→Ifupdate the TLS the certificateLDAPS certificate of the LDAPS on the remote NSP deployer authentication VM, as source described is updated, you must also
992→
993→the NSP TLS certificate for LDAPS remote authentication?” (p. 165) 8.19 in “How do I update
994→
995→
996→END OF STEPS
997→
998→8.13 How do I configure alarm access using roles?
999→
1000→8.13.1 Purpose
1001→
1002→Usersroles. Thecan tasksmanage that alarms users for can objects perform that depend are included on the inaccess the resource level provided groups to assigned the resource to their
1003→
1004→groups. Consider the following:
1005→• Networkall endpoints objects for alarmthat have management. multiple endpoints For example, or components, users can onlysuch see as SAPs,alarms require on physical access links to
1006→
1007→when they have access to both endpoints.
1008→• Viewingequipment. alarms on service-related objects requires access to the parent service and associated
1009→
1010→• Inaccess some level cases, is granted access forlevel a port,can be any inherited level of from access the granted parent object.to the parentFor example, NE will when grant no the
1011→same access level to the port.
1012→• In the Unhealthy NEs view, users must have access above “none” to view any NEs that might
1013→appear in the page.
1014→
1015→
1016→© 2026 
1017→ 
1018→           
1019→ 2026
1020→156
1021→ 11
1022→--- Page 157 ---
1023→NSP user securityNSP User Access Control I configure alarm access using roles?
1024→
1025→
1026→The following table describes in more detail how the access levels of resource groups determine
1027→the type of alarm management tasks that users can perform.
1028→
1029→Resource Access level “none” Access level “read” Access level “write” Access level “execute”
1030→1groups
1031→Equipment→PortPort access is equal to the
1032→Can open affected Can open affected object
1033→• Can see alarms on ports and
1034→parent NE access.
1035→object and impacted and impacted object.
1036→associated SAPs if the user
1037→object.
1038→has access to the
1039→corresponding service.
1040→• Can see alarms on physical
1041→links if the user has access
1042→to both endpoints.
1043→NE No
1044→ access to alarms on the
1045→Can open affected
1046→• Can see alarms on the NE
1047→• Can open NE sessions
1048→NE and equipment.
1049→object and impacted
1050→and its equipment. Can see
1051→for the affected NE.
1052→object.
1053→alarms on service sites and
1054→• Can open affected object
1055→SAPs when the user has
1056→and impacted object.
1057→access to the corresponding
1058→service.
1059→• Can see alarms on physical
1060→links if the user has access
1061→on to both endpoints.
1062→• Can see alarms on LSPs if
1063→users have access to both
1064→endpoints.
1065→Service No access to alarms on
1066→Can open affected
1067→• Can see alarms on service.
1068→• Can open affected object
1069→service and associated
1070→object and impacted
1071→and impacted object.
1072→• Can see alarms on
1073→service object.
1074→object.
1075→associated service objects
1076→only if the user has access to
1077→the corresponding
1078→equipment, including NEs
1079→and ports (SAPs, sites,
1080→tunnel bindings).
1081→
1082→Notes:
1083→1. Resource group alarm access for LAG groups is not currently supported.
1084→
1085→The following workflow describes the high-level steps required to create a role intended for alarm
1086→management, and to assign it to a user group. This workflow applies to all NSP users who need to
1087→view object alarms, regardless of which NSP UI they use for alarm viewing.
1088→
1089→8.13.2 Steps
1090→
1091→Create resource groups
1092→
1093→1
1094→Create an NE | port | LAG group directory; 8.32see “How do I create a group directory?”
1095→(p. 177)
1096→
1097→
1098→© 2026 
1099→ 
1100→           
1101→ 2026 11
1102→157
1103→--- Page 158 ---
1104→NSP user securityNSP User Access Control I configure a role?
1105→
1106→
1107→2
1108→Create an NE | port | LAG resource group in the group directory, and define a filter that includes
1109→the network elements the user needs to view; see8.33 “How do I configure a resource group?”
1110→(p. 177)
1111→
1112→3
1113→Create a service group directory; see8.32 “How do I create a group directory?” (p. 177)
1114→
1115→4
1116→Create a Service resource group in the service group directory, and define a filter that includes
1117→the services the user needs to view. You can create multiple service resource groups within a
1118→group directory; see 8.33 “How do I configure a resource group?” (p. 177)
1119→You can create the service resource group based on a Site ID (NE system address) to include
1120→all services for the associated NE.
1121→
1122→Assign resource groups to roles
1123→
1124→5
1125→Add the resource groups to a role; see8.14 “How do I configure a role?” (p. 157).
1126→
1127→6
1128→Assign the role to the appropriate user group; see8.16 “How do I configure a user group?”
1129→(p. 162) .
1130→
1131→END OF STEPS
1132→
1133→8.14 How do I configure a role?
1134→
1135→8.14.1 Purpose
1136→A role object specifies access rights to specific NSP functions and network resources. Roles are
1137→assigned to user groups, bringing all access rights defined on the role to all members of the user
1138→group.
1139→
1140→Consider the following before configuring a role:
1141→• If you intend to assign resource group access to a role, you must configure your resource groups
1142→before completing this procedure.
1143→• If you intend to assign Data Collection and Analysis resource access in this role, you must first
1144→configure Data Collection and Analysis, and must assign Read/Write/Execute permission to the
1145→Analyze/Assure or Data Collection and Analysis category.
1146→• A user with access to device discovery must also be given access to device management.
1147→Device management access is required to view discovered devices.
1148→
1149→
1150→© 2026 
1151→ 
1152→           
1153→ 2026
1154→158
1155→ 11
1156→--- Page 159 ---
1157→NSP user securityNSP User Access Control I configure a role?
1158→
1159→
1160→Note: Do not confuse the Access settings with the Deployment Control settings that are
1161→configured in the settings; the Deployment Control settings determine which views
1162→are activated and available.
1163→
1164→8.14.2 Steps
1165→
1166→1
1167→Open Users and Security.
1168→
1169→2
1170→Select Roles from the drop-down list on the toolbar.
1171→
1172→3
1173→Click Create Role. The Create Role form opens.
1174→
1175→4
1176→In the Identification panel, specify a role name and description.
1177→The Role Name and Description fields can employ only the following special characters: - _ . @
1178→The Role Name string must not contain any spaces, including a leading or trailing space.
1179→
1180→5
1181→ 
1182→     
1183→   
1184→ 
1185→   
1186→   
1187→   
1188→   
1189→       the
1190→
1191→           
1192→ 
1193→   
1194→
1195→6
1196→
1197→Toassign NSP functional access to the role, go to the Action Permissions panel and select
1198→access level from the drop-down list for each NSP GUI you want to include in the role.
1199→                                         164).descriptionoftheaccesspermissions,see 8.18.2 “NSP action permissions” (p.
1200→If you intend to assign Data Collection and Analysis resource access in this role, you must
1201→assign Read/Write/Execute permission to Data Collection and Analysis.
1202→
1203→In the Characteristics panel, you can enable the Administrator designation for the role.
1204→        Tocreate an administrative role with access to all resource groups and function, enable
1205→        Administrator check box.
1206→If you enable this option, no further steps are necessary. ClickCreate to save the role.
1207→               
1208→   
1209→ an
1210→     
1211→   
1212→           For a
1213→
1214→       
1215→           
1216→ 
1217→ 
1218→     
1219→
1220→7
1221→To assign network resource access to the role, go to the Resource Groups Access panel. (For a
1222→detailed explanation of the Resource Groups Access panel, see8.15 “How do I set network
1223→resource access levels?” (p. 161).)
1224→You can assign resource group access globally, to resource group categories, to individual
1225→resource groups, or a combination of these.
1226→
1227→
1228→© 2026 
1229→ 
1230→           
1231→ 2026 11
1232→159
1233→--- Page 160 ---
1234→user securityUser Access Control I configure a role?
1235→
1236→
1237→a. You can assign resource group access globally by resource type. Enable either or both
1238→options:
1239→• Access To All Equipment assigns full permissions on all NE resource groups and port
1240→resource groups to the role.
1241→• Access To All Services assigns full permissions on all service resource groups to the
1242→role.
1243→
1244→b. Expand the resource group category for resource groups you want to include in the role. (For
1245→a detailed explanation of the Network Resource Access panel, 8.15see “How do I set
1246→network resource access levels?” (p. 161).)
1247→• Select an access level from the drop-down list for each resource type you want to include
1248→in the role.
1249→• If you specify an access level to a resource group category, all resource groups within the
1250→category are included in the role at the same access level.
1251→If the Group Category list is empty or the resource group you are looking for does not
1252→appear, you can create resource groups in the Map Layouts and Groups view.
1253→
1254→8
1255→To assign Analytics resource access to the role, go to the Analytics Resource Access panel.
1256→In order for the Analytics Resource Access panel to appear, Analytics reporting must be
1257→enabled and configured in NSP and you must assign Read/Write/Execute access to Analytics in
1258→this role.
1259→
1260→Assign access to Analytics categories or individual Analytics resources in the Analytics
1261→Repository list:
1262→• To obfuscate specific Analytics report data for user groups associated with the role, enable
1263→the Data Anonymization check box.
1264→• Assign access to an entire Analytics category from by enabling the associated Permissions
1265→check box .
1266→• Assign access to individual Analytics resource items by expanding an Analytics category,
1267→selecting an Analytics resource, and enabling its corresponding Permissions check box
1268→.
1269→Some Analytics categories have nested subcategories, each containing individual Analytics
1270→resources. An Analytics category or subcategory with access granted on all contained
1271→resources is displayed as fully-enabled . If access is granted on only some contained
1272→resources, it is displayed as partially-enabled .
1273→
1274→Note: The View/Execute permissions for a report in an Analytics report repository do not
1275→apply to drill-downs.
1276→For example, a user group has View/Execute permission for report A but no permission for
1277→report B. If report B is a drill-down from report A, users will be able to execute report A via
1278→report B, although this might not seem obvious.
1279→
1280→
1281→© 2026 
1282→ 
1283→           
1284→ 2026
1285→160
1286→ 11

### Turn 34 (Function)
[tool_response]
1→--- Page 161 ---
2→ navigation tree
3→
4→
5→3 navigation tree
6→
7→NFM-P navigation tree
8→
9→3.1 Overview
10→
11→3.1.1 General information
12→The NFM-P navigation tree provides multiple views that list the equipment groups, NEs, routing
13→instances, protocols, and other objects in the NFM-P managed network. Objects are listed in a
14→parent-child hierarchy. You can expand the tree to access child objects or collapse the tree for a
15→broader view. You can access property forms, create equipment groups, and perform other
16→functions using the navigation tree window.
17→
18→For more information about network objects, seeChapter 11, “Working with network objects” .
19→
20→In most system workspaces, the navigation tree window opens by default when the NFM-P client is
21→opened. See Chapter 2, “NFM-P custom workspaces” for information about workspaces. See
22→1.15 “To manage a window or form as an external window” (p.for 107) information about managing
23→the display of windows in the GUI.
24→
25→You can use the navigation tree to locate specific objects in the physical and logical network views.
26→See 3.7 “To locate objects in the navigation tree” (p. 165)for information about searching for objects
27→in the navigation tree.
28→
29→The display of objects in the navigation tree is affected by the span of control settings in user
30→preferences; see 1.2.2 “Span of control” (p. 79)in Chapter 1, “NFM-P GUI” .
31→
32→You can use the following methods to navigate the tree and manage objects.
33→• Double-click on an object or click on the + sign to display child objects. When you double-click
34→on an object that has no child objects, a properties form for the object opens.
35→• Double-click on an object or click the - sign to hide child objects.
36→• Select an object and use the cursor keys to navigate the object hierarchy. The up and down
37→arrow keys move the selection up or down in the tree. The right and left arrow keys expand or
38→collapse objects and move up or down in the hierarchy.
39→• Right-click on an object to open a contextual menu, and choose an option. The menu options are
40→specific to the object type. See3.5 “Contextual menus” (p. 164) in this section for more
41→information.
42→
43→Note: Keyboard-based navigation tree operations may not function as expected when you
44→open the client GUI using a third-party access tool, for example, a Citrix server.
45→
46→The following figure shows the NFM-P navigation tree window, with the Equipment view selected.
47→
48→
49→© 2024 
50→ 
51→           
52→ 2024 1
53→161
54→--- Page 162 ---
55→ and labels
56→
57→ navigation tree
58→ navigation tree
59→Icons
60→
61→
62→Figure 3-1 navigation tree - Equipment view
63→
64→
65→3.2 Icons and labels
66→
67→
68→  2024
69→
70→
71→3.2.1 General information
72→Objects in the navigation tree display on a single line with icons and labels.
73→
74→Icons indicate alarm status and object type. The circle at the left indicates the aggregated alarm
75→status. The square indicates the alarm status for the object. Object types are represented by a
76→unique NFM-P icon for each type. Click on the Legend icon on the physical topology map toolbar for
77→a description of alarm and equipment group icons.
78→
79→
80→     
81→© 2024 
82→   
83→162
84→ 1
85→--- Page 163 ---
86→ navigation tree
87→ navigation tree
88→Equipment groups
89→
90→
91→Labels are displayed as text fields separated by commas, and typically provide an object
92→description, ID number, IP address, or other information such as operational or administrative state.
93→You can customize labels for tree objects by selecting the text field definitions that appear and the
94→order in which they appear; see2.12 “To customize tree labels” (p. 152).
95→
96→3.3 Equipment groups
97→
98→3.3.1 General information
99→Equipment groups allow you to organize the network into logical groupings of NEs, for example, in
100→a geographical area, or by equipment type. An equipment group is sometimes called a topology
101→group. Some of the views in the view selector, for example the Equipment view, allow you to use
102→the navigation tree to create and manage equipment groups.
103→
104→An equipment group can contain up to 2000 NEs. The NFM-P client displays NEs in the navigation
105→tree up to a limit of 500 NEs per group. An administrator can specify a system preference for the
106→default number of NEs to display when a group is expanded on the tree (up to 500); see the
107→procedure to configure NFM-P system preferences in the NSP System Administrator Guide . See
108→3.9 “To manage NEs in equipment groups on the navigation tree” (p.for 167) information about
109→managing NEs in equipment groups on the navigation tree.
110→
111→3.4 Navigation tree toolbar
112→
113→3.4.1 General information
114→A toolbar in the NFM-P navigation tree window contains the view selector, the Make Root At Top
115→Level icon, the Copy to Clipboard icon, and the Find icon. The Find field is located below the
116→navigation tree toolbar.
117→
118→3.4.2 View selector
119→The view selector is a drop-down menu that lists the physical and logical network views available in
120→the main navigation tree window.
121→
122→You can choose the following views:
123→• Equipment—displays the physical objects that the NFM-P manages
124→• OSPF—displays all OSPF objects in the network
125→• ISIS—displays all IS-IS objects in the network
126→• Routing—displays the device routing instances and child objects, such as the network interfaces
127→and the configured protocols
128→• Ring Group—displays the ring group objects that the NFM-P manages
129→• Cloud Network—displays DC POD or interconnect management entities
130→
131→3.4.3 Make Root At Top Level icon
132→The root is the highest-level object in the tree. When Equipment is selected in the view selector, you
133→can change the root of the tree to reduce the display of objects in the tree.
134→
135→
136→© 2024 
137→ 
138→           
139→ 2024 1
140→163
141→--- Page 164 ---
142→ navigation tree
143→ navigation tree
144→Contextual menus
145→
146→
147→The Make Root At Top Level icon restores the navigation tree the default Network root when a
148→lower-level object is the current root.
149→
150→See 3.8 “To change the root object of a navigation tree” (p. for166) information about changing the
151→root object of the navigation tree.
152→
153→3.4.4 Copy to Clipboard icon
154→You can use the Copy to Clipboard icon to copy the property form identifier for one or more objects
155→in the tree to the NFM-P clipboard. You can use the clipboard to open forms, send identifiers to
156→other users, and configure search filters. On the topology map, you can use the clipboard to search
157→for objects and create physical links; seeChapter 4, “Topology map management” .
158→
159→See 1.20 “To use the NFM-P clipboard” (p. 112)for more information about the NFM-P clipboard,
160→
161→3.4.5 Find icon and Find field
162→You can use the Find icon or the Find field to locate and highlight objects in the navigation tree.
163→
164→See 3.7 “To locate objects in the navigation tree” (p. 165)for more information about locating
165→objects in the tree.
166→
167→3.5 Contextual menus
168→
169→3.5.1 General information
170→When you right-click on an object in the NFM-P navigation tree, a contextual menu opens for that
171→object. You can use contextual menus to:
172→• create objects
173→• configure object properties
174→• perform maintenance functions
175→• change the state of objects
176→• open a different management interface, for example, a CLI
177→• change the root object in the navigation tree
178→
179→The available contextual menu options vary, depending on the object type.
180→
181→3.6 Basic navigation tree procedures
182→
183→3.6.1 General information
184→The following procedures describe how to use the NFM-P navigation tree.
185→
186→
187→© 2024 
188→ 
189→           
190→ 2024
191→164
192→ 1
193→--- Page 165 ---
194→ navigation tree
195→ navigation tree
196→ locate objects in the navigation tree
197→
198→
199→   locate objects in the navigation tree
200→
201→3.7.1 General information
202→You can use the Find icon or the Find field in the navigation tree header to locate objects in the
203→navigation tree. Objects that match the search terms are highlighted sequentially in the tree. Each
204→search can produce up to 200 results.
205→
206→A system preferences threshold may limit the number of NEs displayed in the navigation tree when
207→an equipment group is expanded. When you use the Find icon or Find field, the search results
208→include NEs and descendant objects that were not displayed prior to the search, even if they
209→exceed the system preferences NE display threshold.
210→
211→Note: The NFM-P client displays NEs in the navigation tree up to a maximum limit of 500 NEs
212→per equipment group. When an equipment group contains more than 500 NEs, some objects
213→may not appear in the search results.
214→When the system limit of 500 NEs is already displayed under the equipment group, and a
215→matching NE object or descendant object is not among the displayed NEs, the matching
216→object is not displayed or highlighted.
217→See 3.9 “To manage NEs in equipment groups on the navigation tree” (p.for 167) more information
218→about managing the display of NEs in equipment groups.
219→
220→3.7.2 Steps
221→
222→1
223→To locate an object using the Find icon:
224→1. Click the Find icon or press Ctrl-F. The search panel appears.
225→2. Enter search terms in the attribute fields. The available fields vary depending on the
226→selected view.
227→3. Click Find in the search panel or press Enter. The navigation tree expands to show the first
228→matching object highlighted.
229→4. To find additional matching objects, click the Next button or press F3. The navigation tree
230→expands to show the next matching object highlighted in the tree.
231→The Next and Previous buttons are available when more than one object matches the
232→search term.
233→5. Topress return Shift-F3. to the previous matching object in the navigation tree, click the Previous button or
234→
235→6. To remove all search terms from the search panel, click Clear.
236→7. Topress close Ctrl-F. the search panel, click the Find icon at the top of the navigation tree window or
237→
238→
239→2
240→To locate an object using the Find field:
241→
242→Note: For some of the views in the view selector the Find field is not available.
243→
244→
245→© 2024 
246→ 
247→           
248→ 2024 1
249→165
250→--- Page 166 ---
251→ navigation tree
252→ navigation tree
253→ change the root object of a navigation tree
254→
255→
256→1. Enter a search term in the Find field. Search terms are based on object labels. A tooltip for
257→the Find field shows a list of the labels. See “To customize tree labels”
258→(p. 152) for information about how to customize labels.
259→2. Press Enter. The navigation tree expands to show the first matching object highlighted.
260→3. To find additional matching objects, click the Next button or press F3. The navigation tree
261→expands to show the next matching object highlighted in the tree.
262→The Next and Previous buttons are enabled when more than one object matches the
263→search term.
264→4. To return to the previous matching object in the navigation tree, click on the Previous button
265→or press Shift-F3.
266→
267→END OF STEPS
268→
269→3.8 To change the root object of a navigation tree
270→
271→3.8.1 General information
272→The root is the highest-level object in the tree. When Equipment is selected in the view selector, you
273→can change the root of the tree.
274→
275→Perform this procedure to make a lower-level object the root of the current navigation tree window
276→or a new navigation tree window, or to restore the default Network root.
277→
278→3.8.2 Steps
279→
280→1
281→Open the navigation tree window and select the Equipment view.
282→
283→2
284→Change the root object of a tree. Perform any of the following:
285→
286→a. Make a selected object the root of the current tree. Right-click on the object and choose
287→Make Root. The navigation tree is refreshed with the selected object as the root of the tree.
288→
289→b. Make a selected object the root of a new navigation tree window. Right-click on the object
290→and choose Make Root in New Tree. A new navigation tree window opens with the selected
291→object as the root of the tree.
292→Up to five navigation tree windows can be open at one time.
293→The Make Root in New Tree option is also available when you right-click on an equipment
294→group in the topology map navigation tree, or on the map background. A new navigation tree
295→window opens with the equipment group selected or displayed in the map as the root of the
296→tree.
297→The Make Root In New Tree option is not available for the root object of a tree.
298→
299→c. Restore the default Network object as the root object. Click on the Make Root At Top Level
300→icon on the navigation tree toolbar.
301→
302→
303→© 2024 
304→ 
305→           
306→ 2024
307→166
308→ 1
309→--- Page 167 ---
310→ navigation tree
311→ navigation tree
312→ manage NEs in equipment groups on the navigation tree
313→
314→
315→The Make Root At Top Level icon is when a lower-level object is the root of the tree.
316→
317→END OF STEPS
318→
319→3.9 To manage NEs in equipment groups on the navigation tree
320→
321→3.9.1 General information
322→On the navigation tree, you can open an NEs list form for a selected equipment group and use the
323→form to search for NEs, to show the NEs you require on the tree, and to move NEs to other groups.
324→The form lists all of the NEs in the selected equipment group.
325→
326→An administrator can specify a threshold value in system preferences for the default number of NEs
327→to display when a group is expanded in the tree. See the procedure to configure NFM-P system
328→preferences in theNSP System Administrator Guide . When an equipment group contains more NEs
329→than the threshold value, some of the NEs are not displayed in the tree. When the threshold value
330→is less than 500, you can use the NEs list form to temporarily display additional NEs in the group,
331→above the threshold amount, up to 500.
332→
333→An equipment group can contain up to 2000 NEs. The NFM-P client displays NEs in the navigation
334→tree up to a maximum limit of 500 NEs per group. When an equipment group contains more than
335→500 NEs, some of the NEs are not displayed in the tree. You can use the NEs list form to access all
336→of the NEs in the group, or to move NEs to other groups.
337→
338→3.9.2 Steps
339→
340→1
341→
342→Open the NEs list form for an equipment group in the navigation tree. Right-click on the
343→         equipment group object and choose List NEs. The NEs list form opens.
344→When you expand an equipment group in the tree, and the number of NEs in the group
345→or exceeds the threshold value set in system preferences, a message is displayed in the
346→         navigation tree under the equipment group object. You can click on the message to open
347→NEs list form for the equipment group.
348→The message remains in the tree display, even if the number of NEs in the equipment
349→reduced below the system preferences threshold.
350→                     
351→ 
352→             
353→   
354→                   equals
355→   
356→       
357→         
358→         
359→           the
360→       
361→                       group is
362→       
363→ 
364→
365→2
366→Manage NEs using the NEs list form. Perform any of the following:
367→
368→a. Locate NEs in the tree or display additional NEs. Select an NE in the list and click Show on
369→Tree. The selected NE is highlighted in the tree.
370→If the selected NE was not previously displayed in the tree, it is added to the display for the
371→equipment group and highlighted.
372→Alternatively, you can use the Find icon or Find field in the navigation tree header to locate
373→NEs in the tree or to display additional NEs; 3.7see “To locate objects in the navigation tree”
374→(p. 165) .
375→
376→
377→© 2024 
378→ 
379→           
380→ 2024 1
381→167
382→--- Page 168 ---
383→ navigation tree
384→ navigation tree
385→ manage NEs in equipment groups on the navigation tree
386→
387→
388→Theroot displayobject of of the additional tree is NEschanged, is not the preserved. next display If the of navigation the NEs in tree the window group revertsis closed orthe the
389→
390→default display.
391→Upthe tonavigation 500 NEs tree. (the If maximum this limit systemis exceeded, limit) cana message be displayed is displayed. under an equipment group in
392→
393→b. Move NEs to other groups.
394→1. Select one or more NEs in the list and click Move to Group. A drop-down menu opens.
395→2. Choosegroup. an equipment group in the menu. The selected NEs are moved to the selected
396→
397→Alternatively,navigation tree you or can topology move map. NEs to different groups by clicking and dragging icons on the
398→
399→
400→3
401→Close the list form.
402→Whenautomatically the NE when List formyou changefor an equipment the view in group the view is opened selector, from close the thenavigation navigation tree, tree it closes window,
403→or change the root object of the tree.
404→
405→END OF STEPS
406→
407→
408→© 2024 
409→ 
410→           
411→ 2024
412→168
413→ 1
414→--- Page 169 ---
415→Topology map management
416→
417→
418→4 Topology map management
419→
420→
421→4.1 Topology map types
422→
423→4.1.1 Service tunnel topology map
424→
425→TopologyA service from tunnel the topologyNFM-P main map menu. is available The Service on the TunnelNFM-P Topology by choosing Application→Service map is displayed, Tunnelas shown in
426→the following figure.
427→
428→Figure 4-1 Service tunnel topology map
429→
430→
431→Iconsthe status in the of service the device. path Redtopology means map that represent the device devices. is down. The Green color of means the device that the icon device represents is up.
432→Yellowsuspended means management that the device state. is See being synchronized. Purple means that the device is in a
433→
434→discovery and management states.Chapter 9, “Device discovery” for information about device
435→
436→Link groups between devices represent service tunnels. When a link group is red, at least one
437→tunnel in the link group is down. For link groups between managed devices, right click the link group
438→icon to list and edit tunnels in the link group. For link groups between managed and unmanaged
439→devices, right-click the link group icon to open contextual menus and submenus which allow you to
440→open additional information forms for the service tunnel, including the properties form.
441→
442→
443→© 2024 
444→ 
445→           
446→ 2024 1
447→169
448→--- Page 170 ---
449→Topology map management
450→Topology map types
451→
452→
453→4.1.2 EPS path topology maps
454→An EPS path topology map is available on the NFM-P by choosing Application→EPS Path Topology
455→from the NFM-P main menu. The EPS path topology map displays a static representation of mobile
456→network objects and EPS paths. Each network object icon represents an aggregate of all network
457→objects of that type. For SGWs and PGWs, the icon represents an aggregate of all instances of that
458→gateway type and all network objects that contain instances of that type. Each EPS path link
459→represents an aggregate of all EPS paths of a specific type.
460→
461→4.1.3 LSP path topology map
462→An LSP path topology map is available from the MPLS Path form and the LSP Path form. See
463→4.5 “To open an MPLS provisioned path map from the MPLS Path form” (p.to 179)view the map
464→from the MPLS Path form. See4.6 “To open a dynamic LSP path map from the LSP Path form”
465→(p. 179) to view the map from the LSP Path form.
466→The LSP path topology map is used to view a specific provisioned, actual, or CSPF LSP path in the
467→context of its source, and transient and destination hops. The following figure shows an LSP path
468→topology map.
469→
470→Figure 4-2 LSP path topology map
471→
472→
473→When you view the LSP path topology map, hops are linked by straight lines, where each line
474→represents a sub-path between two hops of the LSP path. The direction of each path is indicated by
475→an arrow. Green lines indicate provisioned paths, and gray lines indicate actual paths.
476→
477→4.1.4 LSP cross-connect topology map
478→An LSP cross-connect topology map is available from the LSP Path form. To view the map from the
479→LSP Path form, see4.7 “To open a dynamic LSP cross-connect topology map” (p. 180).
480→Theits source, LSP cross-connect and transient topology and destination map is usedhops. to The view following a specific figure LSP shows cross-connect the LSP cross-connect in the context of
481→
482→topology map.
483→
484→
485→© 2024 
486→ 
487→           
488→ 2024
489→170
490→ 1
491→--- Page 171 ---
492→Topology map management
493→Topology map types
494→
495→
496→Figure 4-3 LSP cross-connect map
497→
498→
499→4.1.5 Service topology maps
500→You can open a topology map for a selected service from the Manage Services form by clicking
501→Topology View. The following figure shows a service topology map. Large NE icons represent
502→managed devices. Small NE icons represent unmanaged devices. The label of an NE icon indicates
503→the service name and the NE IP address.
504→
505→Figure 4-4 Service topology map
506→
507→
508→The symbol and color in the top-right corner of the managed device icon represents the aggregated
509→alarm status, which is the most severe alarm on any service that includes the device. The symbol
510→immediately below the aggregated alarm status and the color of the icon indicate the alarm status
511→
512→
513→© 2024 
514→ 
515→           
516→ 2024 1
517→171
518→--- Page 172 ---
519→Topology map management
520→Topology map types
521→
522→
523→for the currently displayed service site. A red icon indicates that the service site is down. A green
524→icon indicates that the service site is up.
525→
526→A port icon represents a managed access interface. A port label includes the port number and the
527→inner and outer port encapsulation values. A service site can support up to 20 SAPs. When the
528→number of SAPs on a service site exceeds 20, the SAPs on the site are grouped into a SAP group,
529→represented by a SAP group icon. When the number of SAPs drops below 20, the SAP group icon
530→is replaced with the icons for the individual SAPs. To view the list of SAPs in a SAP group, rightclick on the SAP group icon and choose List L2 Access Interface or List L3 Access Interface,
531→depending on the service type. The corresponding Site form for the service opens.
532→
533→SAP aggregation group icons represent SAP aggregation groups configured for a VLL Apipe on the
534→7705 SAR. The SAP aggregation group is linked to the service site and each of the individual SAPs.
535→To hide the associated SAPs for a SAP aggregation group, right-click on the SAP aggregation
536→group icon and choose Hide SAPs. Choose Show SAPs to show them again.
537→
538→A line between two map objects represents a link or group of links. Links between device icons
539→represent service circuits. Links between device icons and port icons represent the binding of an
540→access port or interface to a service. The symbol and color in the bottom right corner of the
541→managed device icon represents the connectivity alarm status. During a resynchronization of the
542→managed device, the icon represents the resynchronization status, and is yellow. The status is
543→inherited from the link endpoints. A plus sign icon located in the centre of the link indicates a
544→bidirectional group link. An arrow icon located on the link indicates a unidirectional link and identifies
545→the direction of the path.
546→Right-clickingfunctions that on include a managed the following: site, port, or link opens a contextual menu that allows you to perform
547→
548→• choose layout options
549→• open an object properties form
550→• turn up or shut down an object
551→• create a service object
552→• create a service object from a template, if a template is bound to the service
553→• delete an object
554→• open a CLI session
555→• manage scripts
556→• plot statistics
557→• display or highlight service topology features
558→YouManage can Servicesview multiple form servicesduring map on acreation. map at the same time if the services are selected from the
559→
560→
561→Service segmentation
562→A service segmentation view is also available to aid in conceptualizing complex services. Segments
563→are logical grouping of interconnected sites, services, and bindings. The segmentation view is
564→available for VPLS and VLL services.
565→A service segment is considered to be a portion of a single service that extends to multiple sites
566→connected within that segment. It is based on the service type through one of the possible
567→
568→
569→© 2024 
570→ 
571→           
572→ 2024
573→172
574→ 1
575→--- Page 173 ---
576→Topology map management
577→Topology map types
578→
579→
580→connection topologies (for example, mesh, PBB tunnels, a switching VLL, rings, and so on), without
581→having pass through any connectors such as spokes, CCAGs, or SCPs (SAP-to-SAP).
582→
583→General examples of segments in Layer 2 service topologies include:
584→• A simple pair or single spoke/mesh SDP binding comprises one segment
585→• A mesh of a multi-NE VPLS service comprises one segment
586→• A multi-NE mesh with a spoke SDP to a single NE comprises two segments
587→• Each mesh of VSIs forms a segment (applicable to H-VPLS)
588→
589→Just a few examples of the many possible service-specific segmentation configurations include
590→scenarios such as the following:
591→• H-VPLS (Inter-Metro with redundant spoke SDPs):
592→− One application of H-VPLS is the connection of two or more geographically-dispersed VPLS
593→domains belonging to the same customer. Two spoke SDP connections are used to connect
594→each VPLS between the two metros, either in a redundant PW spokes topology or under STP
595→protocol. The redundant spokes comprise one segment, while each VPLS will also comprise
596→one or more segments, depending on their specific configurations.
597→• VLL Switching:
598→− For a VLL service at a switching router, a terminating PE device has at least one VLL SAP,
599→while a switching PE device has a VLL instance which cross-connects two spoke bindings. All
600→VLL instances of such a service must have the same service ID, and if the VLL has one or
601→more switching sites, it must have at least two terminating sites. In this scenario, the primary
602→and redundant spoke SDPs on the same network endpoint are considered to be in the same
603→segment.
604→• PBB:
605→− In a PBB configuration, the B-VPLS is considered a service tunnel, from the I-VPLS or
606→I-Epipe perspective. Therefore, the sites connected via a B-VPLS (that is, having the same
607→ISID) are considered to be in one segment.
608→− I-Sites bound to the same PBB tunnel (B-VPLS) and having the same ISID exist in the same
609→segment.
610→− Epipe sites bound to same PBB tunnel (B-VPLS) exist in the same segment
611→
612→Whenever you modify a service, the following actions can trigger segment creation, modification, or
613→deletion in a segmented service view:
614→• Adding or removing service sites
615→• Creating or deleting spoke and/or mesh bindings (either through the NFM-P GUI or CLI)
616→• Creation or deletion of VLAN Uplinks by NFM-P
617→
618→You can access the segmented view of a service by right-clicking on an empty portion of the
619→background in the service’s topology view. A contextual menu allows you to activate or de-activate
620→the segmented view for the service.
621→
622→In a segmented view, the outlined links of all spoke bindings, mesh bindings, or VLAN Uplinks are
623→colored in the same distinct way for the segment they belong to. However, there are currently only
624→19 different colors available for use in showing service segments. If all the colors for a specific
625→service are used, a warning message is logged to indicate this.
626→
627→
628→© 2024 
629→ 
630→           
631→ 2024 1
632→173
633→--- Page 174 ---
634→  2024
635→
636→
637→Topology map management
638→Topology map types
639→
640→
641→The following figure shows an example of how the displays the segmented view of an
642→H-VPLS Metro-to-Metro service.
643→
644→Figure 4-5 Service segmentation example
645→
646→
647→4.1.6 Composite service topology maps
648→You can use the NFM-P to view composite service topology and flat topology maps. The figure
649→below shows a sample composite service topology map. When you open a flat topology view map,
650→the navigation tree is not part of the map.
651→
652→Figure 4-6 Composite service topology map
653→
654→
655→     
656→© 2024 
657→   
658→174
659→ 1
660→--- Page 175 ---
661→Topology map management
662→Topology map types
663→
664→
665→In a composite service topology map, you can use the navigation tree at the left side display the
666→composite service and service tier hierarchy starting from the services object. The map navigation
667→tree displays the following:
668→• composite services and service tiers, including service name and tier number
669→• status of the composite services and their tiers
670→
671→Double-click on a composite service object in the map panel to display the service objects that
672→belong to the composite service. Double-click on the service objects to display the service sites and
673→access interfaces. The links or groups of links between the service sites and access interfaces are
674→also displayed.
675→
676→In the composite service topology map, all service objects in the composite service are displayed
677→simultaneously. The service sites, access interfaces, and the links or groups of links between them
678→are also displayed. The navigation tree is thus not required in this view. The following figure shows
679→a sample composite service flat topology map.
680→
681→Figure 4-7 Composite service flat topology map
682→
683→
684→You can right-click an object icon or link group icon to turn up, shut down, or display the properties
685→form for the item.
686→
687→You can also perform Ethernet CFM diagnostics directly from the composite service flat map.
688→
689→
690→© 2024 
691→ 
692→           
693→ 2024 1
694→175

### Turn 35 (Assistant)
Los PDFs ya están leídos. Armo un shell Python tipo Grok: login, prompt, comandos `/` y navegación del árbol NFM-P (equipment, MPLS, servicios, alarmas).
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\.gitignore
- new_string: __pycache__/
*.py[cod]
*.egg-info/
.eggs/
dist/
build/
.venv/
venv/
.env
.nsp-grok-history
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.log

- old_string: 
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\pyproject.toml
- new_string: [project]
name = "nsp-grok"
version = "24.11.0"
description = "NSP-Grok 24.11 — NFM-P classic management shell for IP/MPLS networks"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "rich>=13.7.0",
    "prompt_toolkit>=3.0.47",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
nsp-grok = "nsp_grok.app:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["nsp_grok*"]

[tool.pytest.ini_options]
testpaths = ["tests"]

- old_string: 
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\requirements.txt
- new_string: rich>=13.7.0
prompt_toolkit>=3.0.47

- old_string: 
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\__init__.py
- new_string: """NSP-Grok 24.11 — NFM-P classic management shell."""

__version__ = "24.11.0"
RELEASE = "24.11"
PRODUCT = "NSP-Grok"
COMPONENT = "Network Functions Manager — Packet"

- old_string: 

### Turn 36 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\__init__.py has been created successfully.

### Turn 37 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\pyproject.toml has been created successfully.

### Turn 38 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\.gitignore has been created successfully.

### Turn 39 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\requirements.txt has been created successfully.

### Turn 40 (Assistant)
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\models.py
- new_string: """NFM-P-inspired object model (equipment, routing, MPLS, services, faults)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Severity = Literal["critical", "major", "minor", "warning", "cleared"]
Access = Literal["none", "read", "write", "execute"]
AdminState = Literal["up", "down"]
OperState = Literal["up", "down", "degraded"]
MgmtState = Literal["managed", "unmanaged", "suspended", "resync"]


SEVERITY_ORDER = {
    "critical": 4,
    "major": 3,
    "minor": 2,
    "warning": 1,
    "cleared": 0,
}


@dataclass
class User:
    username: str
    password_hash: str
    salt: str
    group: str
    role: str
    display_name: str
    email: str = ""
    state: Literal["active", "suspended"] = "active"
    force_password_change: bool = False
    password_history: list[str] = field(default_factory=list)
    failed_logins: int = 0
    locked_until: datetime | None = None
    last_login: datetime | None = None
    # Resource groups the user may see (empty = all).
    span: list[str] = field(default_factory=list)
    access: Access = "execute"


@dataclass
class Port:
    name: str
    mode: str
    encap: str
    admin: AdminState
    oper: OperState
    speed: str
    description: str = ""
    lag: str = ""


@dataclass
class Card:
    slot: str
    card_type: str
    equipped: str
    admin: AdminState
    oper: OperState
    ports: list[Port] = field(default_factory=list)


@dataclass
class NetworkElement:
    name: str
    system_ip: str
    ne_type: str
    version: str
    site: str
    group: str
    admin: AdminState = "up"
    oper: OperState = "up"
    management: MgmtState = "managed"
    chassis_mac: str = ""
    cards: list[Card] = field(default_factory=list)
    protocols: list[str] = field(default_factory=list)


@dataclass
class MplsInterface:
    ne: str
    name: str
    interface: str
    te_metric: int
    admin: AdminState
    oper: OperState
    srlgs: list[str] = field(default_factory=list)


@dataclass
class MplsPath:
    name: str
    hops: list[str]
    hop_type: str = "strict"


@dataclass
class Lsp:
    name: str
    lsp_type: str  # dynamic, static, sr-te, p2mp, bypass
    signaling: str  # rsvp, ldp, sr
    from_ne: str
    to_ne: str
    path: str
    hops: list[str]
    admin: AdminState = "up"
    oper: OperState = "up"
    metric: int = 10
    bandwidth_mbps: int = 0
    setup_priority: int = 7
    hold_priority: int = 7
    protection: str = "none"


@dataclass
class ServiceTunnel:
    sdp_id: int
    name: str
    from_ne: str
    to_ne: str
    signaling: str
    lsp: str
    admin: AdminState = "up"
    oper: OperState = "up"
    far_end: str = ""


@dataclass
class Service:
    svc_id: int
    name: str
    svc_type: str  # vprn, vpls, epipe, ies
    customer: str
    customer_id: int
    sites: list[str]
    sdp_ids: list[int] = field(default_factory=list)
    admin: AdminState = "up"
    oper: OperState = "up"
    mtu: int = 1514
    description: str = ""


@dataclass
class Alarm:
    id: str
    severity: Severity
    probable_cause: str
    object_fdn: str
    ne: str
    raised: datetime
    additional_text: str = ""
    acked: bool = False
    acked_by: str = ""
    cleared: bool = False


@dataclass
class StatSample:
    object_fdn: str
    counter: str
    value: float
    unit: str
    collected: datetime


@dataclass
class Task:
    id: int
    user: str
    operation: str
    object_fdn: str
    state: str
    started: datetime
    finished: datetime | None = None

- old_string: 
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\auth.py
- new_string: """Local user authentication, password policy, lockout, and UAC helpers.

Mirrors NSP 24.11 Users and Security: local users, user groups, roles,
span of control, password complexity, and brute-force lockout.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from nsp_grok.models import Access, User

PBKDF2_ROUNDS = 120_000
MAX_FAILED = 5
LOCK_MINUTES = 5

# NSP local-user default policy (Admin Guide 8.6).
PASSWORD_POLICY = {
    "min_length": 10,
    "uppercase": 1,
    "lowercase": 1,
    "digits": 1,
    "special": 1,
    "special_chars": "()?~!@#$%&*_+",
    "history": 3,
    "must_not_be_username": True,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ROUNDS
    ).hex()
    return digest, salt


def verify_password(user: User, password: str) -> bool:
    digest, _ = hash_password(password, user.salt)
    return hmac.compare_digest(digest, user.password_hash)


def check_password_policy(username: str, password: str, email: str = "") -> list[str]:
    errors: list[str] = []
    p = PASSWORD_POLICY
    if len(password) < p["min_length"]:
        errors.append(f"minimum length is {p['min_length']}")
    if sum(c.isupper() for c in password) < p["uppercase"]:
        errors.append("at least one uppercase letter required")
    if sum(c.islower() for c in password) < p["lowercase"]:
        errors.append("at least one lowercase letter required")
    if sum(c.isdigit() for c in password) < p["digits"]:
        errors.append("at least one digit required")
    if sum(c in p["special_chars"] for c in password) < p["special"]:
        errors.append(f"at least one special character required ({p['special_chars']})")
    if p["must_not_be_username"] and password.lower() == username.lower():
        errors.append("password must not equal the username")
    if email and password.lower() == email.lower():
        errors.append("password must not equal the e-mail address")
    return errors


def authenticate(users: dict[str, User], username: str, password: str) -> tuple[User | None, str]:
    """Return (user, error). Usernames are case-insensitive (NSP 8.1.1)."""
    key = username.strip().lower()
    user = users.get(key)
    if user is None:
        return None, "Invalid username or password."
    if user.state != "active":
        return None, "Account is suspended."
    if user.locked_until and user.locked_until > _now():
        remaining = int((user.locked_until - _now()).total_seconds() // 60) + 1
        return None, f"Account locked. Retry in {remaining} min."
    if not verify_password(user, password):
        user.failed_logins += 1
        if user.failed_logins >= MAX_FAILED:
            user.locked_until = _now() + timedelta(minutes=LOCK_MINUTES)
            return None, (
                f"Account locked after {MAX_FAILED} failed attempts "
                f"({LOCK_MINUTES} min)."
            )
        left = MAX_FAILED - user.failed_logins
        return None, f"Invalid username or password. {left} attempt(s) remaining."
    user.failed_logins = 0
    user.locked_until = None
    user.last_login = _now()
    return user, ""


def change_password(user: User, current: str, new: str) -> list[str]:
    if not verify_password(user, current):
        return ["current password is incorrect"]
    errors = check_password_policy(user.username, new, user.email)
    new_hash, _ = hash_password(new, user.salt)
    if new_hash in user.password_history[-PASSWORD_POLICY["history"] :]:
        errors.append(
            f"password must not match the previous {PASSWORD_POLICY['history']} passwords"
        )
    if errors:
        return errors
    digest, salt = hash_password(new)
    user.password_history.append(user.password_hash)
    user.password_hash = digest
    user.salt = salt
    user.force_password_change = False
    return []


def can(user: User, action: Access) -> bool:
    rank = {"none": 0, "read": 1, "write": 2, "execute": 3}
    return rank[user.access] >= rank[action]


def in_span(user: User, group: str, ne_name: str = "") -> bool:
    if not user.span or user.role == "administrator":
        return True
    if group in user.span:
        return True
    return ne_name in user.span

- old_string: 
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\lab.py
- new_string: """In-memory demo lab: Argentina IP/MPLS core managed by NFM-P 24.11."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from nsp_grok.auth import hash_password
from nsp_grok.models import (
    Alarm,
    Card,
    Lsp,
    MplsInterface,
    MplsPath,
    NetworkElement,
    Port,
    Service,
    ServiceTunnel,
    StatSample,
    User,
)


def _ts(hours_ago: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours_ago)


def _user(username: str, password: str, **kwargs) -> User:
    digest, salt = hash_password(password)
    return User(
        username=username,
        password_hash=digest,
        salt=salt,
        password_history=[digest],
        **kwargs,
    )


def _ports(names: list[tuple[str, str, str, str, str]]) -> list[Port]:
    out: list[Port] = []
    for name, mode, speed, admin, oper in names:
        encap = "null" if mode == "network" else "dot1q"
        out.append(
            Port(
                name=name,
                mode=mode,
                encap=encap,
                admin=admin,  # type: ignore[arg-type]
                oper=oper,  # type: ignore[arg-type]
                speed=speed,
                description=f"{mode} {name}",
            )
        )
    return out


def _line_card(slot: str, card_type: str, ports: list[Port]) -> Card:
    down = any(p.oper == "down" for p in ports)
    return Card(
        slot=slot,
        card_type=card_type,
        equipped=card_type,
        admin="up",
        oper="degraded" if down else "up",
        ports=ports,
    )


def seed_users() -> dict[str, User]:
    users = [
        _user(
            "admin",
            "Nokia123!",
            group="administrators",
            role="administrator",
            display_name="NSP Administrator",
            email="admin@lab.nsp",
            access="execute",
        ),
        _user(
            "operator",
            "Nokia123!",
            group="ip-mpls-ops",
            role="operator",
            display_name="MPLS Operator",
            email="operator@lab.nsp",
            access="write",
        ),
        _user(
            "noc",
            "Nokia123!",
            group="noc-ba",
            role="fault-manager",
            display_name="NOC Buenos Aires",
            email="noc@lab.nsp",
            access="execute",
            span=["METRO-BA", "PE-BAIRES-01", "PE-BAIRES-02"],
        ),
        _user(
            "viewer",
            "Nokia123!",
            group="read-only",
            role="monitor",
            display_name="Read-only Viewer",
            email="viewer@lab.nsp",
            access="read",
        ),
    ]
    return {u.username: u for u in users}


def seed_nes() -> dict[str, NetworkElement]:
    nes = [
        NetworkElement(
            name="PE-BAIRES-01",
            system_ip="10.10.1.1",
            ne_type="7750 SR-12e",
            version="TiMOS-C-24.10.R1",
            site="Buenos Aires",
            group="METRO-BA",
            chassis_mac="00:03:fa:11:01:01",
            protocols=["ospf", "isis", "ldp", "rsvp", "mpls", "bgp", "sr"],
            cards=[
                Card("A", "cpm-2", "cpm-2", "up", "up"),
                Card("B", "cpm-2", "cpm-2", "up", "up"),
                _line_card(
                    "1",
                    "imm48-sfp+",
                    _ports(
                        [
                            ("1/1/1", "network", "10G", "up", "up"),
                            ("1/1/2", "network", "10G", "up", "up"),
                            ("1/1/3", "network", "10G", "up", "up"),
                            ("1/1/10", "access", "10G", "up", "up"),
                            ("1/1/11", "access", "10G", "up", "down"),
                        ]
                    ),
                ),
            ],
        ),
        NetworkElement(
            name="PE-BAIRES-02",
            system_ip="10.10.1.2",
            ne_type="7750 SR-7",
            version="TiMOS-C-24.10.R1",
            site="Buenos Aires",
            group="METRO-BA",
            chassis_mac="00:03:fa:11:01:02",
            protocols=["ospf", "isis", "ldp", "rsvp", "mpls", "bgp"],
            cards=[
                Card("A", "cpm-2", "cpm-2", "up", "up"),
                _line_card(
                    "1",
                    "imm24-sfp+",
                    _ports(
                        [
                            ("1/1/1", "network", "10G", "up", "up"),
                            ("1/1/2", "network", "10G", "up", "up"),
                            ("1/1/10", "access", "1G", "up", "up"),
                        ]
                    ),
                ),
            ],
        ),
        NetworkElement(
            name="P-CORE-01",
            system_ip="10.10.0.1",
            ne_type="7950 XRS-20",
            version="TiMOS-C-24.10.R1",
            site="Core BA",
            group="CORE",
            chassis_mac="00:03:fa:00:00:01",
            protocols=["isis", "ldp", "rsvp", "mpls", "sr"],
            cards=[
                Card("A", "cpm-xrs", "cpm-xrs", "up", "up"),
                _line_card(
                    "1",
                    "xcm-2s",
                    _ports(
                        [
                            ("1/1/1", "network", "100G", "up", "up"),
                            ("1/1/2", "network", "100G", "up", "up"),
                            ("1/1/3", "network", "100G", "up", "up"),
                            ("1/1/4", "network", "100G", "up", "up"),
                        ]
                    ),
                ),
            ],
        ),
        NetworkElement(
            name="P-CORE-02",
            system_ip="10.10.0.2",
            ne_type="7950 XRS-20",
            version="TiMOS-C-24.10.R1",
            site="Core CBA",
            group="CORE",
            chassis_mac="00:03:fa:00:00:02",
            protocols=["isis", "ldp", "rsvp", "mpls", "sr"],
            cards=[
                Card("A", "cpm-xrs", "cpm-xrs", "up", "up"),
                _line_card(
                    "1",
                    "xcm-2s",
                    _ports(
                        [
                            ("1/1/1", "network", "100G", "up", "up"),
                            ("1/1/2", "network", "100G", "up", "up"),
                            ("1/1/3", "network", "100G", "up", "up"),
                        ]
                    ),
                ),
            ],
        ),
        NetworkElement(
            name="PE-CORDOBA-01",
            system_ip="10.10.2.1",
            ne_type="7750 SR-12",
            version="TiMOS-C-24.7.R2",
            site="Córdoba",
            group="METRO-CBA",
            chassis_mac="00:03:fa:22:02:01",
            protocols=["ospf", "isis", "ldp", "rsvp", "mpls", "bgp", "sr"],
            cards=[
                Card("A", "cpm-2", "cpm-2", "up", "up"),
                _line_card(
                    "1",
                    "imm48-sfp+",
                    _ports(
                        [
                            ("1/1/1", "network", "10G", "up", "up"),
                            ("1/1/2", "network", "10G", "up", "up"),
                            ("1/1/10", "access", "10G", "up", "up"),
                        ]
                    ),
                ),
            ],
        ),
        NetworkElement(
            name="PE-ROSARIO-01",
            system_ip="10.10.3.1",
            ne_type="7705 SAR-8",
            version="TiMOS-B-24.10.R1",
            site="Rosario",
            group="ACCESS",
            chassis_mac="00:03:fa:33:03:01",
            protocols=["ospf", "ldp", "mpls", "bgp"],
            cards=[
                Card("A", "csm", "csm", "up", "up"),
                _line_card(
                    "1",
                    "sar-8-eth",
                    _ports(
                        [
                            ("1/1/1", "network", "1G", "up", "up"),
                            ("1/1/2", "access", "1G", "up", "up"),
                            ("1/1/3", "access", "1G", "up", "up"),
                        ]
                    ),
                ),
            ],
        ),
        NetworkElement(
            name="PE-MENDOZA-01",
            system_ip="10.10.4.1",
            ne_type="7750 SR-12",
            version="TiMOS-C-24.10.R1",
            site="Mendoza",
            group="METRO-Cuyo",
            chassis_mac="00:03:fa:44:04:01",
            protocols=["isis", "ldp", "rsvp", "mpls", "bgp", "sr"],
            cards=[
                Card("A", "cpm-2", "cpm-2", "up", "up"),
                _line_card(
                    "1",
                    "imm48-sfp+",
                    _ports(
                        [
                            ("1/1/1", "network", "10G", "up", "up"),
                            ("1/1/2", "network", "10G", "up", "degraded"),
                            ("1/1/10", "access", "10G", "up", "up"),
                        ]
                    ),
                ),
            ],
        ),
        NetworkElement(
            name="PE-SALTA-01",
            system_ip="10.10.5.1",
            ne_type="7705 SAR-8",
            version="TiMOS-B-24.7.R1",
            site="Salta",
            group="ACCESS",
            chassis_mac="00:03:fa:55:05:01",
            management="managed",
            protocols=["ospf", "ldp", "mpls"],
            cards=[
                Card("A", "csm", "csm", "up", "up"),
                _line_card(
                    "1",
                    "sar-8-eth",
                    _ports(
                        [
                            ("1/1/1", "network", "1G", "up", "up"),
                            ("1/1/2", "access", "1G", "up", "up"),
                        ]
                    ),
                ),
            ],
        ),
    ]
    return {ne.name: ne for ne in nes}


def seed_paths() -> dict[str, MplsPath]:
    paths = [
        MplsPath("path-ba-cba", ["PE-BAIRES-01", "P-CORE-01", "P-CORE-02", "PE-CORDOBA-01"]),
        MplsPath("path-ba-mza", ["PE-BAIRES-01", "P-CORE-01", "PE-MENDOZA-01"]),
        MplsPath("path-ba-ros", ["PE-BAIRES-01", "PE-BAIRES-02", "PE-ROSARIO-01"]),
        MplsPath("path-core", ["P-CORE-01", "P-CORE-02"]),
        MplsPath("path-ba-sal", ["PE-BAIRES-01", "P-CORE-01", "PE-SALTA-01"]),
        MplsPath("loose-any", [], "loose"),
    ]
    return {p.name: p for p in paths}


def seed_lsps() -> dict[str, Lsp]:
    lsps = [
        Lsp(
            "lsp-ba-cba",
            "dynamic",
            "rsvp",
            "PE-BAIRES-01",
            "PE-CORDOBA-01",
            "path-ba-cba",
            ["PE-BAIRES-01", "P-CORE-01", "P-CORE-02", "PE-CORDOBA-01"],
            bandwidth_mbps=1000,
            protection="fast-reroute",
            metric=30,
        ),
        Lsp(
            "lsp-cba-ba",
            "dynamic",
            "rsvp",
            "PE-CORDOBA-01",
            "PE-BAIRES-01",
            "path-ba-cba",
            ["PE-CORDOBA-01", "P-CORE-02", "P-CORE-01", "PE-BAIRES-01"],
            bandwidth_mbps=1000,
            protection="fast-reroute",
            metric=30,
        ),
        Lsp(
            "lsp-ba-mza-sr",
            "sr-te",
            "sr",
            "PE-BAIRES-01",
            "PE-MENDOZA-01",
            "path-ba-mza",
            ["PE-BAIRES-01", "P-CORE-01", "PE-MENDOZA-01"],
            bandwidth_mbps=500,
            protection="ti-lfa",
            metric=20,
        ),
        Lsp(
            "lsp-ba-ros",
            "dynamic",
            "ldp",
            "PE-BAIRES-01",
            "PE-ROSARIO-01",
            "path-ba-ros",
            ["PE-BAIRES-01", "PE-BAIRES-02", "PE-ROSARIO-01"],
            bandwidth_mbps=200,
            metric=15,
        ),
        Lsp(
            "lsp-core-p2p",
            "dynamic",
            "rsvp",
            "P-CORE-01",
            "P-CORE-02",
            "path-core",
            ["P-CORE-01", "P-CORE-02"],
            bandwidth_mbps=10000,
            protection="bypass",
            metric=5,
        ),
        Lsp(
            "lsp-ba-sal",
            "dynamic",
            "rsvp",
            "PE-BAIRES-01",
            "PE-SALTA-01",
            "path-ba-sal",
            ["PE-BAIRES-01", "P-CORE-01", "PE-SALTA-01"],
            admin="up",
            oper="down",
            bandwidth_mbps=100,
            metric=40,
        ),
        Lsp(
            "bypass-core-01",
            "bypass",
            "rsvp",
            "P-CORE-01",
            "P-CORE-02",
            "loose-any",
            ["P-CORE-01", "PE-BAIRES-01", "P-CORE-02"],
            bandwidth_mbps=0,
            protection="manual-bypass",
            metric=50,
        ),
        Lsp(
            "lsp-ba-cba-sec",
            "static",
            "rsvp",
            "PE-BAIRES-01",
            "PE-CORDOBA-01",
            "loose-any",
            ["PE-BAIRES-01", "PE-ROSARIO-01", "PE-CORDOBA-01"],
            admin="down",
            oper="down",
            metric=80,
        ),
    ]
    return {l.name: l for l in lsps}


def seed_interfaces() -> list[MplsInterface]:
    return [
        MplsInterface("PE-BAIRES-01", "to-core-01", "1/1/1", 10, "up", "up", ["srlg-ba"]),
        MplsInterface("PE-BAIRES-01", "to-ba-02", "1/1/2", 10, "up", "up"),
        MplsInterface("PE-BAIRES-02", "to-ba-01", "1/1/1", 10, "up", "up"),
        MplsInterface("P-CORE-01", "to-xrs-02", "1/1/1", 5, "up", "up", ["srlg-core"]),
        MplsInterface("P-CORE-01", "to-ba-01", "1/1/2", 10, "up", "up"),
        MplsInterface("P-CORE-01", "to-mza", "1/1/3", 20, "up", "up"),
        MplsInterface("P-CORE-02", "to-xrs-01", "1/1/1", 5, "up", "up", ["srlg-core"]),
        MplsInterface("P-CORE-02", "to-cba", "1/1/2", 10, "up", "up"),
        MplsInterface("PE-CORDOBA-01", "to-core-02", "1/1/1", 10, "up", "up"),
        MplsInterface("PE-MENDOZA-01", "to-core-01", "1/1/1", 20, "up", "up"),
        MplsInterface("PE-MENDOZA-01", "to-core-backup", "1/1/2", 40, "up", "degraded"),
        MplsInterface("PE-ROSARIO-01", "to-ba", "1/1/1", 15, "up", "up"),
        MplsInterface("PE-SALTA-01", "to-core-01", "1/1/1", 30, "up", "up"),
    ]


def seed_tunnels() -> dict[int, ServiceTunnel]:
    tunnels = [
        ServiceTunnel(101, "sdp-ba-cba", "PE-BAIRES-01", "PE-CORDOBA-01", "tldp", "lsp-ba-cba", far_end="10.10.2.1"),
        ServiceTunnel(102, "sdp-cba-ba", "PE-CORDOBA-01", "PE-BAIRES-01", "tldp", "lsp-cba-ba", far_end="10.10.1.1"),
        ServiceTunnel(201, "sdp-ba-ros", "PE-BAIRES-01", "PE-ROSARIO-01", "tldp", "lsp-ba-ros", far_end="10.10.3.1"),
        ServiceTunnel(202, "sdp-ros-ba", "PE-ROSARIO-01", "PE-BAIRES-01", "tldp", "lsp-ba-ros", far_end="10.10.1.1"),
        ServiceTunnel(301, "sdp-ba-mza", "PE-BAIRES-01", "PE-MENDOZA-01", "sr-isis", "lsp-ba-mza-sr", far_end="10.10.4.1"),
        ServiceTunnel(401, "sdp-ba-sal", "PE-BAIRES-01", "PE-SALTA-01", "tldp", "lsp-ba-sal", "up", "down", "10.10.5.1"),
    ]
    return {t.sdp_id: t for t in tunnels}


def seed_services() -> dict[int, Service]:
    services = [
        Service(
            100,
            "vprn-banco-nacion",
            "vprn",
            "Banco Nación",
            12,
            ["PE-BAIRES-01", "PE-CORDOBA-01", "PE-MENDOZA-01"],
            [101, 102, 301],
            mtu=1500,
            description="L3VPN sucursales",
        ),
        Service(
            200,
            "vpls-metro-ba",
            "vpls",
            "Telecom Mayorista",
            20,
            ["PE-BAIRES-01", "PE-BAIRES-02"],
            mtu=1518,
            description="Metro Ethernet CABA",
        ),
        Service(
            300,
            "epipe-ros-ba",
            "epipe",
            "Puerto Rosario",
            33,
            ["PE-BAIRES-01", "PE-ROSARIO-01"],
            [201, 202],
            description="P2P L2 Rosario–BA",
        ),
        Service(
            400,
            "ies-mgmt",
            "ies",
            "Internal",
            1,
            ["PE-BAIRES-01"],
            description="In-band management",
        ),
        Service(
            500,
            "vprn-salta-backup",
            "vprn",
            "Gobierno Salta",
            44,
            ["PE-BAIRES-01", "PE-SALTA-01"],
            [401],
            admin="up",
            oper="down",
            description="L3VPN Salta — SDP down",
        ),
    ]
    return {s.svc_id: s for s in services}


def seed_alarms() -> list[Alarm]:
    return [
        Alarm(
            "A-1001",
            "critical",
            "tunnelOperDown",
            "sdp:401",
            "PE-BAIRES-01",
            _ts(2.1),
            "SDP 401 oper-down — far-end PE-SALTA-01 unreachable via lsp-ba-sal",
        ),
        Alarm(
            "A-1002",
            "critical",
            "lspOperDown",
            "lsp:lsp-ba-sal",
            "PE-BAIRES-01",
            _ts(2.1),
            "Dynamic RSVP LSP lsp-ba-sal operationally down",
        ),
        Alarm(
            "A-1003",
            "major",
            "portLinkDown",
            "ne:PE-BAIRES-01:port:1/1/11",
            "PE-BAIRES-01",
            _ts(8.0),
            "Access port 1/1/11 link down",
        ),
        Alarm(
            "A-1004",
            "major",
            "serviceSiteDown",
            "svc:500",
            "PE-SALTA-01",
            _ts(2.0),
            "VPRN 500 site down at PE-SALTA-01",
        ),
        Alarm(
            "A-1005",
            "minor",
            "sfpRxPowerLow",
            "ne:PE-MENDOZA-01:port:1/1/2",
            "PE-MENDOZA-01",
            _ts(26.0),
            "Optical Rx power below threshold on 1/1/2",
        ),
        Alarm(
            "A-1006",
            "warning",
            "neCpuHigh",
            "ne:P-CORE-01",
            "P-CORE-01",
            _ts(0.4),
            "CPM CPU 78% (threshold 75%)",
        ),
        Alarm(
            "A-1007",
            "minor",
            "versionMismatch",
            "ne:PE-CORDOBA-01",
            "PE-CORDOBA-01",
            _ts(120.0),
            "NE software TiMOS-C-24.7.R2 behind NFM-P preferred 24.10.R1",
            acked=True,
            acked_by="operator",
        ),
    ]


def seed_stats(nes: dict[str, NetworkElement], lsps: dict[str, Lsp]) -> list[StatSample]:
    now = datetime.now(timezone.utc)
    samples: list[StatSample] = []
    for ne in nes.values():
        for card in ne.cards:
            for port in card.ports:
                if port.oper != "up":
                    continue
                base = 1_000_000 if "100G" in port.speed else 80_000 if "10G" in port.speed else 8_000
                fdn = f"ne:{ne.name}:port:{port.name}"
                samples.append(StatSample(fdn, "ifInOctets", base * 940, "bytes", now))
                samples.append(StatSample(fdn, "ifOutOctets", base * 710, "bytes", now))
                samples.append(StatSample(fdn, "utilizationIn", 34.2 if "100G" in port.speed else 41.0, "%", now))
                samples.append(StatSample(fdn, "utilizationOut", 22.8 if "100G" in port.speed else 29.5, "%", now))
    for lsp in lsps.values():
        fdn = f"lsp:{lsp.name}"
        samples.append(StatSample(fdn, "lspOctets", 12_400_000 if lsp.oper == "up" else 0, "bytes", now))
        samples.append(StatSample(fdn, "lspPackets", 98_100 if lsp.oper == "up" else 0, "pkts", now))
        samples.append(StatSample(fdn, "bandwidthReserved", float(lsp.bandwidth_mbps), "Mbps", now))
    return samples


class Store:
    """Mutable in-memory NFM-P database for the demo lab."""

    def __init__(self) -> None:
        self.users = seed_users()
        self.nes = seed_nes()
        self.paths = seed_paths()
        self.lsps = seed_lsps()
        self.mpls_ifs = seed_interfaces()
        self.tunnels = seed_tunnels()
        self.services = seed_services()
        self.alarms = seed_alarms()
        self.stats = seed_stats(self.nes, self.lsps)
        self.tasks: list = []
        self.task_seq = 1

    def visible_nes(self, user: User) -> dict[str, NetworkElement]:
        from nsp_grok.auth import in_span

        return {
            name: ne
            for name, ne in self.nes.items()
            if in_span(user, ne.group, ne.name)
        }

- old_string: 

### Turn 41 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\models.py has been created successfully.

### Turn 42 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\auth.py has been created successfully.

### Turn 43 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\lab.py has been created successfully.

### Turn 44 (Assistant)
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\tree.py
- new_string: """Virtual filesystem over the NFM-P navigation tree.

Maps Equipment / Routing / MPLS / Services / Alarms / Stats views to paths
so the operator can `cd` / `ls` / `show` like a shell.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nsp_grok.auth import in_span
from nsp_grok.lab import Store
from nsp_grok.models import User


@dataclass
class Node:
    name: str
    kind: str
    label: str = ""
    payload: Any = None
    children: dict[str, Node] = field(default_factory=dict)

    def child(self, name: str) -> Node | None:
        return self.children.get(name)


def _folder(name: str, label: str = "", **kids: Node) -> Node:
    node = Node(name, "folder", label)
    node.children = kids
    return node


def _leaf(name: str, kind: str, payload: Any, label: str = "") -> Node:
    return Node(name, kind, label, payload)


def build_tree(store: Store, user: User) -> Node:
    nes = store.visible_nes(user)

    groups: dict[str, dict[str, Node]] = {}
    for ne in nes.values():
        groups.setdefault(ne.group, {})[ne.name] = _ne_node(ne, store)

    group_nodes = {
        gname: _folder(gname, f"equipment-group {gname}", **children)
        for gname, children in sorted(groups.items())
    }

    routing_kids = {name: _routing_node(ne, store) for name, ne in nes.items()}

    lsp_kids = {
        lsp.name: _leaf(lsp.name, "lsp", lsp, f"{lsp.signaling} {lsp.from_ne}->{lsp.to_ne}")
        for lsp in store.lsps.values()
        if lsp.from_ne in nes or lsp.to_ne in nes
    }
    path_kids = {
        p.name: _leaf(p.name, "path", p, f"{len(p.hops)} hops")
        for p in store.paths.values()
    }
    tun_kids = {
        str(t.sdp_id): _leaf(str(t.sdp_id), "sdp", t, t.name)
        for t in store.tunnels.values()
        if t.from_ne in nes or t.to_ne in nes
    }
    if_kids = {}
    for iface in store.mpls_ifs:
        if iface.ne not in nes:
            continue
        key = f"{iface.ne}:{iface.name}"
        if_kids[key] = _leaf(key, "mpls-if", iface, iface.interface)

    svc_kids = {
        str(s.svc_id): _leaf(str(s.svc_id), "service", s, s.name)
        for s in store.services.values()
        if any(site in nes for site in s.sites)
    }

    alarm_kids = {
        a.id: _leaf(a.id, "alarm", a, a.probable_cause)
        for a in store.alarms
        if a.ne in nes or not a.ne
    }

    admin_kids: dict[str, Node] = {}
    if user.role == "administrator":
        admin_kids = {
            "users": _folder(
                "users",
                "local users",
                **{
                    u.username: _leaf(u.username, "user", u, u.role)
                    for u in store.users.values()
                },
            )
        }

    root = _folder(
        "/",
        "NFM-P managed domain",
        equipment=_folder("equipment", "Equipment view", **group_nodes),
        routing=_folder("routing", "Routing view", **routing_kids),
        mpls=_folder(
            "mpls",
            "MPLS",
            lsps=_folder("lsps", "LSPs", **lsp_kids),
            paths=_folder("paths", "MPLS paths", **path_kids),
            interfaces=_folder("interfaces", "MPLS interfaces", **if_kids),
            tunnels=_folder("tunnels", "Service tunnels (SDP)", **tun_kids),
        ),
        services=_folder("services", "Customer services", **svc_kids),
        alarms=_folder("alarms", "Faults", **alarm_kids),
        stats=_folder("stats", "Statistics"),
        admin=_folder("admin", "Users and Security", **admin_kids),
    )
    return root


def _ne_node(ne, store: Store) -> Node:
    cards = {}
    for card in ne.cards:
        port_kids = {
            p.name.replace("/", "-"): _leaf(p.name.replace("/", "-"), "port", p, p.mode)
            for p in card.ports
        }
        cards[card.slot] = Node(
            card.slot,
            "card",
            card.card_type,
            card,
            port_kids,
        )
    return Node(
        ne.name,
        "ne",
        f"{ne.ne_type} {ne.system_ip}",
        ne,
        {
            "cards": _folder("cards", "shelf / cards", **cards),
            "routing": _routing_node(ne, store),
        },
    )


def _routing_node(ne, store: Store) -> Node:
    ifs = {
        iface.name: _leaf(iface.name, "mpls-if", iface, iface.interface)
        for iface in store.mpls_ifs
        if iface.ne == ne.name
    }
    lsps = {
        lsp.name: _leaf(lsp.name, "lsp", lsp, lsp.signaling)
        for lsp in store.lsps.values()
        if lsp.from_ne == ne.name
    }
    proto_kids = {p: _folder(p, p.upper()) for p in ne.protocols}
    if "mpls" in proto_kids:
        proto_kids["mpls"].children = {
            "interfaces": _folder("interfaces", "", **ifs),
            "lsps": _folder("lsps", "", **lsps),
        }
    return Node(
        ne.name if False else "Base",
        "vrtr",
        "Base routing instance",
        ne,
        proto_kids,
    )


def resolve(root: Node, cwd: list[str], spec: str) -> tuple[list[str], Node] | None:
    if spec in ("", "."):
        node = _walk(root, cwd)
        return (cwd, node) if node else None
    if spec == "/":
        return [], root
    parts = spec.replace("\\", "/").split("/")
    if spec.startswith("/"):
        acc: list[str] = []
        parts = [p for p in parts if p]
    else:
        acc = list(cwd)
        parts = [p for p in parts if p]
    node = _walk(root, acc)
    if node is None:
        return None
    for part in parts:
        if part == ".":
            continue
        if part == "..":
            if acc:
                acc.pop()
                node = _walk(root, acc)
            continue
        if node is None or part not in node.children:
            return None
        acc.append(part)
        node = node.children[part]
    return acc, node


def _walk(root: Node, path: list[str]) -> Node | None:
    node = root
    for part in path:
        node = node.child(part)
        if node is None:
            return None
    return node


def pwd(path: list[str]) -> str:
    return "/" + "/".join(path) if path else "/"

- old_string: 
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\render.py
- new_string: """Rich renderers for list forms, property forms, and the status line."""

from __future__ import annotations

from typing import Any, Iterable

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree as RichTree

from nsp_grok.models import (
    SEVERITY_ORDER,
    Alarm,
    Card,
    Lsp,
    MplsInterface,
    MplsPath,
    NetworkElement,
    Port,
    Service,
    ServiceTunnel,
    StatSample,
    User,
)
from nsp_grok.tree import Node, pwd

SEV_STYLE = {
    "critical": "bold red",
    "major": "bold dark_orange",
    "minor": "yellow",
    "warning": "cyan",
    "cleared": "green",
    "up": "green",
    "down": "red",
    "degraded": "yellow",
    "managed": "green",
    "suspended": "magenta",
    "unmanaged": "grey50",
}


def state(value: str) -> Text:
    return Text(str(value), style=SEV_STYLE.get(str(value), ""))


def banner() -> RenderableType:
    body = Text.assemble(
        ("NSP-Grok", "bold cyan"),
        ("  ", ""),
        ("24.11", "bold white"),
        ("\n", ""),
        ("Network Functions Manager — Packet", "dim"),
        ("\n", ""),
        ("Classic management shell  ·  IP/MPLS", "dim"),
    )
    return Panel(body, border_style="cyan", padding=(0, 2))


def kv_table(rows: Iterable[tuple[str, Any]], title: str = "") -> Table:
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0), title=title)
    table.add_column("k", style="dim", min_width=18)
    table.add_column("v")
    for key, value in rows:
        if isinstance(value, Text):
            table.add_row(key, value)
        else:
            table.add_row(key, str(value) if value is not None else "")
    return table


def ls_table(node: Node, path: list[str]) -> RenderableType:
    if not node.children:
        return Text(f"(empty)  {pwd(path)}", style="dim")
    table = Table(
        title=f"{pwd(path)}  [{node.kind}]",
        expand=False,
        border_style="grey37",
    )
    table.add_column("name", style="bold")
    table.add_column("kind", style="cyan")
    table.add_column("label")
    table.add_column("state")
    for name, child in node.children.items():
        st = _object_state(child.payload)
        suffix = "/" if child.children else ""
        table.add_row(name + suffix, child.kind, child.label, state(st) if st else Text(""))
    return table


def tree_view(node: Node, path: list[str], depth: int = 2) -> RenderableType:
    rich = RichTree(f"[bold cyan]{pwd(path)}[/]  [dim]{node.kind}[/]")
    _walk_tree(rich, node, depth)
    return rich


def _walk_tree(rich: RichTree, node: Node, depth: int) -> None:
    if depth <= 0:
        return
    for name, child in node.children.items():
        mark = "/" if child.children else ""
        st = _object_state(child.payload)
        extra = f"  [dim]{child.label}[/]" if child.label else ""
        if st:
            extra += f"  [{SEV_STYLE.get(st, 'white')}]{st}[/]"
        branch = rich.add(f"{name}{mark}{extra}")
        _walk_tree(branch, child, depth - 1)


def show_object(payload: Any, kind: str) -> RenderableType:
    if isinstance(payload, NetworkElement):
        return show_ne(payload)
    if isinstance(payload, Card):
        return show_card(payload)
    if isinstance(payload, Port):
        return show_port(payload)
    if isinstance(payload, Lsp):
        return show_lsp(payload)
    if isinstance(payload, MplsPath):
        return show_path(payload)
    if isinstance(payload, MplsInterface):
        return show_mpls_if(payload)
    if isinstance(payload, ServiceTunnel):
        return show_sdp(payload)
    if isinstance(payload, Service):
        return show_service(payload)
    if isinstance(payload, Alarm):
        return show_alarm(payload)
    if isinstance(payload, User):
        return show_user(payload)
    return Text(repr(payload))


def show_ne(ne: NetworkElement) -> RenderableType:
    ports = sum(len(c.ports) for c in ne.cards)
    general = kv_table(
        [
            ("Displayed Name", ne.name),
            ("System IP", ne.system_ip),
            ("Chassis Type", ne.ne_type),
            ("Software Version", ne.version),
            ("Site", ne.site),
            ("Equipment Group", ne.group),
            ("Chassis MAC", ne.chassis_mac),
            ("Administrative State", state(ne.admin)),
            ("Operational State", state(ne.oper)),
            ("Management State", state(ne.management)),
            ("Protocols", ", ".join(p.upper() for p in ne.protocols)),
            ("Cards / Ports", f"{len(ne.cards)} / {ports}"),
        ]
    )
    cards = Table(title="Cards", border_style="grey37")
    cards.add_column("slot")
    cards.add_column("type")
    cards.add_column("admin")
    cards.add_column("oper")
    cards.add_column("ports")
    for c in ne.cards:
        cards.add_row(c.slot, c.card_type, state(c.admin), state(c.oper), str(len(c.ports)))
    return Panel(Group(general, cards), title=f"NE properties  {ne.name}", border_style="cyan")


def show_card(card: Card) -> RenderableType:
    t = Table(title=f"Card slot {card.slot}", border_style="grey37")
    t.add_column("port")
    t.add_column("mode")
    t.add_column("encap")
    t.add_column("speed")
    t.add_column("admin")
    t.add_column("oper")
    for p in card.ports:
        t.add_row(p.name, p.mode, p.encap, p.speed, state(p.admin), state(p.oper))
    head = kv_table(
        [
            ("Slot", card.slot),
            ("Card Type", card.card_type),
            ("Equipped", card.equipped),
            ("Administrative State", state(card.admin)),
            ("Operational State", state(card.oper)),
        ]
    )
    return Group(head, t)


def show_port(port: Port) -> RenderableType:
    return Panel(
        kv_table(
            [
                ("Port", port.name),
                ("Mode", port.mode),
                ("Encap", port.encap),
                ("Speed", port.speed),
                ("LAG", port.lag or "—"),
                ("Description", port.description),
                ("Administrative State", state(port.admin)),
                ("Operational State", state(port.oper)),
            ]
        ),
        title="Port properties",
        border_style="cyan",
    )


def show_lsp(lsp: Lsp) -> RenderableType:
    hops = " → ".join(lsp.hops) if lsp.hops else "(loose)"
    return Panel(
        kv_table(
            [
                ("Name", lsp.name),
                ("Type", lsp.lsp_type),
                ("Signaling", lsp.signaling.upper()),
                ("From", lsp.from_ne),
                ("To", lsp.to_ne),
                ("Path", lsp.path),
                ("Hops", hops),
                ("Metric", lsp.metric),
                ("Bandwidth", f"{lsp.bandwidth_mbps} Mbps"),
                ("Setup / Hold", f"{lsp.setup_priority} / {lsp.hold_priority}"),
                ("Protection", lsp.protection),
                ("Administrative State", state(lsp.admin)),
                ("Operational State", state(lsp.oper)),
            ]
        ),
        title=f"LSP  {lsp.name}",
        border_style="cyan",
    )


def show_path(path: MplsPath) -> RenderableType:
    hops = " → ".join(path.hops) if path.hops else "(none)"
    return kv_table(
        [("Name", path.name), ("Hop type", path.hop_type), ("Hops", hops)],
        title="MPLS Path",
    )


def show_mpls_if(iface: MplsInterface) -> RenderableType:
    return kv_table(
        [
            ("NE", iface.ne),
            ("MPLS Interface", iface.name),
            ("Bound L3 Interface", iface.interface),
            ("TE Metric", iface.te_metric),
            ("SRLGs", ", ".join(iface.srlgs) or "—"),
            ("Administrative State", state(iface.admin)),
            ("Operational State", state(iface.oper)),
        ]
    )


def show_sdp(sdp: ServiceTunnel) -> RenderableType:
    return kv_table(
        [
            ("SDP ID", sdp.sdp_id),
            ("Name", sdp.name),
            ("From", sdp.from_ne),
            ("To", sdp.to_ne),
            ("Far End", sdp.far_end),
            ("Signaling", sdp.signaling),
            ("LSP", sdp.lsp),
            ("Administrative State", state(sdp.admin)),
            ("Operational State", state(sdp.oper)),
        ],
        title="Service tunnel (SDP)",
    )


def show_service(svc: Service) -> RenderableType:
    return Panel(
        kv_table(
            [
                ("Service ID", svc.svc_id),
                ("Name", svc.name),
                ("Type", svc.svc_type.upper()),
                ("Customer", f"{svc.customer} ({svc.customer_id})"),
                ("Sites", ", ".join(svc.sites)),
                ("SDP bindings", ", ".join(str(i) for i in svc.sdp_ids) or "—"),
                ("MTU", svc.mtu),
                ("Description", svc.description),
                ("Administrative State", state(svc.admin)),
                ("Operational State", state(svc.oper)),
            ]
        ),
        title=f"Service  {svc.svc_id}",
        border_style="cyan",
    )


def show_alarm(alarm: Alarm) -> RenderableType:
    return Panel(
        kv_table(
            [
                ("Alarm ID", alarm.id),
                ("Severity", state(alarm.severity)),
                ("Probable Cause", alarm.probable_cause),
                ("Object", alarm.object_fdn),
                ("NE", alarm.ne),
                ("Raised", alarm.raised.strftime("%Y-%m-%d %H:%M:%SZ")),
                ("Acknowledged", "yes" if alarm.acked else "no"),
                ("Acked by", alarm.acked_by or "—"),
                ("Cleared", "yes" if alarm.cleared else "no"),
                ("Additional Text", alarm.additional_text),
            ]
        ),
        title="Alarm",
        border_style=SEV_STYLE.get(alarm.severity, "cyan"),
    )


def show_user(user: User) -> RenderableType:
    return kv_table(
        [
            ("Username", user.username),
            ("Display Name", user.display_name),
            ("User Group", user.group),
            ("Role", user.role),
            ("Account State", user.state),
            ("Access", user.access),
            ("Span of Control", ", ".join(user.span) or "ALL"),
            ("E-mail", user.email),
            ("Last Login", user.last_login.strftime("%Y-%m-%d %H:%M:%SZ") if user.last_login else "—"),
        ],
        title="User account",
    )


def ne_table(nes: Iterable[NetworkElement]) -> Table:
    t = Table(title="Network Elements", border_style="grey37")
    t.add_column("name", style="bold")
    t.add_column("system IP")
    t.add_column("type")
    t.add_column("version")
    t.add_column("group")
    t.add_column("site")
    t.add_column("mgmt")
    t.add_column("oper")
    for ne in nes:
        t.add_row(
            ne.name,
            ne.system_ip,
            ne.ne_type,
            ne.version,
            ne.group,
            ne.site,
            state(ne.management),
            state(ne.oper),
        )
    return t


def lsp_table(lsps: Iterable[Lsp]) -> Table:
    t = Table(title="MPLS LSPs", border_style="grey37")
    t.add_column("name", style="bold")
    t.add_column("type")
    t.add_column("sig")
    t.add_column("from")
    t.add_column("to")
    t.add_column("path")
    t.add_column("bw")
    t.add_column("prot")
    t.add_column("admin")
    t.add_column("oper")
    for lsp in lsps:
        t.add_row(
            lsp.name,
            lsp.lsp_type,
            lsp.signaling,
            lsp.from_ne,
            lsp.to_ne,
            lsp.path,
            str(lsp.bandwidth_mbps),
            lsp.protection,
            state(lsp.admin),
            state(lsp.oper),
        )
    return t


def service_table(svcs: Iterable[Service]) -> Table:
    t = Table(title="Services", border_style="grey37")
    t.add_column("id", justify="right")
    t.add_column("name", style="bold")
    t.add_column("type")
    t.add_column("customer")
    t.add_column("sites")
    t.add_column("admin")
    t.add_column("oper")
    for s in svcs:
        t.add_row(
            str(s.svc_id),
            s.name,
            s.svc_type,
            s.customer,
            ",".join(s.sites),
            state(s.admin),
            state(s.oper),
        )
    return t


def alarm_table(alarms: Iterable[Alarm]) -> Table:
    t = Table(title="Alarms", border_style="grey37")
    t.add_column("id")
    t.add_column("sev")
    t.add_column("cause")
    t.add_column("object")
    t.add_column("NE")
    t.add_column("acked")
    t.add_column("raised")
    ordered = sorted(
        (a for a in alarms if not a.cleared),
        key=lambda a: (-SEVERITY_ORDER.get(a.severity, 0), a.raised),
    )
    for a in ordered:
        t.add_row(
            a.id,
            state(a.severity),
            a.probable_cause,
            a.object_fdn,
            a.ne,
            "yes" if a.acked else "no",
            a.raised.strftime("%H:%M:%SZ"),
        )
    if not ordered:
        t.add_row("—", "cleared", "no outstanding alarms", "", "", "", "")
    return t


def stats_table(samples: Iterable[StatSample], fdn: str) -> Table:
    t = Table(title=f"Performance statistics  {fdn}", border_style="grey37")
    t.add_column("counter")
    t.add_column("value", justify="right")
    t.add_column("unit")
    t.add_column("collected")
    rows = [s for s in samples if s.object_fdn == fdn]
    for s in rows:
        val = f"{s.value:,.0f}" if s.value >= 100 else f"{s.value:.1f}"
        t.add_row(s.counter, val, s.unit, s.collected.strftime("%H:%M:%SZ"))
    if not rows:
        t.add_row("(none)", "", "", "no MIB policy match")
    return t


def topology_ascii() -> RenderableType:
    art = Text.from_markup(
        """
[bold cyan]Physical / IGP topology[/]  (lab ARGENTINA)

                    [green]PE-SALTA-01[/]
                         |
                    [green]P-CORE-01[/]────────[green]P-CORE-02[/]
                    /    |    \\              \\
         [green]PE-BAIRES-01[/]  [yellow]PE-MENDOZA-01[/]     [green]PE-CORDOBA-01[/]
                |
         [green]PE-BAIRES-02[/]
                |
         [green]PE-ROSARIO-01[/]

  [green]green[/] oper-up    [yellow]yellow[/] degraded    [red]red[/] oper-down
  RSVP-TE: lsp-ba-cba, lsp-core-p2p, lsp-ba-sal [red](down)[/]
  SR-TE:   lsp-ba-mza-sr
  LDP:     lsp-ba-ros
"""
    )
    return Panel(art, border_style="cyan", title="Application → Topology")


def help_text() -> RenderableType:
    nav = Table(title="Navigation (NFM-P tree as a filesystem)", border_style="grey37")
    nav.add_column("command", style="bold cyan")
    nav.add_column("what it does")
    for cmd, desc in [
        ("ls [path]", "list objects (list form)"),
        ("cd <path>", "enter an object / folder"),
        ("pwd", "print current path"),
        ("tree [n]", "hierarchy, depth n (default 2)"),
        ("show [obj]", "property form of object or cwd"),
        ("find <text>", "search names, IPs, FDNs"),
        ("cat <obj>", "alias of show"),
    ]:
        nav.add_row(cmd, desc)

    slash = Table(title="Slash commands  (type /  ·  Tab completes)", border_style="grey37")
    slash.add_column("command", style="bold cyan")
    slash.add_column("what it does")
    for cmd, desc in [
        ("/help", "this help"),
        ("/status", "session, NEs, LSPs, alarms"),
        ("/whoami", "user, role, span of control"),
        ("/ne [name]", "list NEs or show one"),
        ("/mpls [lsps|paths|tunnels|interfaces]", "MPLS inventory"),
        ("/services [id]", "customer services"),
        ("/alarms [sev]", "faults; /alarms ack A-1001"),
        ("/stats <fdn>", "performance statistics"),
        ("/topology", "ASCII topology map"),
        ("/tasks", "task manager"),
        ("/users", "local users (admin)"),
        ("/resync [ne]", "resynchronize NE(s)"),
        ("/passwd", "change password"),
        ("/clear", "clear screen"),
        ("/quit", "end session"),
    ]:
        slash.add_row(cmd, desc)

    mpls = Table(title="MPLS write operations (operator / admin)", border_style="grey37")
    mpls.add_column("command", style="bold cyan")
    mpls.add_column("what it does")
    for cmd, desc in [
        ("mpls lsp list", "list dynamic / static / SR-TE / bypass LSPs"),
        ("mpls lsp show <name>", "LSP property form + hops"),
        ("mpls lsp create name=.. from=.. to=.. type=dynamic sig=rsvp", "create LSP"),
        ("mpls lsp shutdown <name>", "administrative shutdown"),
        ("mpls lsp turnup <name>", "administrative turn-up"),
        ("alarm ack <id>", "acknowledge fault"),
        ("alarm clear <id>", "clear fault"),
    ]:
        mpls.add_row(cmd, desc)

    return Group(nav, slash, mpls)


def _object_state(payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, Alarm):
        return payload.severity if not payload.cleared else "cleared"
    for attr in ("oper", "management", "state"):
        if hasattr(payload, attr):
            return str(getattr(payload, attr))
    return ""

- old_string: 

### Turn 45 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\tree.py has been created successfully.

### Turn 46 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\render.py has been created successfully.

### Turn 47 (Assistant)
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\tree.py
- old_string:     routing_kids = {name: _routing_node(ne, store) for name, ne in nes.items()}
- new_string:     routing_kids = {name: _routing_node(ne, store, name) for name, ne in nes.items()}
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\tree.py
- old_string:             "routing": _routing_node(ne, store),
- new_string:             "routing": _routing_node(ne, store, "Base"),
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\tree.py
- old_string: def _routing_node(ne, store: Store) -> Node:
- new_string: def _routing_node(ne, store: Store, name: str = "Base") -> Node:
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\tree.py
- old_string:     return Node(
        ne.name if False else "Base",
        "vrtr",
        "Base routing instance",
        ne,
        proto_kids,
    )
- new_string:     return Node(
        name,
        "vrtr",
        "Base routing instance",
        ne,
        proto_kids,
    )
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\tree.py
- old_string: from nsp_grok.auth import in_span
from nsp_grok.lab import Store
- new_string: from nsp_grok.lab import Store

### Turn 48 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\tree.py has been updated successfully.

### Turn 49 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\tree.py has been updated successfully.

### Turn 50 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\tree.py has been updated successfully.

### Turn 51 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\tree.py has been updated successfully.

### Turn 52 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\tree.py has been updated successfully.

### Turn 53 (Assistant)
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\commands.py
- new_string: """Command dispatch for the NSP-Grok shell."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from rich.console import Group, RenderableType
from rich.text import Text

from nsp_grok import RELEASE
from nsp_grok.auth import can, change_password
from nsp_grok.lab import Store
from nsp_grok.models import Alarm, Lsp, Task, User
from nsp_grok import render
from nsp_grok.tree import Node, build_tree, pwd, resolve


SLASH = {
    "help": "this help",
    "status": "session summary",
    "whoami": "user, role, span of control",
    "ne": "network elements",
    "mpls": "MPLS objects",
    "services": "customer services",
    "alarms": "faults",
    "stats": "performance statistics",
    "topology": "ASCII topology",
    "tasks": "task manager",
    "users": "local users (admin)",
    "resync": "resynchronize NE(s)",
    "passwd": "change password",
    "clear": "clear screen",
    "quit": "end session",
    "exit": "end session",
}


@dataclass
class Ctx:
    store: Store
    user: User
    cwd: list[str]
    root: Node
    session_id: str
    started: datetime
    theme: str = "dark"
    last_task: int = 0

    def node(self) -> Node:
        found = resolve(self.root, self.cwd, ".")
        assert found is not None
        return found[1]

    def rebuild(self) -> None:
        self.root = build_tree(self.store, self.user)
        found = resolve(self.root, [], pwd(self.cwd) if self.cwd else "/")
        if found is None:
            self.cwd = []
        else:
            self.cwd = found[0]


@dataclass
class Outcome:
    renderable: RenderableType | None = None
    clear: bool = False
    quit: bool = False
    error: str = ""


def dispatch(ctx: Ctx, line: str) -> Outcome:
    raw = line.strip()
    if not raw:
        return Outcome()
    if raw.startswith("/"):
        return _slash(ctx, raw[1:])
    try:
        parts = shlex.split(raw)
    except ValueError as exc:
        return Outcome(error=str(exc))
    verb = parts[0].lower()
    args = parts[1:]
    handlers = {
        "ls": _ls,
        "cd": _cd,
        "pwd": _pwd,
        "tree": _tree,
        "show": _show,
        "cat": _show,
        "find": _find,
        "help": lambda c, a: Outcome(renderable=render.help_text()),
        "mpls": _mpls,
        "alarm": _alarm,
        "alarms": _alarm,
        "ne": _ne,
        "service": _service,
        "services": _service,
        "stats": _stats,
        "resync": _resync,
        "topology": lambda c, a: Outcome(renderable=render.topology_ascii()),
        "clear": lambda c, a: Outcome(clear=True),
        "quit": lambda c, a: Outcome(quit=True),
        "exit": lambda c, a: Outcome(quit=True),
        "whoami": _whoami,
        "status": _status,
        "passwd": _passwd,
        "users": _users,
        "tasks": _tasks,
    }
    fn = handlers.get(verb)
    if fn is None:
        return Outcome(error=f"unknown command: {verb}  (try /help)")
    return fn(ctx, args)


def _slash(ctx: Ctx, rest: str) -> Outcome:
    rest = rest.strip()
    if not rest:
        lines = Text()
        for name, desc in SLASH.items():
            if name == "exit":
                continue
            lines.append(f"/{name:<12}", style="bold cyan")
            lines.append(f" {desc}\n", style="dim")
        return Outcome(renderable=lines)
    parts = rest.split()
    name = parts[0].lower()
    args = parts[1:]
    aliases = {"h": "help", "q": "quit", "exit": "quit", "info": "status"}
    name = aliases.get(name, name)
    mapping = {
        "help": lambda: Outcome(renderable=render.help_text()),
        "status": lambda: _status(ctx, args),
        "whoami": lambda: _whoami(ctx, args),
        "ne": lambda: _ne(ctx, args),
        "mpls": lambda: _mpls(ctx, args),
        "services": lambda: _service(ctx, args),
        "alarms": lambda: _alarm(ctx, args),
        "stats": lambda: _stats(ctx, args),
        "topology": lambda: Outcome(renderable=render.topology_ascii()),
        "tasks": lambda: _tasks(ctx, args),
        "users": lambda: _users(ctx, args),
        "resync": lambda: _resync(ctx, args),
        "passwd": lambda: _passwd(ctx, args),
        "clear": lambda: Outcome(clear=True),
        "quit": lambda: Outcome(quit=True),
    }
    fn = mapping.get(name)
    if fn is None:
        return Outcome(error=f"unknown command: /{name}  (try /help)")
    return fn()


def _ls(ctx: Ctx, args: list[str]) -> Outcome:
    spec = args[0] if args else "."
    found = resolve(ctx.root, ctx.cwd, spec)
    if found is None:
        return Outcome(error=f"no such object: {spec}")
    path, node = found
    return Outcome(renderable=render.ls_table(node, path))


def _cd(ctx: Ctx, args: list[str]) -> Outcome:
    spec = args[0] if args else "/"
    found = resolve(ctx.root, ctx.cwd, spec)
    if found is None:
        return Outcome(error=f"no such object: {spec}")
    ctx.cwd = found[0]
    return Outcome()


def _pwd(ctx: Ctx, args: list[str]) -> Outcome:
    return Outcome(renderable=Text(pwd(ctx.cwd), style="cyan"))


def _tree(ctx: Ctx, args: list[str]) -> Outcome:
    depth = 2
    spec = "."
    for a in args:
        if a.isdigit():
            depth = max(1, min(int(a), 6))
        else:
            spec = a
    found = resolve(ctx.root, ctx.cwd, spec)
    if found is None:
        return Outcome(error=f"no such object: {spec}")
    path, node = found
    return Outcome(renderable=render.tree_view(node, path, depth))


def _show(ctx: Ctx, args: list[str]) -> Outcome:
    spec = args[0] if args else "."
    found = resolve(ctx.root, ctx.cwd, spec)
    if found is None:
        obj = _lookup_anywhere(ctx, spec)
        if obj is None:
            return Outcome(error=f"no such object: {spec}")
        kind, payload = obj
        return Outcome(renderable=render.show_object(payload, kind))
    _path, node = found
    if node.payload is not None:
        return Outcome(renderable=render.show_object(node.payload, node.kind))
    return Outcome(renderable=render.ls_table(node, _path))


def _find(ctx: Ctx, args: list[str]) -> Outcome:
    if not args:
        return Outcome(error="usage: find <text>")
    needle = " ".join(args).lower()
    hits: list[tuple[str, str, str]] = []

    def walk(node: Node, path: list[str]) -> None:
        blob = " ".join(
            [
                node.name,
                node.kind,
                node.label,
                str(getattr(node.payload, "system_ip", "")),
                str(getattr(node.payload, "name", "")),
            ]
        ).lower()
        if needle in blob:
            hits.append((pwd(path), node.kind, node.label))
        for name, child in node.children.items():
            walk(child, path + [name])

    walk(ctx.root, [])
    if not hits:
        return Outcome(renderable=Text("no matches", style="dim"))
    from rich.table import Table

    t = Table(title=f"find  {needle!r}  ({len(hits)})", border_style="grey37")
    t.add_column("path", style="cyan")
    t.add_column("kind")
    t.add_column("label")
    for row in hits[:80]:
        t.add_row(*row)
    if len(hits) > 80:
        t.caption = f"showing 80 of {len(hits)}"
    return Outcome(renderable=t)


def _ne(ctx: Ctx, args: list[str]) -> Outcome:
    visible = ctx.store.visible_nes(ctx.user)
    if not args:
        return Outcome(renderable=render.ne_table(visible.values()))
    name = args[0]
    ne = visible.get(name) or next(
        (n for n in visible.values() if n.system_ip == name), None
    )
    if ne is None:
        return Outcome(error=f"NE not in span of control: {name}")
    return Outcome(renderable=render.show_ne(ne))


def _mpls(ctx: Ctx, args: list[str]) -> Outcome:
    sub = args[0].lower() if args else "lsps"
    rest = args[1:]
    if sub in ("lsps", "lsp"):
        return _mpls_lsp(ctx, rest)
    if sub in ("paths", "path"):
        if rest:
            path = ctx.store.paths.get(rest[0])
            if path is None:
                return Outcome(error=f"unknown path: {rest[0]}")
            return Outcome(renderable=render.show_path(path))
        from rich.table import Table

        t = Table(title="MPLS Paths", border_style="grey37")
        t.add_column("name", style="bold")
        t.add_column("type")
        t.add_column("hops")
        for p in ctx.store.paths.values():
            t.add_row(p.name, p.hop_type, " → ".join(p.hops) or "(loose)")
        return Outcome(renderable=t)
    if sub in ("tunnels", "tunnel", "sdp"):
        from rich.table import Table

        t = Table(title="Service tunnels (SDP)", border_style="grey37")
        t.add_column("id", justify="right")
        t.add_column("name")
        t.add_column("from")
        t.add_column("to")
        t.add_column("sig")
        t.add_column("lsp")
        t.add_column("oper")
        for sdp in ctx.store.tunnels.values():
            t.add_row(
                str(sdp.sdp_id),
                sdp.name,
                sdp.from_ne,
                sdp.to_ne,
                sdp.signaling,
                sdp.lsp,
                render.state(sdp.oper),
            )
        return Outcome(renderable=t)
    if sub in ("interfaces", "interface", "if"):
        from rich.table import Table

        t = Table(title="MPLS interfaces", border_style="grey37")
        t.add_column("NE")
        t.add_column("name")
        t.add_column("bound if")
        t.add_column("TE")
        t.add_column("SRLG")
        t.add_column("oper")
        visible = ctx.store.visible_nes(ctx.user)
        for iface in ctx.store.mpls_ifs:
            if iface.ne not in visible:
                continue
            t.add_row(
                iface.ne,
                iface.name,
                iface.interface,
                str(iface.te_metric),
                ",".join(iface.srlgs) or "—",
                render.state(iface.oper),
            )
        return Outcome(renderable=t)
    return Outcome(error="usage: mpls [lsps|paths|tunnels|interfaces]")


def _mpls_lsp(ctx: Ctx, args: list[str]) -> Outcome:
    if not args or args[0] in ("list", "ls"):
        return Outcome(renderable=render.lsp_table(ctx.store.lsps.values()))
    action = args[0].lower()
    if action == "show" and len(args) >= 2:
        lsp = ctx.store.lsps.get(args[1])
        if lsp is None:
            return Outcome(error=f"unknown LSP: {args[1]}")
        return Outcome(renderable=render.show_lsp(lsp))
    if action == "create":
        return _lsp_create(ctx, args[1:])
    if action in ("shutdown", "shut") and len(args) >= 2:
        return _lsp_admin(ctx, args[1], "down")
    if action in ("turnup", "no-shutdown") and len(args) >= 2:
        return _lsp_admin(ctx, args[1], "up")
    if action == "delete" and len(args) >= 2:
        if not can(ctx.user, "write"):
            return Outcome(error="permission denied (write)")
        name = args[1]
        if name not in ctx.store.lsps:
            return Outcome(error=f"unknown LSP: {name}")
        del ctx.store.lsps[name]
        _task(ctx, f"delete LSP {name}", f"lsp:{name}")
        ctx.rebuild()
        return Outcome(renderable=Text(f"deleted {name}", style="green"))
    # treat first arg as name
    lsp = ctx.store.lsps.get(args[0])
    if lsp:
        return Outcome(renderable=render.show_lsp(lsp))
    return Outcome(
        error="usage: mpls lsp [list|show <n>|create ...|shutdown <n>|turnup <n>|delete <n>]"
    )


def _parse_kv(args: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for a in args:
        if "=" in a:
            k, v = a.split("=", 1)
            out[k.lower()] = v
    return out


def _lsp_create(ctx: Ctx, args: list[str]) -> Outcome:
    if not can(ctx.user, "write"):
        return Outcome(error="permission denied (write)")
    kv = _parse_kv(args)
    name = kv.get("name")
    src = kv.get("from")
    dst = kv.get("to")
    if not name or not src or not dst:
        return Outcome(
            error="usage: mpls lsp create name=X from=NE to=NE [type=dynamic] [sig=rsvp] [path=P]"
        )
    if name in ctx.store.lsps:
        return Outcome(error=f"LSP already exists: {name}")
    visible = ctx.store.visible_nes(ctx.user)
    if src not in visible or dst not in visible:
        return Outcome(error="source/dest NE not in span of control")
    path_name = kv.get("path", "loose-any")
    path = ctx.store.paths.get(path_name)
    hops = path.hops if path else [src, dst]
    lsp = Lsp(
        name=name,
        lsp_type=kv.get("type", "dynamic"),
        signaling=kv.get("sig", "rsvp"),
        from_ne=src,
        to_ne=dst,
        path=path_name,
        hops=hops,
        bandwidth_mbps=int(kv.get("bw", "0")),
        protection=kv.get("prot", "none"),
    )
    ctx.store.lsps[name] = lsp
    _task(ctx, f"create LSP {name}", f"lsp:{name}")
    ctx.rebuild()
    return Outcome(renderable=Group(Text("created", style="green"), render.show_lsp(lsp)))


def _lsp_admin(ctx: Ctx, name: str, admin: str) -> Outcome:
    if not can(ctx.user, "write"):
        return Outcome(error="permission denied (write)")
    lsp = ctx.store.lsps.get(name)
    if lsp is None:
        return Outcome(error=f"unknown LSP: {name}")
    lsp.admin = admin  # type: ignore[assignment]
    lsp.oper = admin  # type: ignore[assignment]
    verb = "shut down" if admin == "down" else "turned up"
    _task(ctx, f"{verb} LSP {name}", f"lsp:{name}")
    return Outcome(renderable=Text(f"{name} {verb}", style="green"))


def _service(ctx: Ctx, args: list[str]) -> Outcome:
    visible = ctx.store.visible_nes(ctx.user)
    svcs = [
        s
        for s in ctx.store.services.values()
        if any(site in visible for site in s.sites)
    ]
    if not args:
        return Outcome(renderable=render.service_table(svcs))
    key = args[0]
    svc = next((s for s in svcs if str(s.svc_id) == key or s.name == key), None)
    if svc is None:
        return Outcome(error=f"unknown service: {key}")
    return Outcome(renderable=render.show_service(svc))


def _alarm(ctx: Ctx, args: list[str]) -> Outcome:
    visible = ctx.store.visible_nes(ctx.user)
    alarms = [a for a in ctx.store.alarms if a.ne in visible or not a.ne]
    if not args:
        return Outcome(renderable=render.alarm_table(alarms))
    action = args[0].lower()
    if action in ("list", "ls"):
        sev = args[1].lower() if len(args) > 1 else ""
        if sev:
            alarms = [a for a in alarms if a.severity == sev]
        return Outcome(renderable=render.alarm_table(alarms))
    if action in ("ack", "acknowledge") and len(args) >= 2:
        if not can(ctx.user, "execute"):
            return Outcome(error="permission denied (execute) — cannot acknowledge")
        return _alarm_mutate(ctx, args[1], ack=True)
    if action == "clear" and len(args) >= 2:
        if not can(ctx.user, "execute"):
            return Outcome(error="permission denied (execute) — cannot clear")
        return _alarm_mutate(ctx, args[1], clear=True)
    if action in ("critical", "major", "minor", "warning"):
        alarms = [a for a in alarms if a.severity == action]
        return Outcome(renderable=render.alarm_table(alarms))
    alarm = next((a for a in alarms if a.id == args[0]), None)
    if alarm:
        return Outcome(renderable=render.show_alarm(alarm))
    return Outcome(error="usage: alarm [list|ack <id>|clear <id>|<id>|<severity>]")


def _alarm_mutate(ctx: Ctx, alarm_id: str, ack: bool = False, clear: bool = False) -> Outcome:
    alarm = next((a for a in ctx.store.alarms if a.id == alarm_id), None)
    if alarm is None:
        return Outcome(error=f"unknown alarm: {alarm_id}")
    if ack:
        alarm.acked = True
        alarm.acked_by = ctx.user.username
        _task(ctx, f"acknowledge {alarm_id}", alarm.object_fdn)
        return Outcome(renderable=Text(f"{alarm_id} acknowledged", style="green"))
    if clear:
        alarm.cleared = True
        alarm.severity = "cleared"
        _task(ctx, f"clear {alarm_id}", alarm.object_fdn)
        ctx.rebuild()
        return Outcome(renderable=Text(f"{alarm_id} cleared", style="green"))
    return Outcome()


def _stats(ctx: Ctx, args: list[str]) -> Outcome:
    if not args:
        return Outcome(
            error="usage: stats <fdn>   e.g. stats ne:PE-BAIRES-01:port:1/1/1  or  stats lsp:lsp-ba-cba"
        )
    fdn = args[0]
    return Outcome(renderable=render.stats_table(ctx.store.stats, fdn))


def _resync(ctx: Ctx, args: list[str]) -> Outcome:
    if not can(ctx.user, "write"):
        return Outcome(error="permission denied (write)")
    visible = ctx.store.visible_nes(ctx.user)
    names = args or list(visible)
    done = []
    for name in names:
        ne = visible.get(name)
        if ne is None:
            return Outcome(error=f"NE not in span: {name}")
        ne.management = "managed"
        _task(ctx, f"resync {name}", f"ne:{name}")
        done.append(name)
    return Outcome(renderable=Text("resynchronized: " + ", ".join(done), style="green"))


def _whoami(ctx: Ctx, args: list[str]) -> Outcome:
    return Outcome(renderable=render.show_user(ctx.user))


def _status(ctx: Ctx, args: list[str]) -> Outcome:
    visible = ctx.store.visible_nes(ctx.user)
    alarms = [a for a in ctx.store.alarms if not a.cleared and a.ne in visible]
    counts: dict[str, int] = {}
    for a in alarms:
        counts[a.severity] = counts.get(a.severity, 0) + 1
    up = sum(1 for n in visible.values() if n.oper == "up")
    lsp_up = sum(1 for l in ctx.store.lsps.values() if l.oper == "up")
    svc_up = sum(1 for s in ctx.store.services.values() if s.oper == "up")
    rows = [
        ("Product", f"NSP-Grok {RELEASE}  NFM-P classic shell"),
        ("Session", ctx.session_id),
        ("User", f"{ctx.user.username}  ({ctx.user.role} / {ctx.user.group})"),
        ("Span of Control", ", ".join(ctx.user.span) or "ALL"),
        ("CWD", pwd(ctx.cwd)),
        ("NEs", f"{up}/{len(visible)} operational"),
        ("LSPs", f"{lsp_up}/{len(ctx.store.lsps)} operational"),
        ("Services", f"{svc_up}/{len(ctx.store.services)} operational"),
        (
            "Alarms",
            "  ".join(f"{k}={v}" for k, v in counts.items()) or "none outstanding",
        ),
        ("Started", ctx.started.strftime("%Y-%m-%d %H:%M:%SZ")),
    ]
    return Outcome(renderable=render.kv_table(rows, title="Session"))


def _passwd(ctx: Ctx, args: list[str]) -> Outcome:
    if len(args) < 2:
        return Outcome(error="usage: passwd <current> <new>     (or /passwd)")
    errors = change_password(ctx.user, args[0], args[1])
    if errors:
        return Outcome(error="; ".join(errors))
    return Outcome(renderable=Text("password updated", style="green"))


def _users(ctx: Ctx, args: list[str]) -> Outcome:
    if ctx.user.role != "administrator":
        return Outcome(error="permission denied (administrator role required)")
    from rich.table import Table

    t = Table(title="Local users", border_style="grey37")
    t.add_column("user")
    t.add_column("group")
    t.add_column("role")
    t.add_column("access")
    t.add_column("span")
    t.add_column("state")
    t.add_column("last login")
    for u in ctx.store.users.values():
        t.add_row(
            u.username,
            u.group,
            u.role,
            u.access,
            ",".join(u.span) or "ALL",
            render.state(u.state),
            u.last_login.strftime("%H:%M:%SZ") if u.last_login else "—",
        )
    return Outcome(renderable=t)


def _tasks(ctx: Ctx, args: list[str]) -> Outcome:
    from rich.table import Table

    t = Table(title="Task Manager", border_style="grey37")
    t.add_column("id", justify="right")
    t.add_column("user")
    t.add_column("operation")
    t.add_column("object")
    t.add_column("state")
    t.add_column("started")
    if not ctx.store.tasks:
        t.add_row("—", "—", "no tasks this session", "", "", "")
        return Outcome(renderable=t)
    for task in ctx.store.tasks[-20:]:
        t.add_row(
            str(task.id),
            task.user,
            task.operation,
            task.object_fdn,
            task.state,
            task.started.strftime("%H:%M:%SZ"),
        )
    return Outcome(renderable=t)


def _task(ctx: Ctx, operation: str, fdn: str) -> None:
    task = Task(
        id=ctx.store.task_seq,
        user=ctx.user.username,
        operation=operation,
        object_fdn=fdn,
        state="success",
        started=datetime.now(timezone.utc),
        finished=datetime.now(timezone.utc),
    )
    ctx.store.task_seq += 1
    ctx.store.tasks.append(task)
    ctx.last_task = task.id


def _lookup_anywhere(ctx: Ctx, spec: str) -> tuple[str, Any] | None:
    if spec in ctx.store.nes:
        ne = ctx.store.visible_nes(ctx.user).get(spec)
        return ("ne", ne) if ne else None
    if spec in ctx.store.lsps:
        return "lsp", ctx.store.lsps[spec]
    if spec in ctx.store.paths:
        return "path", ctx.store.paths[spec]
    if spec.isdigit() and int(spec) in ctx.store.services:
        return "service", ctx.store.services[int(spec)]
    if spec.isdigit() and int(spec) in ctx.store.tunnels:
        return "sdp", ctx.store.tunnels[int(spec)]
    alarm = next((a for a in ctx.store.alarms if a.id == spec), None)
    if alarm:
        return "alarm", alarm
    return None

- old_string: 
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\completer.py
- new_string: """Tab completion for navigation paths and slash commands."""

from __future__ import annotations

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from nsp_grok.commands import SLASH, Ctx
from nsp_grok.tree import resolve

VERBS = [
    "ls",
    "cd",
    "pwd",
    "tree",
    "show",
    "cat",
    "find",
    "help",
    "mpls",
    "alarm",
    "ne",
    "service",
    "stats",
    "resync",
    "topology",
    "clear",
    "quit",
    "whoami",
    "status",
    "passwd",
    "users",
    "tasks",
]


class NspCompleter(Completer):
    def __init__(self, ctx: Ctx) -> None:
        self.ctx = ctx

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        if text.startswith("/"):
            yield from self._slash(text)
            return
        parts = text.split()
        if not parts or (len(parts) == 1 and not text.endswith(" ")):
            prefix = parts[0] if parts else ""
            for v in VERBS:
                if v.startswith(prefix):
                    yield Completion(v, start_position=-len(prefix))
            return
        verb = parts[0]
        current = parts[-1] if not text.endswith(" ") else ""
        if verb in ("cd", "ls", "show", "cat", "tree"):
            yield from self._paths(current)
        elif verb in ("ne", "resync"):
            for name in self.ctx.store.visible_nes(self.ctx.user):
                if name.startswith(current):
                    yield Completion(name, start_position=-len(current))
        elif verb in ("mpls",):
            if len(parts) == 1 or (len(parts) == 2 and not text.endswith(" ")):
                for w in ("lsps", "paths", "tunnels", "interfaces"):
                    if w.startswith(current):
                        yield Completion(w, start_position=-len(current))
            elif len(parts) >= 2 and parts[1] in ("lsp", "lsps", "show"):
                for name in self.ctx.store.lsps:
                    if name.startswith(current):
                        yield Completion(name, start_position=-len(current))
        elif verb in ("alarm", "alarms"):
            if current.startswith("A-") or not current:
                for a in self.ctx.store.alarms:
                    if a.id.startswith(current):
                        yield Completion(a.id, start_position=-len(current))
            for w in ("list", "ack", "clear", "critical", "major", "minor", "warning"):
                if w.startswith(current):
                    yield Completion(w, start_position=-len(current))

    def _slash(self, text: str) -> list[Completion] | None:
        prefix = text[1:]
        word = prefix.split()[0] if prefix else ""
        if " " in prefix:
            return
        for name, desc in SLASH.items():
            if name.startswith(word):
                yield Completion(
                    name,
                    start_position=-len(word),
                    display=f"/{name}",
                    display_meta=desc,
                )

    def _paths(self, current: str):
        if current.startswith("/"):
            parent_spec = "/".join(current.split("/")[:-1]) or "/"
            prefix = current.rsplit("/", 1)[-1]
            found = resolve(self.ctx.root, self.ctx.cwd, parent_spec)
        elif "/" in current:
            parent_spec, prefix = current.rsplit("/", 1)
            found = resolve(self.ctx.root, self.ctx.cwd, parent_spec)
        else:
            prefix = current
            found = resolve(self.ctx.root, self.ctx.cwd, ".")
        if found is None:
            return
        _path, node = found
        for name, child in node.children.items():
            if name.startswith(prefix):
                suffix = "/" if child.children else ""
                yield Completion(name + suffix, start_position=-len(prefix))

- old_string: 
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\app.py
- new_string: """Interactive NSP-Grok shell — login, then a Grok-like REPL."""

from __future__ import annotations

import argparse
import getpass
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML, StyleAndTextTuples
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.text import Text

from nsp_grok import PRODUCT, RELEASE
from nsp_grok.auth import authenticate
from nsp_grok.commands import Ctx, Outcome, dispatch
from nsp_grok.completer import NspCompleter
from nsp_grok.lab import Store
from nsp_grok.models import User
from nsp_grok.render import SEV_STYLE, banner
from nsp_grok.tree import build_tree, pwd

console = Console()

HISTORY_FILE = Path.home() / ".nsp-grok-history"

PROMPT_STYLE = Style.from_dict(
    {
        "prompt": "ansicyan bold",
        "path": "ansibrightblack",
        "user": "ansigreen",
        "bottom-toolbar": "noreverse bg:#0b1f33 #c8d6e5",
        "bt-key": "bold #6ee7ff",
        "bt-bad": "bold #ff6b6b",
        "bt-ok": "#7dcea0",
    }
)


def _toolbar(ctx: Ctx) -> StyleAndTextTuples:
    visible = ctx.store.visible_nes(ctx.user)
    alarms = [a for a in ctx.store.alarms if not a.cleared and a.ne in visible]
    crit = sum(1 for a in alarms if a.severity == "critical")
    major = sum(1 for a in alarms if a.severity == "major")
    alarm_style = "class:bt-bad" if crit else ("class:bt-key" if major else "class:bt-ok")
    alarm_txt = f"{crit} crit · {major} maj"
    return [
        ("class:bt-key", f" {ctx.user.username} "),
        ("class:bottom-toolbar", "│"),
        ("class:bottom-toolbar", f" {ctx.user.role} "),
        ("class:bottom-toolbar", "│"),
        ("class:bottom-toolbar", f" {pwd(ctx.cwd)} "),
        ("class:bottom-toolbar", "│"),
        (alarm_style, f" {alarm_txt} "),
        ("class:bottom-toolbar", "│"),
        ("class:bottom-toolbar", f" {len(visible)} NEs "),
        ("class:bottom-toolbar", "│"),
        ("class:bt-key", f" NSP {RELEASE} "),
    ]


def _prompt(ctx: Ctx) -> HTML:
    return HTML(
        f"<user>{ctx.user.username}</user> <path>{pwd(ctx.cwd)}</path> <prompt>› </prompt>"
    )


def login_interactive(store: Store) -> User | None:
    console.print(banner())
    console.print(
        Text.from_markup(
            "[dim]Local users: [bold]admin[/]  operator  noc  viewer[/]\n"
            "[dim]Default password:[/] [bold]Nokia123![/]\n"
        )
    )
    for _ in range(5):
        try:
            username = console.input("[cyan]user[/] › ").strip()
            if not username:
                continue
            password = getpass.getpass("password › ")
        except (EOFError, KeyboardInterrupt):
            console.print("\nlogin cancelled")
            return None
        user, err = authenticate(store.users, username, password)
        if user:
            return user
        console.print(Text(err, style="bold red"))
    console.print("[red]too many failed login attempts[/]")
    return None


def login_direct(store: Store, username: str, password: str) -> User | None:
    user, err = authenticate(store.users, username, password)
    if user is None:
        console.print(Text(err, style="bold red"))
    return user


def session_intro(ctx: Ctx) -> None:
    visible = ctx.store.visible_nes(ctx.user)
    alarms = [a for a in ctx.store.alarms if not a.cleared and a.ne in visible]
    crit = sum(1 for a in alarms if a.severity == "critical")
    console.print()
    console.print(
        Text.assemble(
            ("session  ", "dim"),
            (ctx.session_id, "bold cyan"),
            ("  ·  ", "dim"),
            (ctx.user.username, "bold"),
            ("  ·  ", "dim"),
            (ctx.user.role, ""),
            ("  ·  span ", "dim"),
            (", ".join(ctx.user.span) or "ALL", "cyan"),
        )
    )
    console.print(
        Text.assemble(
            (f"{len(visible)} NEs managed", ""),
            ("  ·  ", "dim"),
            (f"{len(ctx.store.lsps)} LSPs", ""),
            ("  ·  ", "dim"),
            (f"{len(ctx.store.services)} services", ""),
            ("  ·  ", "dim"),
            (f"{len(alarms)} alarms", SEV_STYLE["critical"] if crit else ""),
        )
    )
    console.print(
        Text.from_markup(
            "[dim]Type [bold cyan]/help[/] or [bold cyan]ls[/] to start.  "
            "Tab completes.  [bold cyan]/[/] opens commands.[/]\n"
        )
    )


def apply_outcome(out: Outcome) -> bool:
    """Return False if the session should end."""
    if out.error:
        console.print(Text(out.error, style="bold red"))
    if out.clear:
        console.clear()
        console.print(banner())
    if out.renderable is not None:
        console.print(out.renderable)
    return not out.quit


def run_repl(ctx: Ctx) -> None:
    HISTORY_FILE.touch(exist_ok=True)
    session: PromptSession = PromptSession(
        history=FileHistory(str(HISTORY_FILE)),
        auto_suggest=AutoSuggestFromHistory(),
        completer=NspCompleter(ctx),
        complete_while_typing=True,
        style=PROMPT_STYLE,
        bottom_toolbar=lambda: _toolbar(ctx),
    )
    while True:
        try:
            line = session.prompt(_prompt(ctx))
        except KeyboardInterrupt:
            console.print("[dim]^C[/]")
            continue
        except EOFError:
            console.print("\nlogout")
            break
        out = dispatch(ctx, line)
        if not apply_outcome(out):
            console.print("[dim]logout[/]")
            break


def run_batch(ctx: Ctx, commands: list[str]) -> int:
    rc = 0
    for line in commands:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        console.print(Text(f"{ctx.user.username} {pwd(ctx.cwd)} › {line}", style="dim"))
        out = dispatch(ctx, line)
        apply_outcome(out)
        if out.error:
            rc = 1
        if out.quit:
            break
    return rc


def build_ctx(store: Store, user: User) -> Ctx:
    return Ctx(
        store=store,
        user=user,
        cwd=[],
        root=build_tree(store, user),
        session_id=secrets.token_hex(4),
        started=datetime.now(timezone.utc),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="nsp-grok",
        description=f"{PRODUCT} {RELEASE} — NFM-P classic management shell",
    )
    p.add_argument("--user", "-u", help="username (skip interactive login)")
    p.add_argument("--password", "-p", help="password (or NSP_GROK_PASSWORD env)")
    p.add_argument(
        "--batch",
        "-c",
        action="append",
        default=[],
        help="run a command non-interactively (repeatable)",
    )
    p.add_argument(
        "--script",
        help="file with one command per line",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    store = Store()
    password = args.password or os.environ.get("NSP_GROK_PASSWORD", "")
    if args.user:
        user = login_direct(store, args.user, password)
        if user is None:
            return 2
    else:
        user = login_interactive(store)
        if user is None:
            return 2

    ctx = build_ctx(store, user)
    batch: list[str] = list(args.batch)
    if args.script:
        batch.extend(Path(args.script).read_text(encoding="utf-8").splitlines())

    if batch or not sys.stdin.isatty():
        if not batch and not sys.stdin.isatty():
            batch = sys.stdin.read().splitlines()
        if not args.user:
            console.print(banner())
        session_intro(ctx)
        return run_batch(ctx, batch)

    console.clear()
    console.print(banner())
    session_intro(ctx)
    run_repl(ctx)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

- old_string: 
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\__main__.py
- new_string: from nsp_grok.app import main

if __name__ == "__main__":
    raise SystemExit(main())

- old_string: 

### Turn 54 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\commands.py has been created successfully.

### Turn 55 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\__main__.py has been created successfully.

### Turn 56 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\app.py has been created successfully.

### Turn 57 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\completer.py has been created successfully.

### Turn 58 (Assistant)
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\tests\test_auth.py
- new_string: from nsp_grok.auth import (
    authenticate,
    can,
    check_password_policy,
    hash_password,
    in_span,
    verify_password,
)
from nsp_grok.lab import Store


def test_default_users_login():
    store = Store()
    user, err = authenticate(store.users, "admin", "Nokia123!")
    assert err == ""
    assert user is not None
    assert user.role == "administrator"


def test_username_is_case_insensitive():
    store = Store()
    user, err = authenticate(store.users, "ADMIN", "Nokia123!")
    assert user is not None
    assert err == ""


def test_bad_password_counts_down():
    store = Store()
    _, err = authenticate(store.users, "viewer", "wrong")
    assert "remaining" in err
    assert store.users["viewer"].failed_logins == 1


def test_lockout_after_five_failures():
    store = Store()
    for _ in range(5):
        _, err = authenticate(store.users, "viewer", "nope")
    assert "locked" in err.lower()
    _, err = authenticate(store.users, "viewer", "Nokia123!")
    assert "locked" in err.lower()


def test_password_policy():
    assert check_password_policy("admin", "short")
    assert check_password_policy("admin", "nouppercase1!")
    assert not check_password_policy("admin", "Nokia123!")


def test_hash_roundtrip():
    digest, salt = hash_password("Nokia123!")
    from nsp_grok.models import User

    u = User("x", digest, salt, "g", "r", "X")
    assert verify_password(u, "Nokia123!")
    assert not verify_password(u, "nope")


def test_span_and_access():
    store = Store()
    noc = store.users["noc"]
    admin = store.users["admin"]
    viewer = store.users["viewer"]
    assert in_span(noc, "METRO-BA", "PE-BAIRES-01")
    assert not in_span(noc, "CORE", "P-CORE-01")
    assert in_span(admin, "CORE", "P-CORE-01")
    assert can(admin, "execute")
    assert can(viewer, "read")
    assert not can(viewer, "write")

- old_string: 
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\tests\test_tree.py
- new_string: from nsp_grok.lab import Store
from nsp_grok.tree import build_tree, pwd, resolve


def _root():
    store = Store()
    user = store.users["admin"]
    return store, user, build_tree(store, user)


def test_root_children():
    _store, _user, root = _root()
    assert set(root.children) >= {"equipment", "routing", "mpls", "services", "alarms"}


def test_cd_and_pwd():
    _store, _user, root = _root()
    found = resolve(root, [], "equipment")
    assert found is not None
    path, node = found
    assert pwd(path) == "/equipment"
    assert "METRO-BA" in node.children


def test_absolute_and_parent():
    _store, _user, root = _root()
    found = resolve(root, [], "/equipment/METRO-BA/PE-BAIRES-01")
    assert found is not None
    path, node = found
    assert node.kind == "ne"
    up = resolve(root, path, "..")
    assert up is not None
    assert up[0] == ["equipment", "METRO-BA"]


def test_span_hides_core_from_noc():
    store = Store()
    noc = store.users["noc"]
    root = build_tree(store, noc)
    found = resolve(root, [], "/equipment")
    assert found is not None
    groups = set(found[1].children)
    assert "METRO-BA" in groups
    assert "CORE" not in groups

- old_string: 
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\tests\test_commands.py
- new_string: from nsp_grok.app import build_ctx
from nsp_grok.commands import dispatch
from nsp_grok.lab import Store


def _admin_ctx():
    store = Store()
    return build_ctx(store, store.users["admin"])


def _viewer_ctx():
    store = Store()
    return build_ctx(store, store.users["viewer"])


def test_ls_root():
    ctx = _admin_ctx()
    out = dispatch(ctx, "ls")
    assert out.error == ""
    assert out.renderable is not None


def test_cd_show_ne():
    ctx = _admin_ctx()
    dispatch(ctx, "cd /equipment/METRO-BA/PE-BAIRES-01")
    out = dispatch(ctx, "show")
    assert out.error == ""


def test_mpls_lsp_list():
    ctx = _admin_ctx()
    out = dispatch(ctx, "/mpls lsps")
    assert out.error == ""


def test_create_and_shutdown_lsp():
    ctx = _admin_ctx()
    out = dispatch(
        ctx,
        "mpls lsp create name=lsp-test from=PE-BAIRES-01 to=PE-CORDOBA-01 type=dynamic sig=rsvp",
    )
    assert out.error == ""
    assert "lsp-test" in ctx.store.lsps
    out = dispatch(ctx, "mpls lsp shutdown lsp-test")
    assert ctx.store.lsps["lsp-test"].admin == "down"


def test_viewer_cannot_create_lsp():
    ctx = _viewer_ctx()
    out = dispatch(
        ctx,
        "mpls lsp create name=lsp-x from=PE-BAIRES-01 to=PE-CORDOBA-01",
    )
    assert "permission denied" in out.error


def test_alarm_ack():
    ctx = _admin_ctx()
    out = dispatch(ctx, "alarm ack A-1001")
    assert out.error == ""
    alarm = next(a for a in ctx.store.alarms if a.id == "A-1001")
    assert alarm.acked
    assert alarm.acked_by == "admin"


def test_unknown_command():
    ctx = _admin_ctx()
    out = dispatch(ctx, "blargh")
    assert "unknown command" in out.error


def test_find_baires():
    ctx = _admin_ctx()
    out = dispatch(ctx, "find BAIRES")
    assert out.error == ""

- old_string: 
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\README.md
- new_string: # NSP-Grok 24.11

Shell de gestión **IP/MPLS** inspirado en Nokia **NFM-P / NSP Classic Management 24.11**.

No replica la GUI Java. El operador inicia sesión y queda en una consola tipo [Grok 4.6](https://x.ai): prompt, **slash commands**, barra de estado, Tab-complete y el árbol de navegación NFM-P montado como un filesystem.

Basado en:

- *NSP NFM-P Classic Management User Guide 24.11* (3HE-20021) — árbol, forms, MPLS, túneles, servicios
- *NSP System Administrator Guide 24.11 Issue 11* (3HE-20030) — usuarios locales, UAC, span of control, password policy, lockout
- *NSP NFM-P Statistics Management Guide 24.11* (3HE-20019) — estadísticas de performance

## Requisitos

Python 3.11+ (Windows, Linux o macOS).

```powershell
cd C:\Users\elzoy\Code\nsp-grok-2411
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Arranque

```powershell
nsp-grok
# o
python -m nsp_grok
```

Login interactivo. Usuarios de laboratorio:

| usuario    | password    | rol             | span                         |
|------------|-------------|-----------------|------------------------------|
| `admin`    | `Nokia123!` | administrator   | ALL                          |
| `operator` | `Nokia123!` | operator (rw)   | ALL                          |
| `noc`      | `Nokia123!` | fault-manager   | solo METRO-BA (Buenos Aires) |
| `viewer`   | `Nokia123!` | monitor (ro)    | ALL, solo lectura            |

Política de password NSP 24.11: ≥10 caracteres, mayúscula, minúscula, dígito, especial. Lockout a los 5 fallos.

## Qué ves después del login

```
admin / › ls
admin / › cd equipment
admin /equipment › ls
admin /equipment › cd METRO-BA/PE-BAIRES-01
admin /equipment/METRO-BA/PE-BAIRES-01 › show
admin / › /alarms
admin / › /mpls lsps
admin / › /topology
```

La barra inferior (estilo Grok status line) muestra usuario, rol, cwd, alarmas crit/maj, NEs y release.

## Comandos

Navegación (árbol NFM-P: Equipment, Routing, MPLS, Services, Alarms):

| comando        | efecto                          |
|----------------|---------------------------------|
| `ls` `cd` `pwd` `tree` | recorrer el dominio        |
| `show` / `cat` | property form del objeto        |
| `find <texto>` | buscar NEs, LSPs, IPs, alarmas  |

Slash (escribí `/` y Tab, como en Grok):

`/help` `/status` `/whoami` `/ne` `/mpls` `/services` `/alarms` `/stats` `/topology` `/tasks` `/users` `/resync` `/passwd` `/clear` `/quit`

MPLS (User Guide cap. 31–33):

```
mpls lsp list
mpls lsp show lsp-ba-cba
mpls lsp create name=lsp-x from=PE-BAIRES-01 to=PE-SALTA-01 type=dynamic sig=rsvp
mpls lsp shutdown lsp-x
mpls lsp turnup lsp-x
alarm ack A-1001
stats lsp:lsp-ba-cba
stats ne:PE-BAIRES-01:port:1/1/1
```

## Modo no interactivo

```powershell
python -m nsp_grok -u admin -p Nokia123! -c "ls" -c "/mpls lsps" -c "/alarms" -c "/quit"
```

## Lab

Red MPLS de demostración (Argentina): 8 NEs (7750 / 7950 / 7705), RSVP-TE, SR-TE, LDP, SDPs, VPRN/VPLS/Epipe, alarmas y stats MIB.

Todo vive en memoria: no habla con un NFM-P real. El siguiente paso natural es cablear el XML/REST API de NSP 24.11 detrás de los mismos comandos.

## Tests

```powershell
pytest -q
```

- old_string: 

### Turn 59 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\README.md has been created successfully.

### Turn 60 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\tests\test_tree.py has been created successfully.

### Turn 61 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\tests\test_auth.py has been created successfully.

### Turn 62 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\tests\test_commands.py has been created successfully.

### Turn 63 (Assistant)
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\commands.py
- old_string: from nsp_grok.models import Alarm, Lsp, Task, User
- new_string: from nsp_grok.models import Lsp, Task, User
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\completer.py
- old_string:     def _slash(self, text: str) -> list[Completion] | None:
- new_string:     def _slash(self, text: str):
[tool_request: run_terminal_command]
- command: python -m venv .venv ; .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
- description: Create venv and install nsp-grok with pytest

### Turn 64 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\completer.py has been updated successfully.

### Turn 65 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\commands.py has been updated successfully.

### Turn 66 (Function)
[tool_response]
<task-id>call-f5cde672-c27b-4938-b18a-7f04a0773198-45</task-id>
<task-type>bash</task-type>
<output-file>C:\Users\elzoy\.grok\sessions\C%3A%5CUsers%5Celzoy%5CCode%5Cnsp-grok-2411\01a06e01-5cac-7511-bc2a-a0dd4373fd76\terminal\call-f5cde672-c27b-4938-b18a-7f04a0773198-45.log</output-file>
<status>running</status>
<summary>Command "python -m venv .venv ; .\.venv\Scripts\python.exe -m pip install -e ".[dev]"" exceeded the default timeout and was automatically moved to background. Process is still running.</summary>
Use get_command_or_subagent_output with task_ids=["call-f5cde672-c27b-4938-b18a-7f04a0773198-45"] when you need the output.

### Turn 67 (Assistant)
[tool_request: get_command_or_subagent_output]
- task_ids: ["call-f5cde672-c27b-4938-b18a-7f04a0773198-45"]
- timeout_ms: 120000

### Turn 68 (Function)
[tool_response]
=== Task call-f5cde672-c27b-4938-b18a-7f04a0773198-45 ===
Command: python -m venv .venv ; .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Status: completed
Duration: 23.50s
Exit Code: 0
Output File: C:\Users\elzoy\.grok\sessions\C%3A%5CUsers%5Celzoy%5CCode%5Cnsp-grok-2411\01a06e01-5cac-7511-bc2a-a0dd4373fd76\terminal\call-f5cde672-c27b-4938-b18a-7f04a0773198-45.log

=== Output ===
Obtaining file:///C:/Users/elzoy/Code/nsp-grok-2411
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Checking if build backend supports build_editable: started
  Checking if build backend supports build_editable: finished with status 'done'
  Getting requirements to build editable: started
  Getting requirements to build editable: finished with status 'done'
  Preparing editable metadata (pyproject.toml): started
  Preparing editable metadata (pyproject.toml): finished with status 'done'
Collecting rich>=13.7.0 (from nsp-grok==24.11.0)
  Using cached rich-15.0.0-py3-none-any.whl.metadata (18 kB)
Collecting prompt_toolkit>=3.0.47 (from nsp-grok==24.11.0)
  Using cached prompt_toolkit-3.0.53-py3-none-any.whl.metadata (6.4 kB)
Collecting pytest>=8.0 (from nsp-grok==24.11.0)
  Using cached pytest-9.1.1-py3-none-any.whl.metadata (7.6 kB)
Collecting wcwidth>=0.1.4 (from prompt_toolkit>=3.0.47->nsp-grok==24.11.0)
  Using cached wcwidth-0.8.3-py3-none-any.whl.metadata (43 kB)
Collecting colorama>=0.4 (from pytest>=8.0->nsp-grok==24.11.0)
  Using cached colorama-0.4.6-py2.py3-none-any.whl.metadata (17 kB)
Collecting iniconfig>=1.0.1 (from pytest>=8.0->nsp-grok==24.11.0)
  Using cached iniconfig-2.3.0-py3-none-any.whl.metadata (2.5 kB)
Collecting packaging>=22 (from pytest>=8.0->nsp-grok==24.11.0)
  Using cached packaging-26.3-py3-none-any.whl.metadata (3.5 kB)
Collecting pluggy<2,>=1.5 (from pytest>=8.0->nsp-grok==24.11.0)
  Using cached pluggy-1.6.0-py3-none-any.whl.metadata (4.8 kB)
Collecting pygments>=2.7.2 (from pytest>=8.0->nsp-grok==24.11.0)
  Using cached pygments-2.21.0-py3-none-any.whl.metadata (2.5 kB)
Collecting markdown-it-py>=2.2.0 (from rich>=13.7.0->nsp-grok==24.11.0)
  Using cached markdown_it_py-4.2.0-py3-none-any.whl.metadata (7.4 kB)
Collecting mdurl~=0.1 (from markdown-it-py>=2.2.0->rich>=13.7.0->nsp-grok==24.11.0)
  Using cached mdurl-0.1.2-py3-none-any.whl.metadata (1.6 kB)
Using cached prompt_toolkit-3.0.53-py3-none-any.whl (392 kB)
Using cached pytest-9.1.1-py3-none-any.whl (386 kB)
Using cached pluggy-1.6.0-py3-none-any.whl (20 kB)
Using cached colorama-0.4.6-py2.py3-none-any.whl (25 kB)
Using cached iniconfig-2.3.0-py3-none-any.whl (7.5 kB)
Using cached packaging-26.3-py3-none-any.whl (129 kB)
Using cached pygments-2.21.0-py3-none-any.whl (1.3 MB)
Using cached rich-15.0.0-py3-none-any.whl (310 kB)
Using cached markdown_it_py-4.2.0-py3-none-any.whl (91 kB)
Using cached mdurl-0.1.2-py3-none-any.whl (10.0 kB)
Using cached wcwidth-0.8.3-py3-none-any.whl (331 kB)
Building wheels for collected packages: nsp-grok
  Building editable for nsp-grok (pyproject.toml): started
  Building editable for nsp-grok (pyproject.toml): finished with status 'done'
  Created wheel for nsp-grok: filename=nsp_grok-24.11.0-0.editable-py3-none-any.whl size=4649 sha256=4628ca19c478598f5f2a22ef51b99a2c2e1e61026f5f2144f71cd9e245791afa
  Stored in directory: C:\Users\elzoy\AppData\Local\Temp\pip-ephem-wheel-cache-do1jerja\wheels\cd\b3\87\81badd70f02572a9559b40ec1f0b072781082599f5526c5854
Successfully built nsp-grok
Installing collected packages: wcwidth, pygments, pluggy, packaging, mdurl, iniconfig, colorama, pytest, prompt_toolkit, markdown-it-py, rich, nsp-grok
Successfully installed colorama-0.4.6 iniconfig-2.3.0 markdown-it-py-4.2.0 mdurl-0.1.2 nsp-grok-24.11.0 packaging-26.3 pluggy-1.6.0 prompt_toolkit-3.0.53 pygments-2.21.0 pytest-9.1.1 rich-15.0.0 wcwidth-0.8.3

[notice] A new release of pip is available: 26.1.2 -> 26.2.1
[notice] To update, run: C:\Users\elzoy\Code\nsp-grok-2411\.venv\Scripts\python.exe -m pip install --upgrade pip


### Turn 69 (Assistant)
[tool_request: run_terminal_command]
- command: .\.venv\Scripts\python.exe -m pytest -q
- description: Run unit tests for auth, tree, commands

### Turn 70 (Function)
[tool_response]
exit: 1
....F..............                                                      [100%]
================================== FAILURES ===================================
____________________________ test_password_policy _____________________________

    def test_password_policy():
        assert check_password_policy("admin", "short")
        assert check_password_policy("admin", "nouppercase1!")
>       assert not check_password_policy("admin", "Nokia123!")
E       AssertionError: assert not ['minimum length is 10']
E        +  where ['minimum length is 10'] = check_password_policy('admin', 'Nokia123!')

tests\test_auth.py:46: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_auth.py::test_password_policy - AssertionError: assert not ...
1 failed, 18 passed in 5.65s


<system-reminder>
Background task "01a06e1a-7852-7b91-89fe-9f4fffaa6908" completed (exit code: 1).
Command: .\.venv\Scripts\python.exe -m pytest -q | Duration: 6.8s
Use get_command_or_subagent_output("01a06e1a-7852-7b91-89fe-9f4fffaa6908") to see the full output.
</system-reminder>

### Turn 71 (Assistant)
La password de demo no cumple la política NSP (≥10). La cambio a `Nokia1234!`.
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\lab.py
- old_string: "Nokia123!"
- new_string: "Nokia1234!"
- replace_all: true
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\app.py
- old_string: "[dim]Default password:[/] [bold]Nokia123![/]\n"
- new_string: "[dim]Default password:[/] [bold]Nokia1234![/]\n"
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\README.md
- old_string: Nokia123!
- new_string: Nokia1234!
- replace_all: true
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\tests\test_auth.py
- old_string: Nokia123!
- new_string: Nokia1234!
- replace_all: true
[tool_request: search_replace]
- file_path: C:\Users\elzoy\Code\nsp-grok-2411\tests\test_commands.py
- old_string: Nokia123!
- new_string: Nokia1234!
- replace_all: true

### Turn 72 (Function)
[tool_response]
The string to replace was not found in the file, use the read_file tool to see the correct string. The user may have changed the file since you last read it.

### Turn 73 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\app.py has been updated successfully.

### Turn 74 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\nsp_grok\lab.py has been updated. All occurrences were successfully replaced.

### Turn 75 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\tests\test_auth.py has been updated. All occurrences were successfully replaced.

### Turn 76 (Function)
[tool_response]
The file C:\Users\elzoy\Code\nsp-grok-2411\README.md has been updated. All occurrences were successfully replaced.

### Turn 77 (Assistant)
[tool_request: run_terminal_command]
- command: .\.venv\Scripts\python.exe -m pytest -q ; .\.venv\Scripts\python.exe -m nsp_grok -u admin -p Nokia1234! -c "ls" -c "cd equipment" -c "ls" -c "cd METRO-BA/PE-BAIRES-01" -c "show" -c "/mpls lsps" -c "/alarms" -c "/topology" -c "/status" -c "/quit"
- description: Re-run tests and demo the CLI in batch mode

### Turn 78 (Function)
[tool_response]
exit: 0
...................                                                      [100%]
19 passed in 4.70s

session  85a60cf7  ·  admin  ·  administrator  ·  span ALL
8 NEs managed  ·  8 LSPs  ·  5 services  ·  7 alarms
Type /help or ls to start.  Tab completes.  / opens commands.

admin / › ls
                         /                          
┌────────────┬────────┬────────────────────┬───────┐
│ name       │ kind   │ label              │ state │
├────────────┼────────┼────────────────────┼───────┤
│ equipment/ │ folder │ Equipment view     │       │
│ routing/   │ folder │ Routing view       │       │
│ mpls/      │ folder │ MPLS               │       │
│ services/  │ folder │ Customer services  │       │
│ alarms/    │ folder │ Faults             │       │
│ stats      │ folder │ Statistics         │       │
│ admin/     │ folder │ Users and Security │       │
└────────────┴────────┴────────────────────┴───────┘
admin / › cd equipment
admin /equipment › ls
                         /equipment                          
┌─────────────┬────────┬────────────────────────────┬───────┐
│ name        │ kind   │ label                      │ state │
├─────────────┼────────┼────────────────────────────┼───────┤
│ ACCESS/     │ folder │ equipment-group ACCESS     │       │
│ CORE/       │ folder │ equipment-group CORE       │       │
│ METRO-BA/   │ folder │ equipment-group METRO-BA   │       │
│ METRO-CBA/  │ folder │ equipment-group METRO-CBA  │       │
│ METRO-Cuyo/ │ folder │ equipment-group METRO-Cuyo │       │
└─────────────┴────────┴────────────────────────────┴───────┘
admin /equipment › cd METRO-BA/PE-BAIRES-01
admin /equipment/METRO-BA/PE-BAIRES-01 › show
┌──────────────────────── NE properties  PE-BAIRES-01 ─────────────────────────┐
│ Displayed Name        PE-BAIRES-01                                           │
│ System IP             10.10.1.1                                              │
│ Chassis Type          7750 SR-12e                                            │
│ Software Version      TiMOS-C-24.10.R1                                       │
│ Site                  Buenos Aires                                           │
│ Equipment Group       METRO-BA                                               │
│ Chassis MAC           00:03:fa:11:01:01                                      │
│ Administrative State  up                                                     │
│ Operational State     up                                                     │
│ Management State      managed                                                │
│ Protocols             OSPF, ISIS, LDP, RSVP, MPLS, BGP, SR                   │
│ Cards / Ports         3 / 5                                                  │
│                      Cards                                                   │
│ ┌──────┬────────────┬───────┬──────────┬───────┐                             │
│ │ slot │ type       │ admin │ oper     │ ports │                             │
│ ├──────┼────────────┼───────┼──────────┼───────┤                             │
│ │ A    │ cpm-2      │ up    │ up       │ 0     │                             │
│ │ B    │ cpm-2      │ up    │ up       │ 0     │                             │
│ │ 1    │ imm48-sfp+ │ up    │ degraded │ 5     │                             │
│ └──────┴────────────┴───────┴──────────┴───────┘                             │
└──────────────────────────────────────────────────────────────────────────────┘
admin /equipment/METRO-BA/PE-BAIRES-01 › /mpls lsps
                                   MPLS LSPs                                    
┌───────┬───────┬──────┬───────┬───────┬───────┬───────┬────────┬───────┬──────┐
│ name  │ type  │ sig  │ from  │ to    │ path  │ bw    │ prot   │ admin │ oper │
├───────┼───────┼──────┼───────┼───────┼───────┼───────┼────────┼───────┼──────┤
│ lsp-… │ dyna… │ rsvp │ PE-B… │ PE-C… │ path… │ 1000  │ fast-… │ up    │ up   │
│ lsp-… │ dyna… │ rsvp │ PE-C… │ PE-B… │ path… │ 1000  │ fast-… │ up    │ up   │
│ lsp-… │ sr-te │ sr   │ PE-B… │ PE-M… │ path… │ 500   │ ti-lfa │ up    │ up   │
│ lsp-… │ dyna… │ ldp  │ PE-B… │ PE-R… │ path… │ 200   │ none   │ up    │ up   │
│ lsp-… │ dyna… │ rsvp │ P-CO… │ P-CO… │ path… │ 10000 │ bypass │ up    │ up   │
│ lsp-… │ dyna… │ rsvp │ PE-B… │ PE-S… │ path… │ 100   │ none   │ up    │ down │
│ bypa… │ bypa… │ rsvp │ P-CO… │ P-CO… │ loos… │ 0     │ manua… │ up    │ up   │
│ lsp-… │ stat… │ rsvp │ PE-B… │ PE-C… │ loos… │ 0     │ none   │ down  │ down │
└───────┴───────┴──────┴───────┴───────┴───────┴───────┴────────┴───────┴──────┘
admin /equipment/METRO-BA/PE-BAIRES-01 › /alarms
                                     Alarms                                     
┌────────┬──────────┬────────────┬────────────┬────────────┬───────┬───────────┐
│ id     │ sev      │ cause      │ object     │ NE         │ acked │ raised    │
├────────┼──────────┼────────────┼────────────┼────────────┼───────┼───────────┤
│ A-1001 │ critical │ tunnelOpe… │ sdp:401    │ PE-BAIRES… │ no    │ 18:21:39Z │
│ A-1002 │ critical │ lspOperDo… │ lsp:lsp-b… │ PE-BAIRES… │ no    │ 18:21:39Z │
│ A-1003 │ major    │ portLinkD… │ ne:PE-BAI… │ PE-BAIRES… │ no    │ 12:27:39Z │
│ A-1004 │ major    │ serviceSi… │ svc:500    │ PE-SALTA-… │ no    │ 18:27:39Z │
│ A-1007 │ minor    │ versionMi… │ ne:PE-COR… │ PE-CORDOB… │ yes   │ 20:27:39Z │
│ A-1005 │ minor    │ sfpRxPowe… │ ne:PE-MEN… │ PE-MENDOZ… │ no    │ 18:27:39Z │
│ A-1006 │ warning  │ neCpuHigh  │ ne:P-CORE… │ P-CORE-01  │ no    │ 20:03:39Z │
└────────┴──────────┴────────────┴────────────┴────────────┴───────┴───────────┘
admin /equipment/METRO-BA/PE-BAIRES-01 › /topology
┌─────────────────────────── Application → Topology ───────────────────────────┐
│                                                                              │
│ Physical / IGP topology  (lab ARGENTINA)                                     │
│                                                                              │
│                     PE-SALTA-01                                              │
│                          |                                                   │
│                     P-CORE-01────────P-CORE-02                               │
│                     /    |    \              \                               │
│          PE-BAIRES-01  PE-MENDOZA-01     PE-CORDOBA-01                       │
│                 |                                                            │
│          PE-BAIRES-02                                                        │
│                 |                                                            │
│          PE-ROSARIO-01                                                       │
│                                                                              │
│   green oper-up    yellow degraded    red oper-down                          │
│   RSVP-TE: lsp-ba-cba, lsp-core-p2p, lsp-ba-sal (down)                       │
│   SR-TE:   lsp-ba-mza-sr                                                     │
│   LDP:     lsp-ba-ros                                                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
admin /equipment/METRO-BA/PE-BAIRES-01 › /status
                           Session                           
Product             NSP-Grok 24.11  NFM-P classic shell      
Session             85a60cf7                                 
User                admin  (administrator / administrators)  
Span of Control     ALL                                      
CWD                 /equipment/METRO-BA/PE-BAIRES-01         
NEs                 8/8 operational                          
LSPs                6/8 operational                          
Services            4/5 operational                          
Alarms              critical=2  major=2  minor=2  warning=1  
Started             2026-09-04 20:27:39Z                     
admin /equipment/METRO-BA/PE-BAIRES-01 › /quit


<system-reminder>
Background task "01a06e1a-eeb1-7ae1-9afe-5dad944b8cad" completed (exit code: 0).
Command: .\.venv\Scripts\python.exe -m pytest -q ; .\.venv\Scripts\python.exe -m nsp_grok -u admin -p Nokia1234! -c "ls" -c "cd equipment" -c "ls" -c "cd METRO-BA/PE-BAIRES-01" -c "show" -c "/mpls lsps" -c "/alarms" -c "/topology" -c "/status" -c "/quit" | Duration: 6.0s
Use get_command_or_subagent_output("01a06e1a-eeb1-7ae1-9afe-5dad944b8cad") to see the full output.
</system-reminder>

### Turn 79 (Assistant)
[tool_request: todo_write]
- todos: [{"id":"1","status":"completed"},{"id":"2","status":"completed"},{"id":"3","status":"completed"},{"id":"4","status":"completed"},{"id":"5","status":"completed"}]
- merge: true

### Turn 80 (Function)
[tool_response]
- [completed] 1: Diseñar modelo de datos NFM-P (NEs, MPLS, servicios, alarmas, usuarios)
- [completed] 2: Implementar auth (login, roles, span of control, sesión)
- [completed] 3: Shell Grok-like: prompt, slash commands, status line, navegación
- [completed] 4: Comandos de dominio: equipment, mpls, services, alarms, stats
- [completed] 5: README + requirements + demo lab y verificar el CLI


### Turn 81 (Assistant)
Listo. Leí los tres PDFs y armé un **shell Python**, no la GUI Java.

La interfaz es tipo Grok 4.6: login, prompt, comandos `/`, Tab-complete y barra de estado. El árbol NFM-P (Equipment, Routing, MPLS, Services, Alarms) se navega con `cd` / `ls` / `show`.

## Arranque

```powershell
cd C:\Users\elzoy\Code\nsp-grok-2411
.\.venv\Scripts\Activate.ps1
python -m nsp_grok
```

| usuario | password | qué puede hacer |
|---|---|---|
| `admin` | `Nokia1234!` | todo |
| `operator` | `Nokia1234!` | leer + escribir MPLS/servicios |
| `noc` | `Nokia1234!` | solo METRO-BA + ack/clear de alarmas |
| `viewer` | `Nokia1234!` | solo lectura |

Password ≥10 caracteres (política NSP 24.11). Lockout a los 5 fallos.

## Después del login

```
admin / › ls
admin / › cd equipment/METRO-BA/PE-BAIRES-01
admin /equipment/METRO-BA/PE-BAIRES-01 › show
admin / › /mpls lsps
admin / › /alarms
admin / › mpls lsp create name=lsp-x from=PE-BAIRES-01 to=PE-SALTA-01 sig=rsvp
admin / › alarm ack A-1001
admin / › /topology
```

`/help` lista todo. La barra de abajo muestra usuario, rol, path, crit/maj y release 24.11.

## De dónde sale

- **User Guide**: árbol, property forms, MPLS LSP/path/SDP, Turn Up / Shut Down, Task Manager
- **Admin Guide**: usuarios locales, grupos, roles, span of control, password policy, lockout
- **Statistics Guide**: stats de performance por FDN (`stats lsp:lsp-ba-cba`)

Lab en memoria: 8 NEs (7750 / 7950 / 7705), RSVP-TE, SR-TE, LDP, VPRN/VPLS/Epipe y alarmas. **No habla con un NFM-P real** todavía.

19 tests OK. Cuando quieras, el siguiente paso puede ser cablear el REST/XML API 24.11 detrás de los mismos comandos.

### Turn 82 (Human)
<user_query>
C:\Users\elzoy\Downloads\XML_API_Developer_Guide_Issue_1.pdf te dejo este otro para que analices como referencia
</user_query>

### Turn 83 (Assistant)
Voy a leer la guía del XML API y cruzarla con el shell que ya tenemos.
[tool_request: read_file]
- target_file: C:\Users\elzoy\Downloads\XML_API_Developer_Guide_Issue_1.pdf
- format: text
- pages: 1-20


[... TRUNCATED at 524288 bytes, 310 turns omitted ...]
