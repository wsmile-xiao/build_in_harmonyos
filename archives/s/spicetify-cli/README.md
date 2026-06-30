# spicetify-cli

Spotify client customization CLI tool. spicetify-cli allows customizing the Spotify client UI and functionality through themes, extensions, and custom apps.

## Version 2.43.2

- **Build System**: Custom (Go static build)
- **Compiler**: go1.26.3
- **Build Date**: 2026-06-01
- **Status**: built

## Description

spicetify-cli is a command-line tool for customizing the Spotify desktop client. It provides:

- Theme customization (CSS, colors, assets)
- Extension management (JavaScript extensions)
- Custom app integration
- Spotify client backup and restore
- Developer tools enablement
- Auto-update checking

## Dependencies

- Go 1.26.3+ (for building)
- Spotify desktop client (for runtime usage)

## Notes

- Pure Go static binary, CGO_ENABLED=0
- Version injected via ldflags: `-X main.version=2.43.2`
- Requires GOROOT=/storage/Users/currentUser/usr/local/go1263 on HongMeng (system default Go has mismatched toolchain)