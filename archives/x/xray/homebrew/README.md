# xray

V2Ray-compatible proxy tool — Xray-core

## Description

Xray is a V2Ray-compatible proxy tool that supports multiple protocols including VMess, VLESS, Trojan, Shadowsocks, and more. It is designed for network proxying and anti-censorship purposes.

## Version Information

- Current version: v26.3.27
- Build system: Go
- Source: https://github.com/XTLS/Xray-core

## Compilation Notes

- Go build with CGO_ENABLED=1 for OHOS arm64
- Version injection via ldflags: `-X github.com/xtls/xray-core/core.build=v26.3.27`
- Byte-type version variables (Version_x/y/z) are hardcoded in source, not injectable via -X
- TMPDIR must use /data/storage/el2/base/cache (R10)