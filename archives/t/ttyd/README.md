# ttyd

**Description**: Share your terminal over the web.

**Website**: https://github.com/tsl0922/ttyd

**License**: MIT

## Compiled Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 1.7.7 | built | 2026-08-17 | CMake build, deps: libwebsockets 4.3.5.1 (LWS_WITH_LIBUV), libuv 1.52.1, json-c 0.18, zlib 1.3.1, openssl 3.5.6 |

## Key Features

- Share your terminal over the web (browser-based terminal)
- Built on libwebsockets + libuv for the WebSocket server and event loop
- Client-side rendering with WebGL2/xterm.js
- SSL/TLS support via OpenSSL, Basic/header auth, plugin support

## Usage

```bash
ttyd -p 7681 /bin/sh
```

- `ttyd --version` — show version (1.7.7)
- `ttyd --help` / `ttyd -h` — usage
- `ttyd -p <port> <command>` — serve `<command>` on the given port
