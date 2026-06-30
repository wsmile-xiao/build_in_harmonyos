# libwebsockets

**Description**: A lightweight, pure C library for websockets and web server implementation.

**Website**: https://libwebsockets.org

**License**: MIT (with some parts LGPL 2.1)

## Compiled Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 4.3.5 | published | 2026-05-28 | CMake build, OpenSSL dependency, E091 sockaddr_storage fix |

## Key Features

- WebSocket server and client implementation
- HTTP/HTTPS server and client
- HTTP/2 support
- MQTT support
- Lightweight and embeddable
- SSL/TLS support via OpenSSL

## Dependencies

- openssl (required for SSL/TLS)

## Build System

- CMake

## Platform Compatibility

- ✅ OpenHarmony (ARM64)
- Requires E091 fix for sockaddr_storage conflict between linux/socket.h and sys/socket.h