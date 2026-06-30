# opa — Open Policy Agent

Open Policy Agent (OPA) is an open-source, general-purpose policy engine that enables unified, context-aware policy enforcement across the stack.

## Version 0.70.0

- **Build Date**: 2026-06-01
- **Build System**: Go (custom)
- **Compiler**: Go 1.26.3
- **Platform**: linux/arm64 (OpenHarmony)
- **Status**: published

### Build Notes

- Static compilation with `CGO_ENABLED=0`
- WebAssembly support unavailable (disabled by CGO_ENABLED=0)
- Built using Go 1.26.3 due to local Go 1.24.2 having mismatched compile tools (1.23.6 vs 1.24.2)