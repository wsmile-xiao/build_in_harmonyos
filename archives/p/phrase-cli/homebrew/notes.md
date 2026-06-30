# phrase-cli homebrew Build Notes

## Source Acquisition
- GitHub URL: https://github.com/phrase/phrase-cli
- Version: 2.63.0 (tag: 2.63.0)
- Download method: git clone --depth 1 --branch 2.63.0 (direct HTTP download failed due to network)
- Source placed in ~/tmp/builds/phrase-cli-homebrew.work/

## Build System
- **Type**: Go (custom/manual build)
- **Go Version**: go1.26.3 linux/arm64
- **CGO_ENABLED**: 1 (required for OpenHarmony)
- **GOOS/GOARCH**: linux/arm64
- **GOPROXY**: https://goproxy.cn,direct

## Build Command
```bash
CGO_ENABLED=1 GOOS=linux GOARCH=arm64 GOPROXY=https://goproxy.cn,direct \
~/usr/local/go1263/bin/go build \
-ldflags="-s -w \
  -X 'github.com/phrase/phrase-cli/cmd.PHRASE_CLIENT_VERSION=2.63.0' \
  -X 'github.com/phrase/phrase-cli/cmd.REVISION=no-git-clone' \
  -X 'github.com/phrase/phrase-cli/cmd.LIBRARY_REVISION=v4.26.0' \
  -X 'github.com/phrase/phrase-cli/cmd.LAST_CHANGE=2026-06-03'" \
-o phrase .
```

## Version Injection
- `PHRASE_CLIENT_VERSION`: 2.63.0 (main version)
- `REVISION`: no-git-clone (git clone source, no separate commit hash)
- `LIBRARY_REVISION`: v4.26.0 (from go.sum)
- `LAST_CHANGE`: 2026-06-03

## DESTDIR Installation
- DESTDIR: ~/tmp/test-install-phrase-cli-2.63.0
- Prefix: ~/usr/local
- Installed: bin/phrase

## Verification
- `phrase version` → 2.63.0 ✅
- ELF: 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), stripped
- Binary size: 12MB (stripped with -s -w)

## Packaging
- Package: phrase-cli-homebrew-ohos-aarch64.tar.gz (11654KB)
- ELF signed ✅
- All quality gates passed ✅

## Network Issues
- GitHub direct download failed (SSL timeout, connection refused)
- GitHub mirrors (ghproxy, gh-proxy, kkgithub) all failed
- goproxy.cn module download: phrase-cli not indexed (module never published to Go proxy)
- Solution: Used git clone --depth 1 to obtain source code directly

## Build Notes
- phrase-cli uses cobra framework for CLI
- Version subcommand (not --version flag): `phrase version`
- Original build uses CGO_ENABLED=0 and Docker, but we use CGO_ENABLED=1 for OpenHarmony
- TMPDIR=/data/storage/el2/base/cache (R10: no hardcoded /tmp)
---

**编译结束**: 2026-06-03 11:03
**最终状态**: published
