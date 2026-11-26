---
inclusion: always
description: Technology stack and standards for Kiro-SkillForge
---

# Kiro-SkillForge Technology Stack

## Primary Languages

### Python 3.10+
- **Purpose**: Core skill engineering scripts
- **Key Scripts** (from tripleyak/SkillForge):
  - `triage_skill_request.py` - Request routing (USE/IMPROVE/CREATE/COMPOSE/CLARIFY)
  - `validate_skill.py` - Structural linting (<1,500 word limit enforcement)
  - `run_skill_evals.py` - Regression evaluation execution
  - `skillforge_doctor.py` - Ecosystem health reports
  - `compile_skill.py` - Cross-runtime compilation
  - `mine_skill_friction.py` - Transcript analysis for bottlenecks
  - `context_advisor.py` - Event-driven context suggestions

### TypeScript 5.x
- **Purpose**: Node.js 20+ ES Modules for core engine
- **Configuration**: `strict: true` in all `tsconfig.json`
- **Module System**: ES Modules (ESM)

## Testing Infrastructure

### Property-Based Testing
- **Library**: `fast-check` for generating randomized inputs
- **Coverage**: 100+ parameter combinations per test
- **Strategy**: Boundary testing for schema validation

### Regression Testing
- **Baseline Storage**: Recorded execution baselines
- **Comparison**: Tool response consistency validation

## AWS Kiro Integration

### Model Context Protocol (MCP)
- **Configuration**: `.kiro/settings/mcp.json`
- **Servers**:
  - `skillforge-core-engine` - Core skill tools exposed to Kiro
  - `sequential-thinking` - Multi-step reasoning

### Agent Hooks
- **Location**: `.kiro/hooks/`
- **Types**:
  - `PostFileSave` - Continuous testing on save
  - `PreToolUse` - Security gate before tool execution
  - `AgentSpawn` - Context injection on agent start

### Spec-Driven Development
- **Requirements**: `.kiro/specs/*/requirements.md` (EARS syntax)
- **Design**: `.kiro/specs/*/design.md`
- **Tasks**: `.kiro/specs/*/tasks.md`

## Frontend Stack (app2-spooky-game-engine)

### UI Framework
- **React** with **Tailwind CSS** dark mode
- **WebGL** for atmospheric particle effects
- **Audio API** for immersive sound design

### Build Tools
- **Vite** or **Next.js** for bundling
- **TypeScript** for type safety

## Cloud Infrastructure (app1-enterprise-compliance)

### IaC Scanning
- **AWS CDK** template analysis
- **Terraform** configuration validation
- **CIS Benchmarks** compliance checking

### AWS Integration
- **AWS SDK** for Python (boto3)
- **AWS CLI** for resource operations

## Code Standards

### Immutability
- Prefer pure functions
- Avoid direct state mutation
- Use immutable data structures

### Security
- No hardcoded API keys, tokens, or credentials
- AWS Secrets Manager for sensitive data
- Hook validation for all shell operations

### Documentation
- All requirements use EARS formatting:
  - `WHILE <condition>, THE <system> SHALL <action>`
  - `WHEN <trigger>, THE <system> SHALL <action>`
- Task progress tracked interactively in `tasks.md`
