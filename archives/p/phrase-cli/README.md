# phrase-cli

Phrase CLI - Command-line tool for Phrase localization management platform.

- **Version**: 2.63.0 (homebrew)
- **Source**: https://github.com/phrase/phrase-cli
- **Build System**: Go
- **Downloads (Homebrew)**: 2885

## Description

The Phrase CLI is a command-line tool for the Phrase localization management platform.
It allows you to push and pull translations, manage projects, and integrate with your
development workflow.

## Compilation Notes

- Go build system with CGO_ENABLED=1 for OpenHarmony compatibility
- Version injected via ldflags: -X github.com/phrase/phrase-cli/cmd.PHRASE_CLIENT_VERSION
- GOPROXY=https://goproxy.cn,direct for Chinese network environment
