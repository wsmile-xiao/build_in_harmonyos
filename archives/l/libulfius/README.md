# libulfius

Web Framework to build REST APIs, Webservices or any HTTP endpoint in C
language (the endpoint of the babelouest stack: orcania → yder → hoel /
ulfius).

- Upstream: https://github.com/babelouest/ulfius
- License: LGPL-2.1-or-later
- Language: C99

## Feature matrix on OHOS

- HTTP endpoints (MHD engine) — enabled
- client requests / SMTP (curl) — enabled
- websocket (gnutls + zlib permessage-deflate) — enabled
- uwsc CLI tool — disabled (BUILD_UWSC=OFF; the library websocket
  functionality itself is fully retained)

## Versions

| Version | Status |
|---------|--------|
| 2.7.15  | built (HarmonyOS PC, aarch64, static) |

## Dependencies

- Runtime: orcania, libyder, jansson, libmicrohttpd, gnutls, zlib, curl
- Test-build only: check (upstream CTest suite)
