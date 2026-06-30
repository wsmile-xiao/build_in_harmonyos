# kyverno 1.13.0 — Build Notes

## Build Summary

| Item | Value |
|------|-------|
| Software | kyverno |
| Version | 1.13.0 |
| Build System | Go |
| Status | built ✅ |
| Date | 2026-06-12 |

## Build Configuration

- CGO_ENABLED=0 (pure Go, static binary)
- GOPROXY=https://goproxy.cn,direct
- LD_FLAGS="-s -w" (strip + no DWARF)
- Go version: go1.26.4 linux/arm64

## Binaries Produced

- `kyverno` (102MB) — Main Kubernetes policy controller
- `kyverno-cli` (170MB) — CLI tool for policy management

## Build Process

1. `go build -o cmd/kyverno/kyverno -ldflags="-s -w" ./cmd/kyverno/` ✅
2. `go build -o cmd/cli/kubectl-kyverno/kyverno-cli -ldflags="-s -w" ./cmd/cli/kubectl-kyverno/` ✅
3. Installed to DESTDIR=$TEST_PREFIX ✅
4. Packaging: kyverno-1.13.0-ohos-aarch64.tar.gz (267MB) ✅
5. Local install verification ✅

## Verification

- kyverno-cli: `version` command → Version: (devel), Time: ---, Git commit ID: ---
- kyverno: Binary runs, shows configuration flags (requires KYVERNO_NAMESPACE + kubeconfig)
- Both: ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped

## G0 Note

G0 clean-verify failed because kyverno is a Go project without a traditional configure/Makefile.
The build was manually verified (CGO_ENABLED=0, go build, no patches needed).

---

**编译结束**: 2026-06-12
**最终状态**: built (成功编译，未发布到 cmd-pkgs)
---

**编译结束**: 2026-06-15 11:53
**最终状态**: built
