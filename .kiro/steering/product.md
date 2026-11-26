---
inclusion: always
description: Product overview and vision for Kiro-SkillForge
---

# Kiro-SkillForge Product Overview

## One-Liner
An autonomous AI skill compiler, spec-driven evaluation harness, and governance platform for AWS Kiro developers.

## Target Users
- **Cloud Engineers** building AI-powered automation on AWS Kiro
- **Platform Teams** creating reusable skill templates and governance policies
- **DevOps Engineers** implementing continuous compliance and security validation
- **AI/ML Developers** designing agent capabilities with spec-driven workflows

## Value Proposition
Kiro-SkillForge transforms unstructured vibe coding into rigorous, evidence-backed skill engineering. It automates the entire lifecycle from requirement synthesis to cross-runtime compilation while maintaining audit trails and enforcing security guardrails.

## Core Capabilities

### 1. Synthesis Engine
Transforms high-level skill specifications into executable artifacts:
- AST parsing from Markdown skill prompts
- JSON Schema generation for typed tool inputs
- Automatic documentation and test fixture generation

### 2. Property-Based Testing (PBT)
Validates skills against randomized inputs to catch edge cases:
- `fast-check` integration for 100+ parameter combinations
- Automatic minimal failing example identification
- Regression baseline comparison

### 3. Ecosystem Doctor
Monitors workspace health and configuration validity:
- Tool identifier collision detection
- Circular parameter reference warnings
- Missing environment credential alerts

### 4. Cross-Runtime Compiler
Deploys skills to multiple execution targets:
- Kiro MCP server configuration (`.kiro/settings/mcp.json`)
- Kiro Agent Hooks (`.kiro/hooks/`)
- Standalone Python/TypeScript modules

## MVP Features

### Phase 1: Core Pipeline
- [x] Synthesis Engine with AST parsing
- [x] PBT harness with fast-check
- [x] Ecosystem Doctor health checks
- [x] MCP Compiler for Kiro integration

### Phase 2: Dual Applications
- [ ] **app1-enterprise-compliance**: Cloud compliance auditor CLI
  - AWS CDK/Terraform scanning
  - CIS benchmark assertions
  - PreToolUse security hooks

- [ ] **app2-spooky-game-engine**: Gothic narrative engine
  - React + WebGL dark-mode UI
  - Branching horror narratives
  - PostFileSave asset hooks

### Phase 3: Governance & Automation
- [ ] Continuous testing hooks (PostFileSave)
- [ ] Security gate hooks (PreToolUse)
- [ ] Workspace MCP server configuration
- [ ] Skill lineage and audit tracking

## Success Metrics
- **Code Quality**: 100% spec-driven development with EARS requirements
- **Test Coverage**: Property-based testing catches edge cases unit tests miss
- **Security**: Zero hardcoded credentials, all hooks validated
- **Reusability**: Single core package powers two distinct applications
