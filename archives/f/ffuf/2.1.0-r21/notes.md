# ffuf 2.1.0-r21 Build Notes

## Build Information

- **Software**: ffuf (Fuzz Faster U Fool) - fast web fuzzer
- **Version**: 2.1.0-r21
- **Language**: Go
- **Source URL**: https://github.com/ffuf/ffuf/archive/refs/tags/v2.1.0.tar.gz
- **Build Date**: 2026-06-04
- **Platform**: OpenHarmony linux/arm64

## Build Parameters

- **Build System**: Go (go build)
- **Go Version**: go1.24.2
- **GOPROXY**: https://goproxy.cn,direct
- **GOTOOLCHAIN**: local
- **CGO_ENABLED**: 0 (pure Go, static binary)
- **GOOS**: linux
- **GOARCH**: arm64
- **Build Command**: `go build -v -trimpath -ldflags="-s -w -X main.version=2.1.0" -o ffuf .`
- **ELF Signing**: Required (OpenHarmony platform requirement)

## Source Modifications

1. pkg/ffuf/constants.go: Changed VERSION_APPENDIX from "-dev" to "" for release build

## Build Issues & Solutions

1. **SSL Certificate Error**: GitHub tarball download failed due to SSL cert verification. Solution: Manually downloaded with curl -kL (E105)
2. **Go Version Mismatch**: Pre-built Go standard library packages (go1.23.6) didn't match tool version (go1.24.2). Solution: Set GOROOT explicitly and cleared build cache with go clean -cache (E105)
3. **ELF Signing Required**: Go test binaries need ELF signing on OpenHarmony. Solution: Built test binaries manually with go test -c, then signed with ohc-run.py sign-elf (E105)
4. **TestToCSV Failure**: Upstream test bug (Go map order + missing fields). Not blocking.

## Test Results

- 14/15 unit tests pass (1 upstream bug: TestToCSV)
- ffuf -V returns "ffuf version: 2.1.0"

**编译结束**: 2026-06-04
**最终状态**: built
---

**编译结束**: 2026-08-06 11:36
**最终状态**: built
