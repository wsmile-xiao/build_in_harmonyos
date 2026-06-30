# restic

Fast, secure, efficient backup program written in Go.

## Description

restic is a backup tool that supports local, SFTP, S3, and many other backends. It features encryption, deduplication, compression, and efficient snapshot management.

## Build System

Go (go build) — custom build system, not autotools/cmake.

## Key Facts

- Pure Go implementation, no C dependencies (CGO_ENABLED=0)
- Build command: `go build -tags release -ldflags="-s -w" -o restic ./cmd/restic`
- Requires Go toolchain with ELF signature for HarmonyOS execution
- goenv local override needed to override go.mod version directive

## Versions

- **0.18.1**: built (2026-06-03)