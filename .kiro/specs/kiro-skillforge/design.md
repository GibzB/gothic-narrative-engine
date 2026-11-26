# Design Document: Kiro-SkillForge

## Overview

Kiro-SkillForge is an autonomous AI skill compiler and governance platform for AWS Kiro developers. It implements a 4-phase pipeline (Synthesis, Property-Based Testing, Diagnostics, MCP Compilation) with evidence-driven testing and adversarial gatekeeping. This document outlines the system architecture, component subsystems, data models, and configuration requirements.

*A design is a blueprint that translates requirements into a technical specification, defining how the system will be built to meet all acceptance criteria.*

## Architecture

Kiro-SkillForge is a monorepo-based platform with a shared core framework that powers two distinct application domains.

```
+-------------------------------------------------------------------+
|                  Kiro Workspace / Agent Hooks                     |
|  - FileEdited hooks                                               |
|  - PreToolUse security gates                                      |
|  - PostToolUse execution tracking                                 |
+-------------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------------+
|              packages/skillforge-core (Skeleton Core)             |
|  +-------------------+  +------------------+  +----------------+ |
|  | Synthesis Engine  |  | PBT Eval Harness |  | Ecosystem Doctor| |
|  +-------------------+  +------------------+  +----------------+ |
|                                |                                  |
|                                v                                  |
|                  +-----------------------+                        |
|                  | Cross-Runtime Compiler|                        |
|                  +-----------------------+                        |
+-------------------------------------------------------------------+
                                |
          +---------------------+---------------------+
          |                                           |
          v                                           v
+-----------------------+                   +-----------------------+
|   app1-enterprise-    |                   |  app2-spooky-game-    |
|      compliance       |                   |      engine           |
|  (Cloud Compliance    |                   |  (Interactive Gothic  |
|       Auditor)        |                   |    Narrative)         |
+-----------------------+                   +-----------------------+
```

### The 4-Phase Pipeline

1. **Synthesis Phase**: Transforms skill specifications into intermediate representations and executable artifacts
2. **PBT Phase**: Validates skills across hundreds of randomized inputs using property-based testing
3. **Diagnostics Phase**: Analyzes performance metrics, code quality, and historical test results
4. **MCP Compilation Phase**: Compiles skills to Model Context Protocol tools and Agent Hooks

*For any valid skill request, the pipeline executes phases sequentially: Synthesis → PBT → Diagnostics → MCP Compilation. If any phase fails, the pipeline halts with detailed error information.*

## Components and Interfaces

### Synthesis Engine (`packages/skillforge-core/src/synthesis/`)

The Synthesis Engine parses skill specifications and generates executable artifacts.

**Components**:
- `parser.ts`: Converts Markdown skill prompts into abstract syntax tree (AST) definitions
- `schema_generator.ts`: Builds JSON Schema definitions for tool input validation
- `artifact_generator.ts`: Produces Python and TypeScript executable artifacts

**Key Behaviors**:
- Parse skill specification files with error reporting and line numbers
- Generate intermediate representation files for downstream phases
- Select appropriate generation strategy based on skill type identifier
- Return descriptive error messages for malformed specifications

**PBT Validation**:
- Property: For any valid skill specification, parsing and schema generation produces consistent AST and schema definitions
- Property: For any skill type identifier, the appropriate generation strategy is selected and applied

### Property-Based Testing Harness (`packages/skillforge-core/src/evaluation/`)

The PBT Harness validates skills across a wide range of inputs using property-based testing.

**Components**:
- `pbt_runner.ts`: Integrates `fast-check` for generating 100+ randomized test inputs
- `regression_checker.ts`: Evaluates tool response consistency against stored execution baselines
- `evidence_recorder.ts`: Captures test inputs, outputs, and evidence of correctness

**Key Behaviors**:
- Load property definitions from skill specifications
- Generate random test inputs within defined constraints
- Execute skills with each generated input
- Generate minimal failing examples when property violations are detected
- Record evidence of correctness for passing tests

**PBT Validation**:
- Property: For any property definition and valid inputs, the PBT harness generates 100+ test cases and verifies the property holds
- Property: For any property violation, the harness produces a minimal failing example that demonstrates the bug
- Property: When property-based testing is disabled, the harness skips validation and completes successfully

### Ecosystem Doctor (`packages/skillforge-core/src/doctor/`)

The Ecosystem Doctor diagnoses platform issues and configuration problems.

**Components**:
- `config_validator.ts`: Validates JSON syntax in `.kiro/hooks/` and configuration files
- `health_reporter.ts`: Generates ecosystem health status reports
- `conflict_analyzer.ts`: Scans for identifier collisions, circular parameters, and missing credentials

**Key Behaviors**:
- Check Python and TypeScript environment availability
- Validate installed packages and versions
- Check configuration file syntax and structure
- Provide remediation guidance for identified issues

**PBT Validation**:
- Property: For any workspace configuration, the doctor produces a consistent health report
- Property: For any environment state, the doctor correctly identifies missing components

### Cross-Runtime Compiler (`packages/skillforge-core/src/compiler/`)

The Cross-Runtime Compiler converts skills to Kiro MCP tools and Agent Hooks.

**Components**:
- `mcp_compiler.ts`: Transpiles skill definitions into stdio MCP server entry points
- `hook_compiler.ts`: Generates Kiro Agent Hook definitions from skill specifications
- `runtime_validator.ts`: Validates output formats for all target runtimes

**Key Behaviors**:
- Load intermediate representation from Synthesis phase
- Generate MCP tool definitions in valid JSON schema format
- Generate Agent Hook definitions with proper trigger patterns
- Support cross-runtime compilation for Python and TypeScript
- Attempt rollback on compilation failures

**PBT Validation**:
- Property: For any intermediate representation, compilation produces valid MCP tool definitions and Agent Hook definitions
- Property: For any target runtime configuration, all supported artifacts are generated correctly

### Evidence Recorder (`packages/skillforge-core/src/evidence/`)

The Evidence Recorder captures test results for audit and verification purposes.

**Components**:
- `evidence_store.ts`: Stores test inputs, outputs, and evidence records
- `evidence_retriever.ts`: Provides complete test evidence history on request
- `failure_analyzer.ts`: Analyzes failure patterns and records exploit paths

**Key Behaviors**:
- Capture test inputs and outputs for all test executions
- Store evidence of correctness for passing property tests
- Record failing inputs and expected outputs for test failures
- Log failures without halting execution when storage fails
- Provide complete evidence history on request

**PBT Validation**:
- Property: For any test execution, evidence is captured including inputs, outputs, and pass/fail status
- Property: For any recorded evidence request, the complete history is returned

### Event Dispatcher (`packages/skillforge-core/src/events/`)

The Event Dispatcher manages event hooks for automation.

**Components**:
- `event_registry.ts`: Stores hook definitions for registered events
- `event_dispatcher.ts`: Triggers hooks on phase completion or failure
- `async_queue.ts`: Queues asynchronous hooks for background execution

**Key Behaviors**:
- Trigger hooks on successful phase completion
- Trigger failure hooks on phase failure
- Execute registered hooks in order
- Log hook errors and continue with other hooks
- Queue asynchronous hooks for background execution

**PBT Validation**:
- Property: For any phase completion, the corresponding hooks are triggered
- Property: For any phase failure, failure hooks are triggered and error details are logged
- Property: For any hook execution failure, other hooks continue execution

### Adversarial Gatekeeper (`packages/skillforge-core/src/gatekeeper/`)

The Adversarial Gatekeeper proactively attempts to break skills for security validation.

**Components**:
- `malicious_generator.ts`: Generates malicious inputs designed to exploit vulnerabilities
- `exploit_monitor.ts`: Monitors skill execution foranomalous behavior
- `vulnerability_recorder.ts`: Records exploit paths when vulnerabilities are detected

**Key Behaviors**:
- Generate malicious inputs using known vulnerability patterns
- Attempt to exploit vulnerability patterns during skill execution
- Monitor foranomalous behavior during malicious input execution
- Record exploit paths when vulnerabilities are detected
- Skip vulnerability exploration when adversarial testing is disabled
- Fail the pipeline immediately when critical vulnerabilities are found

**PBT Validation**:
- Property: For any skill specification, the gatekeeper generates malicious inputs and tests for vulnerability patterns
- Property: When adversarial testing is disabled, no vulnerability exploration occurs

### Triage Module (`packages/skillforge-core/src/triage/`)

The Triage Module validates skill requests before processing.

**Components**:
- `format_validator.ts`: Validates request format and structure
- `field_validator.ts`: Validates required fields in skill requests
- `permission_checker.ts`: Checks request source permissions
- `rate_limiter.ts`: Enforces request rate limits when enabled

**Key Behaviors**:
- Validate request format before processing
- Validate required fields are present
- Check request source permissions
- Reject invalid requests with descriptive error codes
- Log security events for permission failures
- Enforce rate limits when enabled

**PBT Validation**:
- Property: For any skill request, triage validates format, required fields, and permissions
- Property: When rate limiting is enabled, requests exceeding limits are rejected

### Validator (`packages/skillforge-core/src/validation/`)

The Validator ensures skills are well-formed before entering the pipeline.

**Components**:
- `spec_parser.ts`: Parses skill specifications
- `syntax_checker.ts`: Checks syntax correctness
- `schema_validator.ts`: Validates against schema definitions
- `semantic_validator.ts`: Checks semantic correctness

**Key Behaviors**:
- Parse skill specifications
- Check syntax correctness
- Validate against schema definitions
- Check semantic correctness
- Return detailed error locations on validation failures
- Apply custom validation rules when present

**PBT Validation**:
- Property: For any skill specification, validation checks syntax, schema, and semantic correctness

### Evaluator (`packages/skillforge-core/src/evaluation/runner.ts`)

The Evaluator executes evaluation suites for skills.

**Components**:
- `suite_loader.ts`: Loads evaluation suites
- `fixture_manager.ts`: Initializes test fixtures
- `test_runner.ts`: Executes test cases in sequence
- `report_generator.ts`: Generates evaluation reports

**Key Behaviors**:
- Load evaluation suites
- Initialize test fixtures
- Execute test cases in sequence
- Record failure details for failed tests
- Generate evaluation reports
- Halt remaining test execution on critical failures

**PBT Validation**:
- Property: For any evaluation suite, all test cases execute and results are recorded

### Governance Module (`packages/skillforge-core/src/governance/`)

The Governance Module tracks skill lineage and changes for audit purposes.

**Components**:
- `timestamp_recorder.ts`: Records creation, modification, and compilation timestamps
- `version_tracker.ts`: Tracks version history when version control is enabled
- `permission_enforcer.ts`: Enforces access control permissions

**Key Behaviors**:
- Record creation timestamp when skills are synthesized
- Record modification timestamp when skills are changed
- Record compilation timestamp when skills are compiled
- Track version history when version control is enabled
- Enforce access control permissions when enabled
- Log governance recording failures without halting execution

**PBT Validation**:
- Property: For any skill lifecycle event, the corresponding timestamp is recorded
- Property: For any version control configuration, version history is tracked consistently

## Data Models

### Skill Definition Schema (Draft-07)

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "title": "SkillDefinition",
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^[a-z0-9-]+$",
      "description": "Unique identifier for the skill (kebab-case)"
    },
    "name": {
      "type": "string",
      "description": "Human-readable name of the skill"
    },
    "description": {
      "type": "string",
      "description": "Description of what the skill does"
    },
    "skillType": {
      "type": "string",
      "enum": ["cloud-infrastructure", "narrative", "data-processing", "api-client"],
      "description": "Type of skill determines generation strategy"
    },
    "parameters": {
      "type": "object",
      "additionalProperties": true,
      "description": "Input parameters for the skill"
    },
    "evaluations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "sampleInput": {"type": "object"},
          "expectedBehavior": {"type": "string"}
        },
        "required": ["sampleInput", "expectedBehavior"]
      },
      "description": "Sample inputs and expected behaviors for testing"
    },
    "properties": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "description": {"type": "string"},
          "testable": {"type": "boolean"}
        },
        "required": ["name", "description", "testable"]
      },
      "description": "Properties for property-based testing"
    },
    "gatekeeping": {
      "type": "object",
      "properties": {
        "enabled": {"type": "boolean"},
        "rules": {"type": "array", "items": {"type": "string"}}
      },
      "required": ["enabled"]
    },
    "crossRuntime": {
      "type": "object",
      "properties": {
        "enabled": {"type": "boolean"},
        "runtimes": {"type": "array", "items": {"type": "string", "enum": ["python", "typescript"]}}
      },
      "required": ["enabled", "runtimes"]
    }
  },
  "required": ["id", "name", "description", "parameters"]
}
```

### Evidence Record Schema

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "title": "EvidenceRecord",
  "type": "object",
  "properties": {
    "recordId": {
      "type": "string",
      "description": "Unique identifier for the evidence record"
    },
    "testId": {
      "type": "string",
      "description": "Identifier of the test that produced this evidence"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "When the evidence was recorded"
    },
    "testCase": {
      "type": "object",
      "description": "The test input and parameters"
    },
    "output": {
      "type": "object",
      "description": "The observed output"
    },
    "expected": {
      "type": "object",
      "description": "The expected output or behavior"
    },
    "status": {
      "type": "string",
      "enum": ["pass", "fail", "error"],
      "description": "Test result status"
    },
    "evidenceType": {
      "type": "string",
      "enum": ["correctness", "violation", "baseline"],
      "description": "Type of evidence recorded"
    }
  },
  "required": ["recordId", "testId", "timestamp", "status", "evidenceType"]
}
```

### Hook Definition Schema

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "title": "HookDefinition",
  "type": "object",
  "properties": {
    "version": {
      "type": "string",
      "const": "v1"
    },
    "hooks": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "description": {"type": "string"},
          "trigger": {
            "type": "string",
            "enum": ["PreToolUse", "PostToolUse", "FileEdited", "AgentSpawn", "Stop"]
          },
          "matcher": {"type": "string"},
          "timeout": {"type": "integer", "minimum": 0},
          "enabled": {"type": "boolean"},
          "action": {
            "type": "object",
            "properties": {
              "type": {"type": "string", "enum": ["command", "agent"]},
              "command": {"type": "string"},
              "prompt": {"type": "string"}
            },
            "required": ["type"]
          },
          "async": {"type": "boolean"}
        },
        "required": ["name", "trigger", "action"]
      }
    }
  },
  "required": ["version", "hooks"]
}
```

### MCP Tool Schema

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "title": "MCPSkillTool",
  "type": "object",
  "properties": {
    "name": {"type": "string"},
    "description": {"type": "string"},
    "inputSchema": {
      "type": "object",
      "$ref": "https://json-schema.org/draft-07/schema#"
    }
  },
  "required": ["name", "description", "inputSchema"]
}
```

## Error Handling

### Phase-Level Error Handling

Each phase in the pipeline handles errors consistently:

- **Synthesis Phase**: Returns descriptive error messages with file locations and line numbers for malformed specifications
- **PBT Phase**: Records minimal failing examples when property violations are detected
- **Diagnostics Phase**: Produces detailed reports with severity levels and remediation steps
- **MCP Compilation Phase**: Returns detailed error information with line numbers for compilation failures

### Graceful Degradation

- Evidence recording failures are logged but do not halt pipeline execution
- Hook execution failures are logged but other hooks continue
- Governance recording failures are logged but do not halt execution

### Security Error Handling

- Permission failures are logged as security events
- Critical vulnerabilities cause immediate pipeline failure
- Triage module rejects invalid requests with descriptive error codes

## Testing Strategy

### Dual Testing Approach

**Property-Based Testing (PBT)**:
- Test 100+ randomized inputs for all testable properties
- Generate edge cases automatically across input spaces
- Verify invariants across all valid executions

**Example-Based Testing**:
- Test specific scenarios that are difficult to express as universal properties
- Test integration points between components
- Test error paths and failure modes

### Property Test Configuration

- Minimum 100 iterations per property test
- Each property test references its design document property
- Tag format: **Feature: {feature_name}, Property {number}: {property_text}**

### Test Coverage Requirements

- All acceptance criteria covered by either PBT or example tests
- Error handling paths tested with invalid inputs
- Security gate tests include malicious input patterns

## Sub-Application Designs

### Application 1: Enterprise Cloud Compliance Auditor (`apps/app1-enterprise-compliance/`)

**Type**: Terminal-based CLI Tool

**Purpose**: Ingests IaC templates (AWS CDK / Terraform), executes compiled compliance skills, and enforces zero-trust resource creation through Kiro PreToolUse security hooks.

**Architecture**:

```
+--------------------------------------------------+
|     app1-enterprise-compliance (CLI)             |
+--------------------------------------------------+
|  +----------------+    +--------------------+    |
|  | CLI Interface  |    | Compliance Engine  |    |
|  +----------------+    +--------------------+    |
|           |                    |                 |
|           v                    v                 |
|    +-------------+    +------------------+      |
|    | IaC Parser  |    | CIS Benchmark    |      |
|    +-------------+    | Validator        |      |
|                       +------------------+      |
|                              |                  |
|                              v                  |
|                   +------------------+          |
|                   | PreToolUse Gate  |          |
|                   +------------------+          |
+--------------------------------------------------+
```

**Key Components**:
- `cli.ts`: Command-line interface for audit commands
- `iac_parser.ts`: Parses AWS CDK and Terraform templates
- `compliance_engine.ts`: Executes compiled compliance skills
- `cis_validator.ts`: Validates against CIS security benchmarks
- `pretool_gate.ts`: Kiro PreToolUse hook for security enforcement

**Requirements Mapping**:
- Requirement 1: Pipeline execution for compliance skill processing
- Requirement 2: Synthesis for compliance skill generation
- Requirement 5: MCP Compilation to generate compliance tools
- Requirement 15: Application-specific initialization

### Application 2: Spooky Gothic Narrative Engine (`apps/app2-spooky-game-engine/`)

**Type**: Interactive Gothic Web Application (React + WebGL)

**Purpose**: Generates dynamic branching horror stories and spatial puzzles using compiled narrative skills, updating dynamic context graphs via PostFileSave hooks.

**Architecture**:

```
+--------------------------------------------------+
|   app2-spooky-game-engine (Web App)              |
+--------------------------------------------------+
|  +-------------+  +------------------+           |
|  | UI Layer    |  | Narrative Engine |           |
|  | (React)     |  | (Dynamic Branch) |           |
|  +-------------+  +------------------+           |
|         |                  |                     |
|         v                  v                     |
|  +-------------+    +------------------+         |
|  | WebGL Canvas|    | PostFileSave Hook|         |
|  | Visualizer  |    | Context Graph    |         |
|  +-------------+    +------------------+         |
+--------------------------------------------------+
```

**Key Components**:
- `ui.tsx`: React component with dark-mode Gothic theme
- `webgl_visualizer.ts`: WebGL visualizer for narrative elements
- `narrative_engine.ts`: Dynamic branching story generator
- `context_graph.ts`: Updates dynamic context graph state
- `postfile_hook.ts`: Kiro PostFileSave hook for asset tracking

**Requirements Mapping**:
- Requirement 1: Pipeline execution for narrative skill processing
- Requirement 2: Synthesis for narrative skill generation
- Requirement 5: MCP Compilation to generate narrative tools
- Requirement 15: Application-specific initialization

## Configuration

### Event Hook Configuration

#### eval-on-save.json

Runs Property-Based Tests and TypeScript compilation on file saves:

```json
{
  "version": "v1",
  "hooks": [
    {
      "name": "SkillForge Continuous Testing & PBT Evaluator",
      "description": "Runs TypeScript compilation and property-based boundary tests automatically whenever core engine files are modified.",
      "trigger": "PostFileSave",
      "matcher": ".*packages/skillforge-core/src/.*\\.ts$",
      "timeout": 30,
      "enabled": true,
      "action": {
        "type": "command",
        "command": "npm --prefix packages/skillforge-core run test"
      }
    }
  ]
}
```

#### pre-tool-security-gate.json

Intercepts tool calls and enforces security policies:

```json
{
  "version": "v1",
  "hooks": [
    {
      "name": "SkillForge Pre-Tool Security Gate",
      "description": "Evaluates tool execution against security policies before allowing dangerous operations.",
      "trigger": "PreToolUse",
      "matcher": ".*",
      "timeout": 5,
      "enabled": true,
      "action": {
        "type": "command",
        "command": "python3 packages/skillforge-core/src/security/gate.py"
      }
    }
  ]
}
```

#### agent-spawn-context.json

Injects workspace steering rules on agent startup:

```json
{
  "version": "v1",
  "hooks": [
    {
      "name": "SkillForge Agent Context Injector",
      "description": "Injects workspace steering rules and active test requirements when an agent session starts.",
      "trigger": "AgentSpawn",
      "matcher": ".*",
      "timeout": 5,
      "enabled": true,
      "action": {
        "type": "agent",
        "prompt": "Load workspace steering rules from .kiro/steering/ and apply them to this session. Enforce strict TypeScript interfaces and immutability patterns."
      }
    }
  ]
}
```

### .kiro/settings/mcp.json

Model Context Protocol server configuration:

```json
{
  "mcpServers": {
    "skillforge-core-engine": {
      "command": "node",
      "args": [
        "${WORKSPACE_ROOT}/packages/skillforge-core/dist/mcp-server/index.js"
      ],
      "env": {
        "NODE_ENV": "development",
        "SKILLFORGE_LOG_LEVEL": "info"
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
```

### .kiro/steering/core-conventions.md

```markdown
---
inclusion: always
description: Core architectural rules, code standards, and security constraints for the Kiro-SkillForge monorepo.
---

# Kiro-SkillForge Development Standards

## Code Standards
- **Language**: TypeScript 5.x executing on Node.js 20+ ES Modules.
- **Strict Mode**: `strict: true` must remain enabled in all `tsconfig.json` files.
- **Immutability**: Avoid mutating state directly; prefer pure functions and immutable data structures.

## Spec-Driven Rules
- Never write code directly without an active feature spec in `.kiro/specs/`.
- All requirements must follow Easy Approach to Requirements Syntax (EARS) formatting:
  - `WHILE <condition>, THE <system> SHALL <action>`
  - `WHEN <trigger>, THE <system> SHALL <action>`
- Task progress inside `tasks.md` must be updated interactively as implementation proceeds.

## Security Constraints
- Hardcoded API keys, tokens, or AWS credentials are strictly prohibited.
- Shell operations executed by Kiro agents must pass the `.kiro/hooks/pre-tool-security-gate.json` validation hook (must exit 0).
```

### .kiro/steering/skill-engineering.md

```markdown
---
inclusion: auto
description: Triggers when prompts mention "skill" or "eval", guiding Kiro to follow the 4-phase SkillForge architecture.
---

# Skill Engineering Workflow

When working on skill development or evaluation:

1. **Verify Active Spec**: Ensure requirements.md exists in `.kiro/specs/{skill-name}/`
2. **Follow 4-Phase Pipeline**: Execute Synthesis → PBT → Diagnostics → MCP Compilation
3. **Property-Based Testing**: Define properties for all testable acceptance criteria
4. **Evidence Recording**: Capture test evidence for audit and verification
5. **MCP Compilation**: Compile skills to stdio MCP servers and Agent Hooks

Use the `skillforge_core` package for shared functionality across all skills.
```

### .kiro/steering/security-guardrails.md

```markdown
---
inclusion: auto
description: Mandates AWS Secrets Manager for all sensitive credentials.
---

# Security Guardrails

## Credential Management
- **MUST** use `{{resolve:secretsmanager:secret-id:SecretString:json-key}}` with `asm-exec`
- **MUST NOT** hardcode API keys, tokens, or credentials
- **MUST NOT** log sensitive values in output

## Code Security
- All shell commands must pass security gate validation
- AWS operations must use the AWS MCP Server or CLI
- Security-sensitive changes require explicit user confirmation

## Rate Limiting
- External API calls must respect rate limits
- Property-based testing iterations must be throttled when calling external services
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Pipeline Execution Order

*For any* valid skill request, the SkillForge Core SHALL execute phases in the order: Synthesis → PBT → Diagnostics → MCP Compilation. If any phase fails, execution halts and failure details are returned.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

### Property 2: Synthesis Artifact Generation

*For any* valid skill specification, the Synthesizer SHALL generate intermediate representation files and executable artifacts for all configured runtimes (Python and TypeScript).

**Validates: Requirements 2.1, 2.2, 2.3**

### Property 3: Property-Based Testing Coverage

*For any* property definition in a skill specification, the PBT Harness SHALL generate at least 100 test inputs and verify the property holds across all valid inputs. When a property violation is detected, the harness SHALL produce a minimal failing example.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

### Property 4: Evidence Record Integrity

*For any* test execution (pass or fail), the Evidence Recorder SHALL capture the test input, output, expected behavior, and status. When evidence is requested, the complete history SHALL be provided.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4**

### Property 5: Hook Execution Reliability

*For any* phase completion or failure, the Event Dispatcher SHALL execute registered hooks in order. When a hook fails, errors SHALL be logged and other hooks SHALL continue execution.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

### Property 6: Malicious Input Testing

*For any* skill specification, the Adversarial Gatekeeper SHALL generate malicious inputs using known vulnerability patterns and monitor foranomalous behavior. When critical vulnerabilities are detected, the pipeline SHALL fail immediately.

**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.6**

### Property 7: Request Triage Validation

*For any* skill request, the Triage Module SHALL validate format, required fields, and source permissions. Invalid requests SHALL be rejected with descriptive error codes, and permission failures SHALL be logged as security events.

**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

### Property 8: Skill Specification Validation

*For any* skill specification, the Validator SHALL check syntax correctness, schema validity, and semantic correctness. Validation failures SHALL return detailed error locations.

**Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**

### Property 9: MCP Compilation Output

*For any* intermediate representation, the MCP Compiler SHALL generate valid MCP tool definitions and Agent Hook definitions in proper JSON schema format. When cross-runtime compilation is enabled, all target runtimes SHALL produce valid artifacts.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.6**

### Property 10: Governance Timestamp Recording

*For any* skill lifecycle event (creation, modification, compilation), the Governance Module SHALL record the corresponding timestamp. When version control is enabled, version history SHALL be tracked consistently.

**Validates: Requirements 14.1, 14.2, 14.3**

### Property 11: Ecosystem Doctor Health Reporting

*For any* workspace configuration, the Doctor SHALL produce a consistent health report with environment status, package validation, and configuration checks. When issues are found, remediation guidance SHALL be provided.

**Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5, 12.6**

### Property 12: Cross-Application Core Initialization

*For any* sub-application (app1-enterprise-compliance or app2-spooky-game-engine), initialization SHALL load the shared skillforge-core library and register custom pipelines. Application failures SHALL trigger proper resource cleanup.

**Validates: Requirements 15.1, 15.2, 15.3, 15.6**