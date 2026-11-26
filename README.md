# Kiro-SkillForge

> Autonomous AI skill compiler, spec-driven evaluation harness, and governance platform for AWS Kiro developers.

## Overview

Kiro-SkillForge transforms unstructured vibe coding into rigorous, evidence-backed skill engineering. It automates the entire lifecycle from requirement synthesis to cross-runtime compilation while maintaining audit trails and enforcing security guardrails.

## 4-Phase Pipeline

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  SYNTHESIS   │──▶│     PBT      │──▶│ DIAGNOSTICS  │──▶│     MCP      │
│              │   │              │   │              │   │ COMPILATION  │
│ Parse specs  │   │ Property-    │   │ Performance  │   │ Generate     │
│ Generate AST │   │ based tests  │   │ analysis     │   │ MCP tools    │
│ Create IR    │   │ 100+ inputs  │   │ Health check │   │ Agent hooks  │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

1. **Synthesis Phase**: Transform skill specifications into intermediate representations and executable artifacts
2. **PBT Phase**: Validate skills across hundreds of randomized inputs using property-based testing
3. **Diagnostics Phase**: Analyze performance metrics, code quality, and historical test results
4. **MCP Compilation Phase**: Compile skills to Model Context Protocol tools and Agent Hooks

## Project Structure

```
kiro-skillforge/
├── .kiro/                          # Kiro configuration (MANDATORY - tracked in Git)
│   ├── hooks/                      # Agent event hooks
│   ├── settings/                   # MCP server configuration
│   ├── steering/                   # Persistent context rules
│   └── specs/                      # Spec-driven development files
│
├── packages/
│   └── skillforge-core/           # Core 4-phase pipeline engine
│       └── src/
│           ├── synthesis/         # Phase 1: AST parsing & schema generation
│           ├── evaluation/        # Phase 2: Property-based testing
│           ├── doctor/            # Phase 3: Ecosystem health
│           ├── compiler/          # Phase 4: Cross-runtime compilation
│           ├── triage/            # Request validation
│           ├── validation/        # Skill validation
│           ├── events/            # Event dispatching
│           ├── gatekeeper/        # Adversarial security testing
│           ├── evidence/          # Test evidence recording
│           └── governance/        # Skill lineage & audit
│
├── apps/
│   ├── app1-enterprise-compliance/    # Cloud Compliance Auditor CLI
│   └── app2-spooky-game-engine/       # Gothic Narrative Engine
│
├── scripts/                       # Utility scripts
│   ├── triage_skill_request.py
│   ├── validate_skill.py
│   ├── run_skill_evals.py
│   ├── skillforge_doctor.py
│   ├── compile_skill.py
│   └── mine_skill_friction.py
│
└── docs/                          # Documentation
```

## Prerequisites

- **Node.js**: 20.x or higher (specified in `.nvmrc`)
- **Python**: 3.12 or higher (specified in `.python-version`)
- **npm**: For workspace management

## Quick Start

```bash
# Clone the repository
git clone https://github.com/gibzb/kiro-skillforge.git
cd kiro-skillforge

# Install dependencies
npm install

# Build all packages
npm run build

# Run ecosystem doctor
npm run doctor

# Run tests
npm run test
```

## Core Capabilities

### 1. Synthesis Engine
- AST parsing from Markdown skill prompts
- JSON Schema generation for typed tool inputs
- Automatic documentation and test fixture generation

### 2. Property-Based Testing (PBT)
- `fast-check` integration for 100+ parameter combinations
- Automatic minimal failing example identification
- Regression baseline comparison

### 3. Ecosystem Doctor
- Tool identifier collision detection
- Circular parameter reference warnings
- Missing environment credential alerts

### 4. Cross-Runtime Compiler
- Kiro MCP server configuration
- Kiro Agent Hooks generation
- Standalone Python/TypeScript modules

## Applications

### App 1: Enterprise Cloud Compliance Auditor
Terminal-based CLI tool for IaC scanning and CIS benchmark validation.

```bash
cd apps/app1-enterprise-compliance
npm run start -- --help
```

### App 2: Spooky Gothic Narrative Engine
Interactive web application with branching horror stories and WebGL visualizations.

```bash
cd apps/app2-spooky-game-engine
npm run dev
```

## Development

### Scripts

| Command | Description |
|---------|-------------|
| `npm run build` | Build all workspaces |
| `npm run test` | Run all tests |
| `npm run lint` | Lint all workspaces |
| `npm run typecheck` | TypeScript type checking |
| `npm run doctor` | Run ecosystem health check |

### Spec-Driven Development

All requirements use EARS (Easy Approach to Requirements Syntax) formatting:
- `WHEN <trigger>, THE <system> SHALL <action>`
- `IF <condition>, THEN THE <system> SHALL <action>`

Specs are located in `.kiro/specs/*/`:
- `requirements.md` - EARS-format requirements
- `design.md` - System architecture
- `tasks.md` - Implementation checklist

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
