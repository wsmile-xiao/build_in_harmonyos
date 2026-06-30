# base64

Base64 encoder/decoder command-line utility by John Walker (Fourmilab).

## Description

The `base64` utility encodes and decodes binary data in the Base64 format as specified in RFC 1341. It supports both redirection and command-line file argument modes.

## Available Versions

| Version | Status | Date |
|---------|--------|------|
| 1.5 | published | 2026-05-28 |

## Source

- URL: https://www.fourmilab.ch/webtools/base64/base64-1.5.tar.gz

## Build Notes

- Build system: autotools
- Compiler: clang
- Requires patches for OpenHarmony HMDFS compatibility (R10: /tmp read-only)