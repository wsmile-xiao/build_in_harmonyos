# jira-cli 1.7.0 Build Notes

## Build Info
- **Software**: jira-cli (github.com/ankitpokhrel/jira-cli)
- **Version**: 1.7.0
- **Build System**: Go (CGO_ENABLED=0, GOOS=linux, GOARCH=arm64)
- **Go Version**: go1.26.3
- **Build Date**: 2026-06-02

## Build Process
- Source extracted from jira-cli-1.7.0.tar.gz
- Binary built with ldflags for version injection
- Static binary (no shared library dependencies)
- Verified as ELF64 arm64 executable via `file` and `readelf`

## Notes
- HarmonyOS sandbox prevents direct execution verification
- Binary verified via `file` command: ELF executable, 64-bit LSB arm64, static
- Binary size: 19M (stripped with -s -w)
---

**编译结束**: 2026-06-02 11:44
**最终状态**: built
