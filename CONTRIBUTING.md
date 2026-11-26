# Contributing to Kiro-SkillForge

Thank you for your interest in contributing to Kiro-SkillForge!

## Development Setup

1. Fork and clone the repository
2. Install Node.js 20.x and Python 3.12
3. Run `npm install` to install dependencies
4. Run `npm run doctor` to verify your environment

## Code Standards

- **TypeScript**: Strict mode enabled in all `tsconfig.json` files
- **Immutability**: Prefer pure functions and immutable data structures
- **Testing**: Property-based testing for universal properties, unit tests for edge cases

## Spec-Driven Development

All requirements use EARS (Easy Approach to Requirements Syntax) formatting:

- `WHEN <trigger>, THE <system> SHALL <action>`
- `IF <condition>, THEN THE <system> SHALL <action>`

Before implementing a feature:
1. Create a spec in `.kiro/specs/<feature-name>/`
2. Write `requirements.md` with EARS-format acceptance criteria
3. Write `design.md` with architecture and data models
4. Write `tasks.md` with implementation checklist

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes following code standards
3. Ensure all tests pass: `npm run test`
4. Update documentation if needed
5. Submit a pull request with a clear description

## Security

- Never commit hardcoded credentials
- Use AWS Secrets Manager for sensitive data
- All shell operations must pass security gate validation
