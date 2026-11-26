tags. They are asking for a brand new comprehensive markdown document of the brainstormed plan and build guide. *   *Mode 2: Simple Q&A?* Yes, this is a textual answer/deliverable generated from the conversation history and research material, without usingtags. Let's double check: "Do Not Use a report Tag: This is a strict rule. Your response should be plain text in this mode." *   *Wait*: Should I attach the "Would you like me to do a more in-depth research instead and propose a research plan?" prompt? Let's check rule 5 of Mode 2: *   Obvious follow-up: asks about facts/findings already in report, clarify/elaborate on specific sections, or synthesize what was already discussed. Here, the user explicitly says "create a comprehensive markdown document of what we have brainstormed and how I can use it to start the build." That is directly grounded in the conversation history and existing research material! So do NOT attach the research offer. 3.  **Check Facts & Grounding against Research Material (Internal Snippets) & Conversation History**: *   Wait—let's carefully verify details from the provided snippets so we don't hallucinate or repeat anything inaccurate from earlier turns if there were discrepancies, while staying faithful to what was brainstormed! *   Let's check the snippets: *   Kiroween 2026 rules (,,): *   Submission deadline: Dec 4, 2026 @ 2:00pm PST (,). *   Judging Period: Dec 16, 2026 (1:00 pm PT) – Jan 29, 2027 (1:00 pm PT) (). *   Skeleton Crew track: Build a skeleton code template lean enough to be clear but flexible enough to support various use cases. Show versatility with two distinct applications from the foundation. Repo must contain 2 separate repo folders for the 2 separate applications (,). *   Repo rules: Public GitHub (not GitLab/BitBucket), open-source license visible in About section,/.kirodirectory at root (NOT in.gitignore, as that could disqualify) (,). *   Video: Public YouTube video < 3 minutes, showing project functioning on device (,,). *   Judging criteria (20% / 10 pts each): Potential Impact, Technological Implementation, Design, Innovation/Idea, Presentation (). *   Prizes: Overall ($30k, $20k, $10k), Category ($5k each for Resurrection, Frankenstein, Skeleton Crew, Costume Contest), Bonus (Best Startup $10k, Best Ghost of Kiroween Past $2k, Best Kiro Crew App $1k, Best Student $1.5k + 1-yr Kiro Pro Max, Best Demo $1k, Bonus Blog 2k Kiro credits, Social Blitz 3-month Kiro Pro+ #KiroweenHackathon26) (,). *   Models in Kiro (,): *   Wait! Notice in earlier turns, the model mentioned Claude 3.7 Sonnet / 3.5 Sonnet / Nova Pro, which aren't in the Nov 2026 / snippets! Look at and: Active models in Kiro as of Nov 2026 include **Claude Sonnet 5.5** (1.3x credit multiplier, 1M context, >30% faster output, great for scoped coding, agents/subagents), **Claude Sonnet 5** (spec-driven workflows, multi-step agentic CLI/Web tasks), **Claude Opus 5.5** (2.0x, demanding agentic coding, self-verification, architecture decisions), **GPT-5.6 Terra** (2.2x up to 272K, routine multi-step development) / **GPT-5.6 Luna** (0.6x up to 272K, high-frequency agentic tasks, speed & credit efficiency), **MiniMax M2.5** (0.25x, frontier-class coding at low cost), **GLM-5** (0.5x, 200K context, systems engineering), **Qwen3 Coder Next** (0.05x, 256K context, long CLI sessions). *   This is a GREAT catch! Since the user asked for a comprehensive markdown document to start the build, I should update/refine the model advice using the actual active Kiro models from and (e.g., Claude Sonnet 5.5 / Claude Sonnet 5 for spec-driven execution and speed, Claude Opus 5.5 for heavy architecture/debugging, and GPT-5.6 Luna or MiniMax M2.5 / Qwen3 Coder Next for credit-efficient boilerplate/iterations)! *   Hooks schema in Kiro (,,,): *   Look closely at and (updated Nov 12 & Nov 18, 2026!): *   Exact JSON schema (v1): "version": "v1", "hooks": [ { "name": "...", "description": "...", "trigger": "...", "matcher": "...", "action": { "type": "command"|"agent", "command"|"prompt": "..." }, "timeout": 60, "enabled": true } ]. *   Exact trigger names in Kiro IDE/CLI ([cite: 6]): *   PromptSubmit(IDE, CLI, Web) *  AgentStop(IDE, CLI, Web) *  SessionStart(IDE, CLI V3, Web) *  AgentSpawn (AgentSpawn/agentSpawn- CLI 2.x/V3 alias, NOT supported in IDE!) -> Good catch! Earlier turn usedAgentSpawnfor IDE, whereasSessionStartworks across IDE, CLI V3, and Web! *  PreToolUse, PostToolUse (IDE, CLI, Web) *   File Save (PostFileSavein/ JSON examples, orFile Savein UI) — note that file hooks respond ONLY to changes made by the agent, not manual human edits in the editor (,)! *  PreTaskExecution, PostTaskExecution(IDE, CLI V3) *  PreCompact, PostCompact(IDE 1.4.121+, CLI 3.1.0+) *  PermissionRequest(IDE, CLI 3.4.0+) *   Also in Kiro Crew ([cite: 8]): hooks live in~/.kiro/crew/hooks.jsonand triggers areAgentSpawn, UserPromptSubmit, PreToolUse, PostToolUse, Stop. *   Also note the user's own preference: The user is a **Cloud Engineer, minimal code experience, works best with Python code**, and wants to bridge GibzB/skillforgeandtripleyak/SkillForge (scripts/.py! Python 3.8+ standard library / PyYAML). Earlier in the conversation, the Blueprint drifted a bit into TypeScript (packages/skillforge-corein TS +fast-check), whereas earlier we also talked about skillforge_core/in Python! Let's make sure the comprehensive markdown document clearly reconciles this—highlighting the Python core scripts fromtripleyak/SkillForge (frontmatter.py, discover_skills.py, triage_skill_request.py, validate_skill.py, run_skill_evals.py, skillforge_doctor.py, compile_skill.py, mine_skill_friction.py, init_skill.py, package_skill.py[cite: 9]) and either keeping the core Python-first (which fits the user's "work best with Python code" +tripleyak/SkillForge's actual codebase!) or clearly explaining how the Python core powers the two apps (e.g., Python CLI / AWS Compliance Auditor + Web/React or Python-backed Gothic Narrative Engine), with Property-Based Testing using Python's hypothesis(orfast-checkif using Node/TS for the web app)! Keepingskillforge-corePython-native (mirroringtripleyak/SkillForge's actual scripts/.py) while using React/WebGL or FastAPI+React for App 2 makes it *actually* easy for a Python cloud engineer to build and vibecode! Let's definitely make it practical and aligned with both the user's strengths and what we brainstormed. 4.  **Structure of the Comprehensive Markdown Document**: Make it a complete, copy-paste-ready "Master Build & Blueprint Document" (KIRO_SKILLFORGE_MASTER_BLUEPRINT.md) that the user can drop straight into their repo and start executing immediately in Kiro. Let's organize it cleanly into logical sections: *   **1. Project Identity, User Profile & Hackathon Alignment** *   Submission metadata (Kiroween 2026, Skeleton Crew track, Kiro ID d-9067642ac7.649834d8-d081-70cb-1dec-8857d5478ad4, dates: Dec 1 credits deadline, Dec 4 @ 2:00 PM PST submission deadline). *   The Core Concept (combining GibzB/skillforge+tripleyak/SkillForgev6.0.0 evidence-driven 4-phase architecture into a Kiro-native platform). *   Why Skeleton Crew + Multi-Prize Stacking (Category $5k, Overall $10k–$30k, Best Kiro Crew App $1k, Best Demo $1k, Bonus Blog 2k credits, Social Blitz 3-mo Pro+#KiroweenHackathon26). *   **2. Optimal Kiro Model Strategy (Fast & Rigorous)** *   Exact active Kiro models from docs (,): *   *Architecture, Specs & Complex Debugging:* **Claude Sonnet 5** / **Claude Sonnet 5.5** (1.3x multiplier, 1M context, >30% faster output, built for spec-driven workflows) or **Claude Opus 5.5** (2.0x multiplier, self-verification & architecture decisions). *   *High-Speed Vibecoding & Credit-Efficient Execution:* **GPT-5.6 Luna** (0.6x up to 272K tokens, 74.6 Coding Agent Index, fast high-frequency agentic tasks) or **MiniMax M2.5** (0.25x, strong full-lifecycle coding) / **Qwen3 Coder Next** (0.05x, 256K context, strong CLI error recovery). *   How to combine them with your 4,000 free Kiro credits. *   **3. Unified Monorepo Architecture (Skeleton Crew Compliant)** *   Note the Skeleton Crew requirement: lean skeleton core + **2 separate application folders** (apps/app1-cloud-compliance/andapps/app2-spooky-game-engine/) + un-ignored /.kiro/at root + MITLICENSE+README.md. *   Explain the Python-first core (packages/skillforge-core/adaptingtripleyak/SkillForge's Python 3.8+ modules: frontmatter.py, triage_skill_request.py, validate_skill.py, run_skill_evals.py, skillforge_doctor.py, compile_skill.py, mine_skill_friction.py) so the user can easily test and extend it with Python, plus the MCP stdio server wrapper and Property-Based Testing (hypothesisfor Python /fast-check if TS frontend). *   Detail both applications: *   **App 1 (apps/app1-cloud-compliance):** Cloud Security & IaC Compliance Auditor (Python CLI + AWS CDK/Terraform scanning + CIS/Well-Architected skill compilation + PreToolUse safety gating). Fits the user's Cloud Engineer background! *   **App 2 (apps/app2-spooky-game-engine):** Interactive Gothic Narrative & Diagnostics Engine (Web UI + atmospheric spooky theme + Python FastAPI/MCP backend compiling narrative skills and running regression evals on story logic). Also appeals to Design & Costume-style polish! *   **4. Ready-to-Use .kiro/Workspace Files (Copy & Paste)** *   Include complete, valid configurations updated to match Kiro's exact v1 schemas (,,,): *  .kiro/specs/core-skillforge-engine/requirements.md(EARS notation) *  .kiro/specs/core-skillforge-engine/design.md*  .kiro/specs/core-skillforge-engine/tasks.md*  .kiro/steering/core-conventions.md (inclusion: always) *   .kiro/steering/skill-engineering.md (inclusion: auto) *   .kiro/hooks/eval-on-save.json (PostFileSave) *   .kiro/hooks/pre-tool-security-gate.json (PreToolUse, using tool_name/tool_inputper) *  .kiro/hooks/session-start-context.json (SessionStart— works in IDE, CLI V3, and Web, replacingAgentSpawnwhich is CLI-only!) *  .kiro/settings/mcp.json(withskillforge-core-engineandsequential-thinking, noting Kiro's full path/env rules from [cite: 12],) *   **5. Step-by-Step "Day 1 to Demo Day" Build Playbook** *   Step 1: Claim credits & initialize GitHub repo (public, MIT License, verify .gitignoredoes NOT ignore.kiro/). *   Step 2: Seed .kiro/files and run "Generate Steering Docs" / open Spec panel in Kiro IDE (,,). *   Step 3: Buildskillforge-core via Kiro's Spec task runner (Design-First or Requirements-First workflow, executing tasks sequentially or in parallel waves,). *   Step 4: Build App 1 (app1-cloud-compliance) and App 2 (app2-spooky-game-engine) using #speccontext tags ([cite: 15]). *   Step 5: Verify Hooks & MCP (Remember the gotcha:PostFileSave/File Savehooks fire ONLY on agent edits, not manual human file saves ,, and checkView → Output → "Kiro - MCP Logs"[cite: 13]). *   Step 6: Record the <3-minute YouTube Demo & complete Devpost write-up (covering all 8 Kiro usage prompts,). *   **6. Final Pre-Submission Verification Checklist & Video Script** 5.  **Check Constraints & Formatting Guidelines**: *   Notags! (Mode 2: Simple Q&A). *   No internal language ("research material", "snippets", "report tags"). *   Strict citation format[cite: source_id] at the end of sentences containing information from the sources. Wait: make sure NOT to put citations inside fenced code blocks ( ... )! Very important rule: "NEVER place citations inside fenced code blocks (```...```); citations must only appear in regular prose outside of code blocks." *   Table formatting: single spaces between cell content and pipe (|) separators. Do not pretty-print tables. (e.g., | Column 1 | Column 2 |`).*   LaTeX formatting: No complex math needed here; do not use LaTeX for simple numbers, ranges, currency, or tables.*   Safety: No personal medical advice, no weapons/drugs/circumvention. Note: App 1 is Cloud Compliance, App 2 is a Spooky Game Engine. Totally safe.*   Remember: Do NOT attach "Would you like me to do a more in-depth research instead and propose a research plan?" because this is directly elaborating/synthesizing what was already discussed and researched.Double-check Citations to Use:: Dec 4, 2026 @ 2:00pm PST deadline.: Judging criteria (5x 20% = 10 pts each), 3-min YouTube video, 8 Kiro write-up questions (IDE/CLI/Web/Crew, custom agents, hooks, spec-driven vs vibe coding, steering, MCP, PBT, Kiro powers), no extensions.: 4 tracks, Skeleton Crew = skeleton template + 2 distinct apps in 2 separate folders, public GitHub (not GitLab/BitBucket), OSI license visible in About, /.kiro at root and not in .gitignore, Bonus prizes (Best Kiro Crew App, Best Demo, Social Blitz #KiroweenHackathon26, Bonus Blog Prize).: Submission window Oct 30 – Dec 4, 2026, max 3 team members, prize amounts ($30k/$20k/$10k overall, $5k category, $1k Best Kiro Crew App, $1k Best Demo, 2,000 bonus credits blog, 3-mo Pro+ social blitz).,,,: Hooks JSON schema (v1, hooks, trigger, matcher, action, timeout, enabled, PostFileSave).,,: Getting started with Kiro (Kiro Ghost icon, Generate Steering Docs, EARS notation, requirements.md/design.md/tasks.md, Quick Spec vs Feature Spec, parallel wave execution, #spec context key).[cite: 16],,: Spec-driven development vs vibe coding, AWS Bedrock, steering files.[cite: 9],,,,: tripleyak/SkillForge architecture, 4-phase architecture, Context Skill Advisor, Python 3.8+ scripts (frontmatter.py, discover_skills.py, triage_skill_request.py, validate_skill.py, run_skill_evals.py, skillforge_doctor.py, init_skill.py, compile_skill.py, package_skill.py, mine_skill_friction.py, install_skillforge.py).[cite: 12],: MCP configuration (.kiro/settings/mcp.json, ${VAR}, full paths / env.PATH, View -> Output -> "Kiro - MCP Logs").[cite: 22],: Steering inclusion modes (always, auto, fileMatch, manual), YAML frontmatter at very top of file.,: Exact trigger names (PromptSubmit, AgentStop, SessionStart, PreToolUse, PostToolUse, File Save, PreTaskExecution, PostTaskExecution), PreToolUse JSON payload (hook_event_name, cwd, session_id, tool_name, tool_input), agent-only file trigger gotcha (only fires on agent edits, not human saves).,: Active Kiro models (Claude Sonnet 5.5 1.3x 1M >30% faster, Claude Sonnet 5 spec-driven, Claude Opus 5.5 2.0x 1M, GPT-5.6 Luna 0.6x/1.2x 1M 74.6 Coding Agent Index, GPT-5.6 Terra 2.2x/4.4x, MiniMax M2.5 0.25x, GLM-5 0.5x 200K, Qwen3 Coder Next 0.05x 256K).[cite: 23],: User's profile (GibzB, Billy G., Python & AWS).Formatting Check for Code Blocks Inside a Markdown Document:Since the user wants a comprehensive markdown document they can save directly (e.g., BUILD_GUIDE.md), if I wrap the entire thing in one giant ```markdown fence, then inner ```json or ```bash code blocks would break unless I use 4-backtick fences (markdown ... ) OR simply present the document directly in the response with clean headers and standard 3-backtick inner code blocks. Presenting it directly with a clear divider or 4-backtick outer fence? Actually, if I put citations inside a 4-backtick fenced block, that would violate: "NEVER place citations inside fenced code blocks (```...```); citations must only appear in regular prose outside of code blocks."Therefore, I MUST present the document as regular formatted Markdown prose/headers/tables/inner code blocks (NOT wrapped in one giant outer code block), so that all [cite: ...] tags sit properly in regular prose outside of fenced code blocks! That way it renders beautifully in chat AND the user can copy-paste it cleanly.Drafting the Content Thoroughly:Make sure every table uses single spaces around pipes (| Col1 | Col2 |).Make sure no citations appear inside code blocks or tables? Wait: can citations appear in tables? Let's check the rules: "NEVER place citations inside fenced code blocks (```...```); citations must only appear in regular prose outside of code blocks." Putting citations at the end of prose sentences (and keeping tables clean or putting citations in the text introducing the table) is super clean and avoids any ambiguity. Let's keep citations in prose sentences!Include concrete Python + Kiro implementation details tailored to the user's background (Cloud Engineer, Python-friendly, vibecoding with Kiro's spec workflow).Ensure the hook JSON files use the exact v1 schema (version: "v1", hooks: [...], trigger, matcher, action: { type, command/prompt }) and valid triggers (SessionStart instead of CLI-only AgentSpawn for IDE compatibility, PostFileSave, PreToolUse).Explain how pre-tool-security-gate.json reads tool_input from STDIN and uses exit code 2 (or 1? Wait: in Kiro Crew exit 2 denies PreToolUse; in Kiro IDE/CLI, any non-zero exit code for Shell Command actions sends STDERR to the agent and blocks PreToolUse tool invocation! Exit code 2 works cleanly as non-zero across both).Include an explicit "First 60 Minutes in Kiro IDE" actionable walkthrough so "once we get to build, it will be an easy feat."Review against all rules:Mode 2 (Simple Q&A): plain text (rendered Markdown), no <report> tags, no research offer at the end.No internal language ("snippets", "research material", "report tags").Citations strictly [cite: source_id], only outside fenced code blocks.Tables use single spaces (| A | B |), not pretty-printed with extra padding.Time/location awareness: Today is Nov 19, 2026 (EAT). The credits deadline is Dec 1, 2026 (12:00 PM PT), and the hackathon submission deadline is Dec 4, 2026 (2:00 PM PST) — ~15 days left to build! That gives great urgency and realism to the Day-by-Day sprint plan (Nov 19 – Dec 4).Let's write out the comprehensive, detailed response clearly and concisely without fluff, packed with actionable engineering details.Below is your complete, consolidated Master Blueprint & Build Playbook (KIRO_SKILLFORGE_BLUEPRINT.md). You can save this directly into the root of your project repository as a reference guide while building inside Kiro IDE.Kiro-SkillForge: Master Blueprint & Build Playbook (Kiroween 2026)1. Hackathon Identity & Strategic PositioningHackathon: Kiroween 2026 (https://kiroween.devpost.com/)Primary Track: Skeleton Crew ($5,000 Category Prize)Builder Profile: Cloud Engineer (AWS & Python focus), leveraging Kiro's Spec-Driven Development and AI-assisted workflows.Kiro User ID: d-9067642ac7.649834d8-d081-70cb-1dec-8857d5478ad4Key Deadlines (Current Date: November 19, 2026):Free Credits Form (4,000 Kiro Credits / Pro+ Tier): December 1, 2026 @ 12:00 PM PT (submitted via https://kiroween.devpost.com/resources)Final Project Submission: Friday, December 4, 2026 @ 2:00 PM PST (5:00 PM EST / Dec 5 @ 1:00 AM EAT) — no late extensions granted.Judging Period: December 16, 2026 – January 29, 2027.Submitted Project PitchI am building Kiro-SkillForge for the Skeleton Crew track, an autonomous AI skill compiler and governance platform featuring cloud compliance auditing and an interactive gothic game engine. It uses a structured 4-phase pipeline (Synthesis, PBT, Diagnostics, MCP) to automate rigorous spec-driven development and workspace verification.Prize Stacking StrategyYour submission is structured to compete across multiple awards simultaneously without diluting focus:Prize TierAward ValueQualification RequirementOverall Prizes (1st / 2nd / 3rd)$30,000 / $20,000 / $10,000Highest composite score across the 5 judging criteria (20% each).Category: Best Skeleton Crew$5,000Lean core template + 2 distinct apps in 2 separate folders inside your GitHub repo.Bonus: Best Kiro Crew App$1,000Include a functional Kiro Crew configuration/app with public GitHub repo URL and feature description.Bonus: Best Demo$1,000Considered automatically for all eligible submissions with a strong <3-minute YouTube demo.Bonus Blog Prize2,000 Kiro creditsPublish a public third-party blog post (e.g., Medium/Dev.to) during the window mentioning Kiroween 2026.Social Blitz Prize3-month Kiro Pro+Public social post starting with #KiroweenHackathon26 sharing how Kiro changed your workflow.2. Optimal Kiro Model Strategy (Fast & Rigorous)Because you are working in a 2-week sprint and relying on Kiro to write most of the boilerplate and application code, matching the right active Kiro model to each phase keeps both speed and code quality high while stretching your 4,000 credits:Build PhaseRecommended Kiro ModelCredit MultiplierWhy This Model FitsSpecs, Architecture & Core EngineClaude Sonnet 5 or Claude Sonnet 5.51.3x (Sonnet 5.5)Built specifically for spec-driven workflows, multi-step agentic tasks, and >30% faster output with a 1M token context window.Complex Debugging / RefactorsClaude Opus 5.52.0xExcels at sustained multi-file work, architectural decisions, and self-verification when a hook or test gets stuck.High-Speed Task ExecutionGPT-5.6 Luna0.6x (up to 272K)Scores 74.6 on the Coding Agent Index; fastest low-cost tier for executing well-defined tasks.md items.Long CLI / Boilerplate LoopsMiniMax M2.5 or Qwen3 Coder Next0.25x / 0.05xUltra-low credit cost for repetitive unit tests, CLI scaffolding, or extended Kiro CLI sessions with strong error recovery.Rule of Thumb: Use Claude Sonnet 5.5 to generate and refine your requirements.md, design.md, and tasks.md specs, then switch to GPT-5.6 Luna (or MiniMax M2.5) when clicking Run all Tasks to execute implementation steps rapidly.3. Core Architecture: Merging GibzB/skillforge & tripleyak/SkillForgeTo maximize your strength as a Python Cloud Engineer and minimize language-switching friction, the Skeleton Core (packages/skillforge-core) should be Python 3.10+ native, directly adapting the battle-tested standard-library scripts from tripleyak/SkillForge alongside your prompt/workflow improvements from GibzB/skillforge.The 4-Phase Kiro-SkillForge PipelinePhase 1 — Synthesis (triage + init + schema): Routes user requests (USE, IMPROVE, CREATE, COMPOSE, CLARIFY) and converts natural-language prompts into structured SKILL.md specs and Draft-07 JSON Schemas.Phase 2 — Evidence-Driven Evaluation & PBT (validate + evals): Enforces structural linting (word limits, frontmatter integrity via frontmatter.py) and runs automated Property-Based Testing (using Python hypothesis or randomized input generators) plus baseline regression checks (run_skill_evals.py).Phase 3 — Ecosystem Diagnostics (doctor + friction): Scans active .kiro/ directories, steering files, and MCP registries via skillforge_doctor.py to detect tool name collisions, stale references, budget violations, and missing environment variables.Phase 4 — Cross-Runtime Compilation (compile + mcp): Transpiles verified skill definitions via compile_skill.py into native Model Context Protocol (MCP) stdio servers, Kiro Agent Hooks, and Kiro Steering documents.Skeleton Crew Monorepo StructureUnder Kiroween rules, Skeleton Crew projects must keep the core lean and include two separate application folders demonstrating versatility:Plaintextkiro-skillforge/
├── .kiro/                                 # MANDATORY at root; NEVER add to .gitignore
│   ├── hooks/
│   │   ├── eval-on-save.json              # PostFileSave: runs Python unit & PBT tests
│   │   ├── pre-tool-security-gate.json    # PreToolUse: blocks destructive shell/AWS ops
│   │   └── session-start-context.json     # SessionStart: injects SkillForge architecture context
│   ├── settings/
│   │   └── mcp.json                       # Registers local skillforge-core MCP stdio server
│   ├── specs/
│   │   └── core-skillforge-engine/
│   │       ├── requirements.md            # EARS-formatted system requirements
│   │       ├── design.md                  # System architecture & data schemas
│   │       └── tasks.md                   # Trackable implementation checklist
│   └── steering/
│       ├── core-conventions.md            # inclusion: always (Python/UI standards & rules)
│       ├── skill-engineering.md           # inclusion: auto (4-phase SkillForge pipeline rules)
│       └── security-guardrails.md         # inclusion: auto (AWS Secrets/IAM & zero-trust rules)
├── packages/
│   └── skillforge-core/                   # SHARED SKELETON CORE (Python 3.10+)
│       ├── skillforge/
│       │   ├── frontmatter.py             # Typed YAML frontmatter parser
│       │   ├── triage.py                  # Request router (USE/IMPROVE/CREATE/COMPOSE/CLARIFY)
│       │   ├── validate.py                # Structural linter & schema validator
│       │   ├── evals.py                   # Regression & Hypothesis PBT runner
│       │   ├── doctor.py                  # Ecosystem & .kiro/ health analyzer
│       │   ├── compiler.py                # Transpiles skills -> MCP tools / Kiro Hooks
│       │   └── mcp_server.py              # Python stdio MCP server exposing core tools to Kiro
│       └── tests/
│           └── test_pbt_schemas.py        # Property-based tests using Python hypothesis
├── apps/
│   ├── app1-cloud-compliance/             # APPLICATION 1: Enterprise Cloud Compliance Auditor
│   │   ├── README.md
│   │   ├── cli.py                         # Python CLI scanning Terraform/CDK via SkillForge
│   │   ├── skills/                        # Compiled AWS CIS & Well-Architected audit skills
│   │   └── samples/                       # Sample insecure vs. compliant IaC files for demo
│   └── app2-spooky-game-engine/           # APPLICATION 2: Gothic Narrative & AST Graveyard UI
│       ├── README.md
│       ├── server.py                      # Lightweight Python FastAPI/HTTP backend using core
│       ├── skills/                        # Compiled horror-story & puzzle-logic skills
│       └── web/                           # Dark-mode gothic HTML/JS/Tailwind/WebGL UI
├── LICENSE                                # OSI-approved MIT License (must be visible on GitHub)
└── README.md                              # Setup, architecture diagram, and usage guide
Why These Two Applications Win Skeleton Crewapps/app1-cloud-compliance (Enterprise / Serious Cloud Ops): Directly leverages your AWS & Cloud Engineering background. It compiles AWS security rules into verified skills, audits sample Terraform/CDK templates for open S3 buckets or wildcard IAM roles, and pairs with Kiro's PreToolUse hook to block unsafe AWS CLI mutations (aws s3 rm, terraform destroy) before they run.apps/app2-spooky-game-engine (Creative / Halloween Aesthetic): Proves the exact same skillforge-core engine works for entertainment. It compiles branching gothic horror narrative skills, validates story state invariants with evals.py (ensuring players can't hit dead-end state bugs), and presents a polished, spooky dark-mode web interface—scoring high on Design, Innovation, and the Kiroween theme.4. Ready-to-Use .kiro/ Blueprint FilesCreate these exact files inside your .kiro/ folder before asking Kiro to write application code. This ensures Kiro generates clean, spec-aligned code from turn one.4.1 .kiro/specs/core-skillforge-engine/requirements.mdMarkdown# Requirements Document: Kiro-SkillForge Core Engine

## Introduction
Kiro-SkillForge is a modular Python skeleton framework that turns natural language requests into validated, property-tested AI skills and compiles them into Model Context Protocol (MCP) tools and Kiro Agent Hooks.

## Requirements (EARS Notation)

### Requirement 1: Skill Synthesis & Triage
1.1 WHEN a user submits a skill creation or enhancement request, THE Triage Router SHALL classify the intent into one of `USE`, `IMPROVE`, `CREATE`, `COMPOSE`, or `CLARIFY`.
1.2 WHEN a new skill is initialized, THE Synthesis Engine SHALL generate a `SKILL.md` file containing valid YAML frontmatter and a Draft-07 JSON Schema for tool parameters.

### Requirement 2: Structural Validation & Property-Based Testing
2.1 WHEN a skill directory is validated, THE Validator SHALL enforce frontmatter schema integrity, trigger-only descriptions, and a body limit under 1,500 words.
2.2 WHILE running the evaluation harness, THE PBT Runner SHALL test skill parameter schemas against at least 50 randomized boundary inputs using Hypothesis and fail on unhandled type or constraint exceptions.

### Requirement 3: Ecosystem Diagnostics (Doctor)
3.1 WHEN the Ecosystem Doctor executes on a workspace, THE Doctor SHALL scan `.kiro/hooks/`, `.kiro/steering/`, `.kiro/settings/mcp.json`, and skill registries to detect duplicate tool names, invalid JSON, and unresolved environment variable references.

### Requirement 4: Cross-Runtime MCP Compilation
4.1 WHEN a verified skill passes validation and regression evals, THE Compiler SHALL output a runnable Python stdio MCP server definition compatible with `.kiro/settings/mcp.json`.

### Requirement 5: Dual Reference Applications
5.1 THE Repository SHALL provide `apps/app1-cloud-compliance` importing `skillforge-core` to audit IaC templates against AWS security rules.
5.2 THE Repository SHALL provide `apps/app2-spooky-game-engine` importing `skillforge-core` to synthesize and validate branching gothic narratives served via a dark-mode Web UI.
4.2 .kiro/specs/core-skillforge-engine/design.mdMarkdown# System Design Document: Kiro-SkillForge Core Engine

## 1. Architecture Overview
`packages/skillforge-core` is implemented in Python 3.10+ using standard library modules (`json`, `re`, `pathlib`, `subprocess`, `sys`) with optional `PyYAML` and `hypothesis` for PBT. It exposes both a Python library API (imported by App 1 and App 2) and a stdio MCP server (`mcp_server.py`) consumed directly by Kiro IDE/CLI.

+-------------------------------------------------------------------+

| AWS Kiro IDE / CLI / Crew |
| Specs (.kiro/specs) | Steering (.kiro/steering) | Hooks |
+-------------------------------------------------------------------+
|
                         MCP (stdio) & CLI
                                  v
+-------------------------------------------------------------------+

| packages/skillforge-core (Python Skeleton Core) |
| [triage.py] -> [validate.py] -> [evals.py (PBT)] -> [doctor.py] |
| | |
| [compiler.py] |
+-------------------------------------------------------------------+

| |
     imports core  v                 imports core  v
+---------------------------------+ +-------------------------------+

| apps/app1-cloud-compliance | | apps/app2-spooky-game-engine |
| Python IaC Scanner CLI | | FastAPI + Gothic WebGL/UI App |
+---------------------------------+ +-------------------------------+

## 2. Core Data Schema (`SkillDefinition`)
Every compiled skill conforms to the following JSON structure:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SkillDefinition",
  "type": "object",
  "properties": {
    "id": { "type": "string", "pattern": "^[a-z0-9-]+$" },
    "name": { "type": "string" },
    "description": { "type": "string" },
    "parameters": { "type": "object" },
    "eval_cases": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "input": { "type": "object" },
          "expected_keys": { "type": "array", "items": { "type": "string" } }
        },
        "required": ["input", "expected_keys"]
      }
    }
  },
  "required": ["id", "name", "description", "parameters"]
}
3. Application DesignsApp 1 (app1-cloud-compliance): Reads Terraform (.tf) or AWS CloudFormation/CDK JSON/YAML files, invokes compiled compliance skills (check_s3_public_access, check_iam_wildcards), and outputs a structured risk report with remediation snippets.App 2 (app2-spooky-game-engine): Loads compiled gothic story-node skills (generate_haunted_encounter, resolve_curse_puzzle), runs state-invariant evals via evals.py, and serves an interactive atmospheric dark-mode web interface (web/index.html) over a lightweight Python API (server.py).
### 4.3 `.kiro/specs/core-skillforge-engine/tasks.md`

```markdown
# Implementation Plan: Kiro-SkillForge

- [ ] 1. Initialize Skeleton Monorepo & Compliance Setup
  - [ ] 1.1 Create directory layout (`packages/skillforge-core`, `apps/app1-cloud-compliance`, `apps/app2-spooky-game-engine`)
  - [ ] 1.2 Add `pyproject.toml`, `requirements.txt` (`pyyaml`, `hypothesis`, `pytest`, `fastapi`, `uvicorn`, `mcp`), and MIT `LICENSE`
  - [ ] 1.3 Ensure `.gitignore` excludes `.venv/` and `__pycache__/` but NEVER ignores `.kiro/`

- [ ] 2. Build `packages/skillforge-core` (4-Phase Python Engine)
  - [ ] 2.1 Implement `frontmatter.py` and `triage.py` (intent classification & scaffolding)
  - [ ] 2.2 Implement `validate.py` (structural linting & JSON Schema validation)
  - [ ] 2.3 Implement `evals.py` and `tests/test_pbt_schemas.py` using `hypothesis` for Property-Based Testing
  - [ ] 2.4 Implement `doctor.py` (workspace `.kiro/` & skill registry health checks)
  - [ ] 2.5 Implement `compiler.py` and `mcp_server.py` (stdio MCP server exposing `triage_request`, `validate_skill`, `run_doctor`, `compile_skill`)

- [ ] 3. Build Application 1: Enterprise Cloud Compliance Auditor
  - [ ] 3.1 Create sample IaC files (`samples/insecure_infra.tf`, `samples/secure_infra.tf`)
  - [ ] 3.2 Author compliance skills (`s3-audit`, `iam-least-privilege`) and validate them with `skillforge-core`
  - [ ] 3.3 Build `apps/app1-cloud-compliance/cli.py` outputting colorized terminal audit reports and remediation advice

- [ ] 4. Build Application 2: Spooky Gothic Narrative Engine
  - [ ] 4.1 Author gothic story skills (`haunted-encounter`, `crypt-riddle`) and write PBT state-transition evals
  - [ ] 4.2 Build `apps/app2-spooky-game-engine/server.py` exposing narrative endpoints powered by `skillforge-core`
  - [ ] 4.3 Build `apps/app2-spooky-game-engine/web/index.html` with dark gothic styling, fog/ember canvas effects, and interactive choices

- [ ] 5. Final Verification & Kiro Governance
  - [ ] 5.1 Run `skillforge-core` doctor across the entire monorepo and resolve any warnings
  - [ ] 5.2 Test all `.kiro/hooks/` triggers (`PostFileSave`, `PreToolUse`, `SessionStart`) live in Kiro IDE
  - [ ] 5.3 Update root `README.md` with setup commands and architecture overview
4.4 Steering Files (.kiro/steering/)Create .kiro/steering/core-conventions.md (inclusion: always ensures these rules apply to every chat turn):Markdown---
inclusion: always
---

# Kiro-SkillForge Core Conventions

- **Python Standard:** Target Python 3.10+. Use type hints (`typing` / PEP 585), `pathlib.Path`, and clean docstrings on all public functions.
- **Monorepo Boundaries:** `packages/skillforge-core` must NEVER import code from `apps/`. Both `apps/app1-cloud-compliance` and `apps/app2-spooky-game-engine` must import from `skillforge-core`.
- **Spec Traceability:** Update task checkboxes in `.kiro/specs/core-skillforge-engine/tasks.md` as work completes.
- **Security:** Never hardcode AWS keys, API tokens, or secrets. Always reference environment variables.
Create .kiro/steering/skill-engineering.md (inclusion: auto loads automatically when your prompt discusses skills, schemas, or evals):Markdown---
inclusion: auto
description: Enforces the 4-phase SkillForge pipeline (Synthesis, PBT Evals, Doctor Diagnostics, MCP Compilation) when designing or modifying skills.
---

# Skill Engineering Standards

1. Every skill MUST include a `SKILL.md` with YAML frontmatter (`name`, `description`) under 1,500 words and a JSON Schema defining input parameters.
2. Every new skill or schema change MUST include at least one `hypothesis` property-based test verifying invalid/boundary inputs fail gracefully.
3. Run `python3 -m skillforge.doctor` after adding or modifying skills to verify no tool name collisions exist.
4.5 Agent Hooks (.kiro/hooks/)Note Kiro's exact v1 JSON schema and surface behavior:Use SessionStart (supported in IDE, CLI V3, and Web) instead of AgentSpawn (which is CLI-only).Remember that PostFileSave / File Save hooks fire only when the Kiro agent modifies/saves a file, not when you press Ctrl+S manually..kiro/hooks/eval-on-save.json (Runs pytest/PBT automatically whenever Kiro edits core Python files):JSON{
  "version": "v1",
  "hooks": [
    {
      "name": "skillforge-eval-on-save",
      "description": "Runs pytest and Hypothesis PBT tests whenever the agent saves Python files in skillforge-core.",
      "trigger": "PostFileSave",
      "matcher": "packages/skillforge-core/.*\\.py$",
      "action": {
        "type": "command",
        "command": "python3 -m pytest packages/skillforge-core/tests -q"
      },
      "timeout": 45,
      "enabled": true
    }
  ]
}
.kiro/hooks/pre-tool-security-gate.json (Reads PreToolUse JSON on STDIN and exits with code 2 to block dangerous shell commands):JSON{
  "version": "v1",
  "hooks": [
    {
      "name": "pre-tool-security-gate",
      "description": "Blocks destructive shell or AWS deletion commands before execution.",
      "trigger": "PreToolUse",
      "matcher": "shell",
      "action": {
        "type": "command",
        "command": "python3 -c 'import sys, json; ctx = json.load(sys.stdin); cmd = str(ctx.get(\"tool_input\", {})); blocked = [\"rm -rf /\", \"aws s3 rm\", \"terraform destroy\", \"DROP TABLE\"]; hits = [b for b in blocked if b in cmd]; sys.stderr.write(f\"BLOCKED BY SECURITY GATE: {hits}\\n\") if hits else None; sys.exit(2 if hits else 0)'"
      },
      "timeout": 10,
      "enabled": true
    }
  ]
}
.kiro/hooks/session-start-context.json (Injects project workflow instructions at session start):JSON{
  "version": "v1",
  "hooks": [
    {
      "name": "session-start-context",
      "description": "Reminds the agent of the Skeleton Crew monorepo layout and spec-driven rules on session start.",
      "trigger": "SessionStart",
      "action": {
        "type": "agent",
        "prompt": "You are working in the Kiro-SkillForge Skeleton Crew monorepo. Keep packages/skillforge-core decoupled from apps/, follow .kiro/specs/core-skillforge-engine/, and verify tests pass after changes."
      },
      "enabled": true
    }
  ]
}
4.6 Workspace MCP Configuration (.kiro/settings/mcp.json)Because Kiro does not inherit your shell PATH automatically, use absolute paths (or ${WORKSPACE_ROOT} / virtual environment python binary paths) if python3 or npx fails to resolve:JSON{
  "mcpServers": {
    "skillforge-core-engine": {
      "command": "python3",
      "args": [
        "-m",
        "skillforge.mcp_server"
      ],
      "env": {
        "PYTHONPATH": "${WORKSPACE_ROOT}/packages/skillforge-core",
        "SKILLFORGE_LOG_LEVEL": "INFO"
      },
      "disabled": false
    },
    "sequential-thinking": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sequential-thinking"
      ],
      "disabled": false
    }
  }
}
(Tip: If skillforge-core-engine shows an error in the Kiro Ghost panel before you build mcp_server.py, set "disabled": true initially, then flip it to false once Task 2.5 is complete!)5. Step-by-Step Build Playbook (Nov 19 – Dec 4)Step 0: Immediate Setup (First 60 Minutes)Claim Credits: Submit the Resource Request Form at https://kiroween.devpost.com/resources with your Kiro ID (d-9067642ac7.649834d8-d081-70cb-1dec-8857d5478ad4) before Dec 1 @ 12:00 PM PT.Create Public GitHub Repo: Initialize kiro-skillforge on GitHub (GitLab/BitBucket are ineligible) with an MIT License selected during repo creation so GitHub displays it in the top "About" section.Seed .kiro/ First: Clone the repo locally, create the .kiro/ folders and paste the files from Section 4 above, and add a .gitignore containing .venv/, __pycache__/, .pytest_cache/, and node_modules/ (verify .kiro/ is NOT in .gitignore).Clone Reference Inspiration: In a separate temporary folder outside your project (e.g., /tmp/ref-skillforge), clone https://github.com/tripleyak/SkillForge and your https://github.com/GibzB/skillforge so you can reference or feed specific Python modules into Kiro chat.Open in Kiro IDE: Run kiro . from your repo root, click the Kiro Ghost icon in the left sidebar, and verify your Specs, Steering files, and Hooks appear in the Kiro panel.Step 1: Build packages/skillforge-core (Nov 19 – Nov 23)Select Claude Sonnet 5.5 (or Claude Sonnet 5) in Kiro chat.Type #spec in chat and select core-skillforge-engine so Kiro loads requirements.md, design.md, and tasks.md automatically.Execute Tasks 1.1 through 2.5 from tasks.md using Kiro's task runner.Ask Kiro to adapt the Python logic from tripleyak/SkillForge's frontmatter.py, triage_skill_request.py, validate_skill.py, run_skill_evals.py, skillforge_doctor.py, and compile_skill.py cleanly into packages/skillforge-core/skillforge/.Enable "disabled": false in .kiro/settings/mcp.json and check View → Output → "Kiro - MCP Logs" to confirm your skillforge-core-engine MCP server connects cleanly.Step 2: Build Application 1 — Cloud Compliance Auditor (Nov 24 – Nov 27)Switch to GPT-5.6 Luna for fast task execution.Execute Tasks 3.1 – 3.3 in apps/app1-cloud-compliance/:Have Kiro create realistic insecure Terraform/CloudFormation samples (public S3 ACL, 0.0.0.0/0 SSH security group, * IAM policy).Build cli.py so running python3 apps/app1-cloud-compliance/cli.py scan samples/ uses skillforge-core to run compiled audit skills and print a clean terminal report with severity scores and fix suggestions.Test the Security Hook Live: Ask Kiro in chat to run a harmless dry-run command containing aws s3 rm to verify pre-tool-security-gate.json intercepts and blocks it!Step 3: Build Application 2 — Spooky Gothic Narrative Engine (Nov 28 – Nov 30)Execute Tasks 4.1 – 4.3 in apps/app2-spooky-game-engine/:Create 2 compiled narrative skills (haunted-encounter, crypt-riddle) validated by evals.py (proving no unreachable story branches).Build a fast Python backend (server.py using FastAPI or http.server) plus a single-page dark-mode gothic UI (web/index.html) with flickering candle/fog CSS animations, spooky typography, and interactive choices powered by skillforge-core.Bonus Polish: Add a live "SkillForge Diagnostics Drawer" in the web UI showing the real-time doctor.py and PBT eval pass status of the active story skills.Step 4: Polish, Blog/Social Bonus & Demo Video (Dec 1 – Dec 3)Publish Bonus Content:Write a short technical post on Medium/Dev.to explaining how you built Kiro-SkillForge for Kiroween 2026 (qualifies for Bonus Blog Prize — 2,000 Kiro credits).Post on X/LinkedIn starting with #KiroweenHackathon26 sharing your favorite Kiro feature (qualifies for Social Blitz Prize — 3-month Kiro Pro+).Record the Demo Video (< 3 Minutes, Public on YouTube):0:00 – 0:30 (The Hook & Skeleton Concept): Show the GitHub repo layout (/.kiro, packages/skillforge-core, apps/app1..., apps/app2...) and explain why AI skills need spec-driven testing and governance.0:30 – 1:15 (Kiro Workflow Live): Open .kiro/specs/, edit a core Python file via Kiro agent to show eval-on-save.json (PostFileSave) running Hypothesis PBT tests automatically, and trigger pre-tool-security-gate.json (PreToolUse) blocking a dangerous command.1:15 – 2:00 (App 1 Live Demo): Run the Cloud Compliance Auditor CLI against insecure_infra.tf, showing SkillForge catching AWS misconfigurations.2:00 – 2:45 (App 2 Live Demo): Open the Spooky Gothic Narrative Engine in the browser, play through a haunted encounter, and show it running off the same skillforge-core engine.2:45 – 3:00 (Wrap-up): Show doctor.py passing 100% and recap impact.Step 5: Final Pre-Submission Audit (Dec 4, Before 2:00 PM PST)[ ] Public GitHub repository URL works in an incognito browser (not GitLab/BitBucket).[ ] MIT LICENSE is visible in GitHub's "About" sidebar.[ ] /.kiro/ (with specs/, hooks/, steering/, settings/mcp.json) is pushed and visible at the repository root.[ ] Both apps/app1-cloud-compliance/ and apps/app2-spooky-game-engine/ reside in separate folders and run cleanly from fresh setup instructions in README.md.[ ] YouTube demo video is Public, under 3:00, and free of copyrighted music/trademarks.[ ] Devpost form answers all 8 Kiro usage write-up prompts (IDE/CLI/Web/Crew, Custom Agents, Hooks, Spec-Driven vs Vibe Coding, Steering Docs, MCP, PBT, Kiro Powers) plus links to your Social Blitz post and Bonus Blog post.