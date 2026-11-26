# Implementation Plan: Kiro-SkillForge

## Overview

Kiro-SkillForge is an autonomous AI skill compiler and governance platform implementing a 4-phase pipeline (Synthesis, Property-Based Testing, Diagnostics, MCP Compilation). This task plan breaks down implementation into discrete coding steps, covering repository setup, core skeleton package, two specialized applications, and governance configuration.

## Tasks

- [x] 1. Repository setup & workspace initialization
  - [x] 1.1 Create project directory structure
    - Create monorepo root with standard folders: `packages/skillforge-core/`, `apps/app1-enterprise-compliance/`, `apps/app2-spooky-game-engine/`
    - Create `docs/`, `tests/`, `scripts/` directories at workspace root
    - Create workspace configuration files: `tsconfig.json`, `package.json`, `nx.json`
    - _Requirements: 15.3_

  - [x] 1.2 Initialize Git repository and setup CI/CD
    - Create `.gitignore` with Python, TypeScript, and build artifacts patterns
    - Setup GitHub Actions workflow for automated testing
    - Configure branch protection rules for main branch
    - _Requirements: 14.4_

  - [x] 1.3 Setup Node.js and Python environment
    - Create `.nvmrc` for Node.js version (20.x)
    - Create `.python-version` for Python version (3.12)
    - Setup virtual environment for Python dependencies
    - _Requirements: 12.1, 12.2_

- [x] 2. Implement core skeleton package (packages/skillforge-core)
  - [x] 2.1 Create package structure and base interfaces
    - Define core TypeScript interfaces for SkillDefinition, EvidenceRecord, HookDefinition
    - Create base classes for PhaseExecutor, Validator, and Compiler
    - Setup shared logging and error handling utilities
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 2.2 Implement Triage Module (`src/triage/`)
    - [x] 2.2.1 Create format validator
      - Validate JSON structure of skill requests
      - Check required fields: id, name, description, parameters
      - Return descriptive error codes for validation failures
      - _Requirements: 9.1, 9.2, 9.4_

    - [x] 2.2.2 Create permission checker
      - Check request source against allowed list
      - Log security events for permission failures
      - Support rate limiting when enabled
      - _Requirements: 9.3, 9.5, 9.6_

  - [x] 2.3 Implement Validator (`src/validation/`)
    - [x] 2.3.1 Create spec parser
      - Parse skill specification files with error reporting
      - Extract AST definitions from Markdown skill prompts
      - Return line numbers for syntax errors
      - _Requirements: 10.1, 10.5_

    - [x] 2.3.2 Create syntax checker
      - Validate JSON Schema draft-07 compliance
      - Check enum values against allowed types
      - Validate pattern matching for identifiers
      - _Requirements: 10.2_

    - [x] 2.3.3 Create schema validator
      - Validate against SkillDefinition schema
      - Check required properties and nested object validity
      - _Requirements: 10.3_

    - [x] 2.3.4 Create semantic validator
      - Check parameter consistency across skill types
      - Validate property definitions for testability
      - Apply custom validation rules if present
      - _Requirements: 10.4_

  - [x] 2.4 Implement Synthesis Engine (`src/synthesis/`)
    - [x] 2.4.1 Create parser
      - Convert Markdown skill prompts to AST
      - Extract skill type identifier and generation strategy
      - Return descriptive error messages for malformed specifications
      - _Requirements: 2.1, 2.4, 2.5_

    - [x] 2.4.2 Create schema generator
      - Build JSON Schema definitions for tool input validation
      - Support dynamic parameter schemas from skill specifications
      - _Requirements: 2.2_

    - [x] 2.4.3 Create artifact generator
      - Produce Python executable artifacts
      - Produce TypeScript executable artifacts
      - Generate intermediate representation files
      - _Requirements: 2.3_

  - [x] 2.5 Implement PBT Harness (`src/evaluation/`)
    - [x] 2.5.1 Create PBT runner
      - Integrate fast-check for generating 100+ randomized test inputs
      - Load property definitions from skill specifications
      - Execute skills with each generated input
      - _Requirements: 3.1, 3.2, 3.3_

    - [x] 2.5.2 Create regression checker
      - Evaluate tool response consistency against stored baselines
      - Identify performance drift across test runs
      - _Requirements: 3.5_

    - [x] 2.5.3 Create evidence recorder
      - Capture test inputs and outputs for all executions
      - Store evidence of correctness for passing tests
      - Store failing inputs and expected outputs for failures
      - _Requirements: 6.1, 6.2, 6.3_

  - [x] 2.6 Implement Diagnostics Phase (`src/diagnostics/`)
    - [x] 2.6.1 Create performance analyzer
      - Analyze skill execution timing metrics
      - Flag performance issues exceeding configured thresholds
      - Generate performance reports with remediation suggestions
      - _Requirements: 4.1, 4.2_

    - [x] 2.6.2 Create code analyzer
      - Identify potential correctness issues through static analysis
      - Check for common anti-patterns and security vulnerabilities
      - _Requirements: 4.3_

    - [x] 2.6.3 Create historical analyzer
      - Analyze historical test results for failure patterns
      - Identify skills with recurring issues
      - _Requirements: 4.4_

  - [x] 2.7 Implement MCP Compiler (`src/compiler/`)
    - [x] 2.7.1 Create MCP compiler
      - Load intermediate representation from Synthesis phase
      - Generate MCP tool definitions in valid JSON schema format
      - _Requirements: 5.1, 5.2_

    - [x] 2.7.2 Create hook compiler
      - Generate Agent Hook definitions from skill specifications
      - Support PreToolUse, PostToolUse, FileEdited triggers
      - _Requirements: 5.3_

    - [x] 2.7.3 Create runtime validator
      - Validate output formats for Python artifacts
      - Validate output formats for TypeScript artifacts
      - _Requirements: 5.4, 5.6_

  - [x] 2.8 Implement Event Dispatcher (`src/events/`)
    - [x] 2.8.1 Create event registry
      - Store hook definitions for registered events
      - Support registration of phase completion hooks
      - Support registration of phase failure hooks
      - _Requirements: 7.3_

    - [x] 2.8.2 Create event dispatcher
      - Trigger hooks on successful phase completion
      - Trigger failure hooks on phase failure
      - Execute registered hooks in order
      - _Requirements: 7.1, 7.2, 7.4_

    - [x] 2.8.3 Create async queue
      - Queue asynchronous hooks for background execution
      - Execute hooks without blocking main pipeline
      - _Requirements: 7.6_

  - [x] 2.9 Implement Adversarial Gatekeeper (`src/gatekeeper/`)
    - [x] 2.9.1 Create malicious input generator
      - Generate malicious inputs using known vulnerability patterns
      - Support SQL injection, XSS, command injection patterns
      - _Requirements: 8.1_

    - [x] 2.9.2 Create exploit monitor
      - Monitor skill execution for异常 behavior
      - Detect memory exhaustion, infinite loops, unauthorized access
      - _Requirements: 8.3_

    - [x] 2.9.3 Create vulnerability recorder
      - Record exploit paths when vulnerabilities are detected
      - Generate detailed vulnerability reports
      - _Requirements: 8.4_

  - [x] 2.10 Implement Governance Module (`src/governance/`)
    - [x] 2.10.1 Create timestamp recorder
      - Record creation timestamp when skills are synthesized
      - Record modification timestamp when skills are changed
      - Record compilation timestamp when skills are compiled
      - _Requirements: 14.1, 14.2, 14.3_

    - [x] 2.10.2 Create version tracker
      - Track version history when version control is enabled
      - Generate version snapshots for each skill state
      - _Requirements: 14.4_

    - [x] 2.10.3 Create permission enforcer
      - Enforce access control permissions when enabled
      - Validate user permissions before modification operations
      - _Requirements: 14.5_

  - [x] 2.11 Implement Ecosystem Doctor (`src/doctor/`)
    - [x] 2.11.1 Create config validator
      - Validate JSON syntax in configuration files
      - Check `.kiro/hooks/` directory structure
      - Report configuration file errors
      - _Requirements: 12.4_

    - [x] 2.11.2 Create health reporter
      - Generate ecosystem health status reports
      - Summarize environment availability and package versions
      - _Requirements: 12.5_

    - [x] 2.11.3 Create conflict analyzer
      - Scan for identifier collisions across skills
      - Detect circular parameter dependencies
      - Identify missing required credentials
      - _Requirements: 12.6_

- [x] 3. Implement Application 1: Enterprise Cloud Compliance Auditor
  - [x] 3.1 Create application structure
    - Initialize package with `package.json` and `tsconfig.json`
    - Create CLI interface with command definitions
    - Setup integration with skillforge-core
    - _Requirements: 15.1_

  - [x] 3.2 Implement IaC Parser
    - Parse AWS CDK templates (TypeScript/Python)
    - Parse Terraform templates (HCL)
    - Extract resource definitions and properties
    - _Requirements: App1-specific_

  - [x] 3.3 Implement Compliance Engine
    - Load compiled compliance skills from skillforge-core
    - Execute compliance checks against parsed IaC resources
    - Generate compliance reports with severity levels
    - _Requirements: App1-specific_

  - [x] 3.4 Implement CIS Validator
    - Validate resources against CIS AWS Foundations Benchmark
    - Check for common security misconfigurations
    - Map findings to specific CIS controls
    - _Requirements: App1-specific_

  - [x] 3.5 Implement PreToolUse Gate
    - Create Kiro PreToolUse hook for security enforcement
    - Evaluate tool execution against security policies
    - Block dangerous operations based on compliance rules
    - _Requirements: App1-specific, 15.3_

- [x] 4. Implement Application 2: Spooky Gothic Narrative Engine
  - [x] 4.1 Create application structure
    - Initialize React application with TypeScript
    - Setup build configuration and development server
    - Create directory structure for components and assets
    - _Requirements: 15.2_

  - [x] 4.2 Implement UI Layer
    - Create dark-mode Gothic theme with CSS
    - Build interactive narrative controls
    - Implement navigation for story branches
    - _Requirements: App2-specific_

  - [x] 4.3 Implement WebGL Visualizer
    - Setup Three.js for 3D rendering
    - Create spatial puzzle visualizations
    - Animate narrative element transitions
    - _Requirements: App2-specific_

  - [x] 4.4 Implement Narrative Engine
    - Load compiled narrative skills from skillforge-core
    - Generate dynamic branching story content
    - Track player progress and story state
    - _Requirements: App2-specific_

  - [x] 4.5 Implement Context Graph
    - Update dynamic context graph state
    - Persist context changes to storage
    - Load context from previous sessions
    - _Requirements: App2-specific_

  - [x] 4.6 Implement PostFileSave Hook
    - Create Kiro PostFileSave hook for asset tracking
    - Monitor narrative asset files for changes
    - Trigger context graph updates on file saves
    - _Requirements: App2-specific, 15.3_

- [x] 5. Configure Kiro governance & automation hooks
  - [x] 5.1 Setup evaluation-on-save hook
    - Create `.kiro/hooks/eval-on-save.json`
    - Configure PostFileSave trigger for core engine files
    - Set timeout to 30 seconds for test execution
    - _Requirements: 7.1, 7.2_

  - [x] 5.2 Setup security gate hook
    - Create `.kiro/hooks/pre-tool-security-gate.json`
    - Configure PreToolUse trigger with matcher for all tools
    - Set timeout to 5 seconds for fast security checks
    - _Requirements: 7.1, 7.2_

  - [x] 5.3 Setup agent spawn hook
    - Create `.kiro/hooks/agent-spawn-context.json`
    - Configure AgentSpawn trigger
    - Inject workspace steering rules and active test requirements
    - _Requirements: 7.1, 7.2_

  - [x] 5.4 Configure MCP servers
    - Create `.kiro/settings/mcp.json`
    - Register skillforge-core-engine as stdio MCP server
    - Add sequential-thinking server for reasoning
    - _Requirements: 5.1, 5.2_

  - [x] 5.5 Setup steering files
    - Create `.kiro/steering/core-conventions.md`
    - Create `.kiro/steering/skill-engineering.md`
    - Create `.kiro/steering/security-guardrails.md`
    - _Requirements: 14.6_

- [x] 6. Integration and wiring
  - [x] 6.1 Wire core components together
    - Connect Triage → Validator → Synthesis → PBT → Diagnostics → MCP Compilation
    - Setup error handling between phases
    - Configure event hook triggers for phase completion/failure
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 6.2 Wire applications to core
    - Connect app1-enterprise-compliance to skillforge-core
    - Connect app2-spooky-game-engine to skillforge-core
    - Setup custom pipeline registration for each application
    - _Requirements: 15.1, 15.2, 15.3_

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Testing and validation
  - [x] 8.1 Write property tests for core pipeline execution
    - **Property 1: Pipeline Execution Order**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

  - [x] 8.2 Write property tests for synthesis phase
    - **Property 2: Synthesis Artifact Generation**
    - **Validates: Requirements 2.1, 2.2, 2.3**

  - [x] 8.3 Write property tests for PBT harness
    - **Property 3: Property-Based Testing Coverage**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4**

  - [x] 8.4 Write property tests for evidence recording
    - **Property 4: Evidence Record Integrity**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

  - [x] 8.5 Write property tests for event dispatching
    - **Property 5: Hook Execution Reliability**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

  - [x] 8.6 Write property tests for adversarial gatekeeping
    - **Property 6: Malicious Input Testing**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.6**

  - [x] 8.7 Write property tests for triage module
    - **Property 7: Request Triage Validation**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

  - [x] 8.8 Write property tests for validation
    - **Property 8: Skill Specification Validation**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**

  - [x] 8.9 Write property tests for MCP compilation
    - **Property 9: MCP Compilation Output**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.6**

  - [x] 8.10 Write property tests for governance module
    - **Property 10: Governance Timestamp Recording**
    - **Validates: Requirements 14.1, 14.2, 14.3**

  - [x] 8.11 Write property tests for ecosystem doctor
    - **Property 11: Ecosystem Doctor Health Reporting**
    - **Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5, 12.6**

  - [x] 8.12 Write property tests for cross-application initialization
    - **Property 12: Cross-Application Core Initialization**
    - **Validates: Requirements 15.1, 15.2, 15.3, 15.6**

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Application-specific components can be developed in parallel after core skeleton is established
- Ecosystem Doctor utilities provide diagnostic scripts: `triage_skill_request.py`, `validate_skill.py`, `run_skill_evals.py`, `skillforge_doctor.py`, `compile_skill.py`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.2.1", "2.2.2", "2.3.1", "2.3.2", "2.4.1"] },
    { "id": 3, "tasks": ["2.3.3", "2.3.4", "2.4.2", "2.4.3", "2.5.1"] },
    { "id": 4, "tasks": ["2.5.2", "2.5.3", "2.6.1", "2.6.2", "2.6.3"] },
    { "id": 5, "tasks": ["2.7.1", "2.7.2", "2.7.3", "2.8.1", "2.8.2"] },
    { "id": 6, "tasks": ["2.8.3", "2.9.1", "2.9.2", "2.9.3", "2.10.1"] },
    { "id": 7, "tasks": ["2.10.2", "2.10.3", "2.11.1", "2.11.2", "2.11.3"] },
    { "id": 8, "tasks": ["3.1", "4.1"] },
    { "id": 9, "tasks": ["3.2", "4.2", "5.1", "5.2", "5.3"] },
    { "id": 10, "tasks": ["3.3", "4.3", "5.4", "5.5"] },
    { "id": 11, "tasks": ["3.4", "4.4"] },
    { "id": 12, "tasks": ["3.5", "4.5", "4.6"] },
    { "id": 13, "tasks": ["6.1", "6.2"] },
    { "id": 14, "tasks": ["8.1", "8.2", "8.3", "8.4", "8.5"] },
    { "id": 15, "tasks": ["8.6", "8.7", "8.8", "8.9", "8.10"] },
    { "id": 16, "tasks": ["8.11", "8.12"] }
  ]
}
```
