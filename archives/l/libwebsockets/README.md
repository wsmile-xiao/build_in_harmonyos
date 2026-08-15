# libwebsockets

**Description**: A lightweight, pure C library for websockets and web server implementation.

**Website**: https://libwebsockets.org

**License**: MIT (with some parts BSD / CC0)

## Compiled Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 4.3.5 | built | 2026-08-14 | CMake build, OpenSSL 3.5.6 dependency, OHOS sockaddr_storage fixes, ttyd 1.7.7 dependency |

## Key Features

- WebSocket server and client implementation
- HTTP/HTTPS server and client
- HTTP/2 support
- MQTT support
- Lightweight and embeddable
- SSL/TLS support via OpenSSL

## Dependencies

- openssl/3.5.6 (required for SSL/TLS)

## Build System

- CMake

## Platform Compatibility

- ✅ OpenHarmony PC (ARM64)
- OHOS 平台需应用 0001/0002 补丁解决 linux/if_addr.h、linux/netlink.h 的 sockaddr_storage 与 musl sys/socket.h 冲突
