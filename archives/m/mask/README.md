# mask

A CLI task runner defined by a simple markdown file — inspired by [just](https://github.com/casey/just).

mask reads a `maskfile.md` (markdown file with embedded shell commands) and makes each command available as a CLI subcommand. It supports arguments, flags, environment variables, and subcommands.

## Features
- Define CLI commands in markdown files
- Support for arguments and flags
- Support for environment variables
- Nested subcommands
- Introspection (JSON output of command structure)

## Build Info
- **Build System**: cargo (Rust)
- **Version**: 0.11.7
- **Repository**: https://github.com/jacobdeichert/mask
- **License**: MIT
