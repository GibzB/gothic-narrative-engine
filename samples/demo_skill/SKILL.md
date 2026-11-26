---
name: demo-skill
version: 1.0.0
description: A demonstration skill showing the SKILL.md format with YAML frontmatter and parameter schema validation.
triggers:
  - When the user requests a demonstration of skill capabilities.
  - When testing the skillforge-core validation pipeline.
parameters:
  $schema: "http://json-schema.org/draft-07/schema#"
  type: object
  properties:
    action:
      type: string
      enum: ["validate", "test", "compile"]
      description: The action to perform with this skill.
    target:
      type: string
      minLength: 1
      maxLength: 500
      description: The target file or resource to operate on.
    verbose:
      type: boolean
      default: false
      description: Whether to output verbose logging.
    count:
      type: integer
      minimum: 1
      maximum: 100
      default: 10
      description: Number of iterations or items to process.
  required:
    - action
    - target
---

# Demo Skill

This is a demonstration skill that showcases the Kiro-SkillForge 4-phase pipeline.

## Capabilities

The demo skill can:

1. **Validate** - Check files for structural integrity
2. **Test** - Run property-based tests against schemas
3. **Compile** - Generate MCP server code from definitions

## Usage Example

```
Use the demo-skill to validate the configuration file at ./config.yaml
```

## Implementation Notes

This skill is designed for testing the skillforge-core pipeline:

- Phase 1 (Synthesis): The triage router should classify requests using this skill as `USE` intent
- Phase 2 (Validation): The validator should verify frontmatter integrity and parameter schema
- Phase 3 (Diagnostics): The doctor should check for ecosystem health issues
- Phase 4 (Compilation): The compiler should generate working MCP server code

## Parameter Validation

The skill accepts the following parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| action | string | Yes | One of: validate, test, compile |
| target | string | Yes | Target file or resource path |
| verbose | boolean | No | Enable verbose logging |
| count | integer | No | Number of iterations (1-100) |

## Error Handling

The skill handles errors gracefully:

- Returns clear error messages for invalid actions
- Validates target paths before processing
- Provides detailed diagnostics in verbose mode
