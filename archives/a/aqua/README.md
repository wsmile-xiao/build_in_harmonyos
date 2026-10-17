# aqua

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Declarative CLI Version Manager written in Go. Support Lazy Install, Registry, and continuous update with Renovate.

## Build System

- **Language**: Go
- **Build**: Prebuilt binary from GitHub releases (linux_arm64)
- **CGO**: Disabled (pure Go, statically linked)
- **Approach**: Go linker cannot work on HarmonyOS (mmap restriction), uses official prebuilt binary

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| v2.60.0 | built | Prebuilt linux_arm64 binary, ELF signed for OHOS |
