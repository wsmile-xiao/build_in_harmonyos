# wslay

wslay is a C library implementing the WebSocket protocol defined by RFC 6455.
It provides frame-level and event-based APIs for WebSocket clients and servers.

## Features

- WebSocket frame encoding and decoding
- Event-based client and server APIs
- Text, binary, control, fragmented, and masked frames

## HarmonyOS adaptation

The Conan recipe supports HarmonyOS PC arm64 with clang. It applies the
minimum Autotools portability fixes needed to recognize the OHOS triplet and
to let `config.status` create temporary files on HMDFS.

## Dependencies

The installed library has no runtime Conan dependencies. CUnit is used only
as an upstream test requirement and is not exposed to consumers.

## References

- Homepage: https://github.com/tatsuhiro-t/wslay
- RFC 6455: https://www.rfc-editor.org/rfc/rfc6455

## Versions

| Version | Status | Date |
|---------|--------|------|
| 1.1.1   | built  | 2026-08-29 |
