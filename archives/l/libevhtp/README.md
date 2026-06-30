# libevhtp

Libevhtp is a flexible, high-performance HTTP server and request parser built on top of libevent. It provides a more flexible and feature-rich replacement for libevent's built-in HTTPD API.

## Features
- High-performance HTTP request parsing
- SSL/TLS support via OpenSSL
- Thread pool support (evthr)
- Based on libevent event loop
- KV (key-value) storage for headers and query strings
- Regex-based path routing (disabled in this build)

## Compiled Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 1.2.18 | published | 2026-06-02 | CMake 4.1 compat fix + test_big_endian replacement; 9/9 functional tests PASS on HarmonyOS |

## Dependencies
- libevent >= 2.1 (required)
- OpenSSL (optional, for SSL/TLS support — enabled in this build)
- pthread (for threading support — enabled in this build)

## HarmonyOS Platform Notes
- Compiled as static library (libevhtp.a) only
- ONIGURUMA regex routing disabled (EVHTP_DISABLE_REGEX)
- SSL/TLS support enabled (linked with OpenSSL 1.1.1w)
- Thread pool support enabled (linked with libevent_pthreads)
- pkg-config file has libdir/includedir field issues; recommend CMake integration (`find_package(libevhtp)`)

## Functional Test Results (2026-06-03)

| Test | Result |
|------|--------|
| Header compilation compatibility | ✅ PASS |
| KV operations (create/find) | ✅ PASS |
| HTTP method enums | ✅ PASS |
| Response status codes | ✅ PASS |
| HTTP server creation/bind | ✅ PASS |
| Callback registration | ✅ PASS |
| Thread pool create/free | ✅ PASS |
| SSL context initialization | ✅ PASS |
| End-to-end HTTP request/response | ✅ PASS |