---
inclusion: always
description: Project structure for Kiro-SkillForge monorepo
---

# Kiro-SkillForge Project Structure

## Monorepo Layout

```
kiro-skillforge/
├── .kiro/                              # Kiro configuration root (MANDATORY - NOT in .gitignore)
│   ├── hooks/                          # Agent event hooks
│   │   ├── eval-on-save.json          # PostFileSave continuous testing
│   │   ├── pre-tool-security-gate.json # PreToolUse security validation
│   │   └── agent-spawn-context.json    # AgentSpawn context injection
│   ├── specs/                          # Spec-driven development files
│   │   └── core-skillforge-engine/
│   │       ├── requirements.md         # EARS-format requirements
│   │       ├── design.md               # System architecture
│   │       └── tasks.md                # Implementation checklist
│   ├── steering/                       # Persistent context rules
│   │   ├── product.md                  # Product overview
│   │   ├── tech.md                     # Technology stack
│   │   └── structure.md                # This file
│   └── settings/
│       └── mcp.json                    # MCP server configuration
│
├── packages/
│   └── skillforge-core/               # Shared core library (Skeleton Crew requirement)
│       ├── src/
│       │   ├── synthesis/             # Phase 1: AST parsing & schema generation
│       │   │   ├── parser.ts
│       │   │   └── schema_generator.ts
│       │   ├── evaluation/            # Phase 2: Property-based testing
│       │   │   ├── pbt_runner.ts
│       │   │   └── regression_checker.ts
│       │   ├── doctor/                # Phase 3: Ecosystem health
│       │   │   └── conflict_analyzer.ts
│       │   ├── compiler/              # Phase 4: Cross-runtime compilation
│       │   │   └── mcp_compiler.ts
│       │   ├── governance/            # Skill lineage & audit
│       │   │   ├── timestamp_recorder.ts
│       │   │   └── version_tracker.ts
│       │   └── mcp-server/            # MCP server entry point
│       │       └── index.ts
│       ├── dist/                      # Compiled output
│       ├── tests/
│       │   ├── pbt/                   # Property-based tests
│       │   └── unit/                  # Unit tests
│       ├── package.json
│       └── tsconfig.json
│
├── apps/
│   ├── app1-enterprise-compliance/    # Application 1: Cloud Compliance Auditor
│   │   ├── src/
│   │   │   ├── cli/                   # CLI interface
│   │   │   ├── scanners/              # IaC template scanners
│   │   │   │   ├── cdk_scanner.py
│   │   │   │   └── terraform_scanner.py
│   │   │   ├── policies/              # Compliance policies
│   │   │   │   └── cis_benchmarks.py
│   │   │   └── hooks/                 # Kiro hook integrations
│   │   │       └── pre_tool_security.py
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   └── README.md
│   │
│   └── app2-spooky-game-engine/       # Application 2: Gothic Narrative Engine
│       ├── src/
│       │   ├── components/            # React components
│       │   │   ├── NarrativeView.tsx
│       │   │   └── ParticleCanvas.tsx
│       │   ├── engine/                # Story generation engine
│       │   │   └── narrative_skill.ts
│       │   ├── hooks/                 # Kiro hook integrations
│       │   │   └── post_file_save.ts
│       │   └── styles/                # Tailwind dark mode
│       │       └── gothic.css
│       ├── public/
│       │   └── audio/                 # Atmospheric sounds
│       ├── package.json
│       └── README.md
│
├── scripts/                           # Utility scripts
│   ├── triage_skill_request.py
│   ├── validate_skill.py
│   ├── run_skill_evals.py
│   ├── skillforge_doctor.py
│   ├── compile_skill.py
│   └── mine_skill_friction.py
│
├── LICENSE                            # MIT License (MANDATORY for Devpost)
├── README.md                          # Project documentation
├── package.json                       # Root package.json (workspaces)
└── tsconfig.json                      # Root TypeScript config
```

## Key Directories

### `.kiro/` - Kiro Configuration
- **MANDATORY**: Must be committed to repo root, NOT in `.gitignore`
- **hooks/**: JSON files defining agent automation triggers
- **specs/**: Requirements, design, and task files for each feature
- **steering/**: Persistent context rules loaded on every session
- **settings/**: MCP server and other Kiro settings

### `packages/skillforge-core/` - Shared Core
- Implements 4-phase pipeline: Synthesis → PBT → Diagnostics → MCP Compilation
- Powers both downstream applications
- Exposes tools via MCP server

### `apps/app1-enterprise-compliance/` - Application 1
- Terminal-based CLI tool
- Cloud compliance auditing
- IaC template scanning

### `apps/app2-spooky-game-engine/` - Application 2
- Web application (React + WebGL)
- Gothic narrative generation
- Atmospheric UI

## Workspace Configuration

### Root `package.json`
```json
{
  "name": "kiro-skillforge",
  "workspaces": [
    "packages/*",
    "apps/*"
  ],
  "private": true
}
```

### MCP Server Configuration (`.kiro/settings/mcp.json`)
```json
{
  "mcpServers": {
    "skillforge-core-engine": {
      "command": "node",
      "args": ["${WORKSPACE_ROOT}/packages/skillforge-core/dist/mcp-server/index.js"],
      "env": {
        "NODE_ENV": "development",
        "SKILLFORGE_LOG_LEVEL": "info"
      },
      "disabled": false
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
      "disabled": false
    }
  }
}
```

## Devpost Submission Requirements

- [x] Public GitHub repository
- [x] OSI-approved open-source license (MIT)
- [x] Root `/.kiro/` directory committed (not in .gitignore)
- [x] Two separate application folders (Skeleton Crew requirement)
- [ ] Demo video under 3 minutes
- [ ] README with setup instructions
