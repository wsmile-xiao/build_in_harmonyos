# runme 3.16.11 Build Notes

## Software
- **Name**: runme
- **Version**: 3.16.11
- **Source**: GitHub github.com/runmedev/runme v3.16.11
- **Language**: Go

## Build Environment
- **Go Version**: go1.26.4
- **Target**: linux/arm64 (static, CGO_ENABLED=0)
- **GOPROXY**: https://goproxy.cn,direct
- **SSL_CERT_FILE**: /etc/ssl/certs/cacert.pem (required for TLS in this environment)

## Build Command
```bash
SSL_CERT_FILE=/etc/ssl/certs/cacert.pem \
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
go build -ldflags "-s -w -X 'github.com/runmedev/runme/v3/internal/version.BuildVersion=3.16.11' -X 'github.com/runmedev/runme/v3/internal/version.Commit=v3.16.11'" -o runme .
```

## Key Issues & Fixes
1. **TLS/SSL证书问题**: 系统仅提供 /etc/ssl/certs/cacert.pem，Go/curl默认无法完成TLS验证。必须显式设置 `SSL_CERT_FILE=/etc/ssl/certs/cacert.pem` 才能访问HTTPS站点。
2. **Go代理超时**: proxy.golang.org 在中国大陆不可用。配置 GOPROXY=https://goproxy.cn,direct 和 GOSUMDB=sum.golang.google.cn 解决。
3. **首次编译失败**: 因proxy.golang.org超时和TLS证书问题导致模块下载失败。
4. **模块下载耗时**: 第二次编译成功，但模块下载耗时较长（goproxy.cn作为代理）。

## Binary Details
- **Output**: runme (ELF 64-bit LSB arm64, static, stripped)
- **Size**: ~49MB (51450944 bytes)

## Quality Gate
- G1: PASS (binary integrity verified)
- G2: WARN (runme --version returns non-zero; runme uses `version` subcommand)
- G3: PASS (static binary, no RPATH needed)
- G4: PASS (manifest, notes, directories present)

## Installation
DESTDIR install to staging directory, binary placed at:
/data/storage/el2/base/cache/test-install-runme-3.16.11/storage/Users/currentUser/usr/local/bin/runme
---

**编译结束**: 2026-06-11 01:14
**最终状态**: built
