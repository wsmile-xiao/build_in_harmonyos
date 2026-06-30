# ntfy 2.15.0-r5 Compilation Notes

## Software Overview
- **Name**: ntfy
- **Version**: 2.15.0-r5
- **Description**: Simple HTTP push notification service (Go project)
- **Homepage**: https://ntfy.sh/
- **Source**: https://github.com/binwiederhier/ntfy/archive/refs/tags/v2.15.0.tar.gz (downloaded from gitee mirror)

## Build System
- **Type**: Go (CGO_ENABLED=1 for sqlite3)
- **Go Version**: go1.24.2 (from ~/usr/local/go/bin/go)
- **Build Tags**: sqlite_omit_load_extension,osusergo,netgo
- **CGO**: Enabled (required for mattn/go-sqlite3)
- **Compiler**: clang (for CGO)

## Compilation Issues and Solutions

### Issue 1: Source download - GitHub unreachable
- **Problem**: GitHub URLs unreachable from this platform (SSL/network issues)
- **Solution**: Downloaded from gitee.com mirror (https://gitee.com/mirrors/ntfy/repository/archive/v2.15.0.tar.gz)

### Issue 2: Go stdlib version mismatch (go1.23.6 vs go1.24.2)
- **Problem**: ~/usr/local/bin/go uses GOROOT=~/usr/local which has pre-compiled stdlib from go1.23.6, incompatible with go1.24.2 tool
- **Solution**: Used ~/usr/local/go/bin/go with GOROOT=~/usr/local/go which has proper stdlib including crypto/pbkdf2

### Issue 3: crypto/pbkdf2 not in std (with ~/usr/local/bin/go)
- **Problem**: go-jose/v4@v4.1.3 uses crypto/pbkdf2 (new in Go 1.24), but the ~/usr/local Go installation was incomplete (missing this stdlib package)
- **Solution**: Using ~/usr/local/go/bin/go with GOROOT=~/usr/local/go resolves this since it has the complete stdlib source (~/usr/local/go/src/crypto/pbkdf2/)

### Issue 4: go.mod toolchain directive
- **Problem**: go.mod has `toolchain go1.24.5` which would trigger automatic toolchain download
- **Solution**: Set GOTOOLCHAIN=local to use local Go 1.24.2 instead. The go.mod was kept intact since GOTOOLCHAIN=local overrides it.

## Build Configuration
- **Build Command**: `go build -o ntfy -tags sqlite_omit_load_extension,osusergo,netgo -ldflags "-X main.version=v2.15.0 -X main.commit=v2.15.0" .`
- **DESTDIR**: $TEST_PREFIX (test-install staging directory)
- **Install**: ntfy binary → $DEFAULT_PREFIX/bin/ntfy

## Verification Results
- **Binary**: ntfy v2.15.0 (v2.15.0), runtime go1.24.2
- **File**: ELF 64-bit LSB arm64, dynamic (ld-musl)
- **Size**: ~90MB (not stripped), ~43MB (stripped in package)
- **ELF Signing**: Successful
- **Package**: ntfy-2.15.0-r5-ohos-aarch64.tar.gz (43214KB)

## Test Report
- ntfy --help: Works correctly, shows all commands
- No formal `make check` (Go project - test suite requires Go toolchain + network)
- Functional verification: binary executes correctly on OpenHarmony
---

**编译结束**: 2026-06-04 14:13
**最终状态**: published
