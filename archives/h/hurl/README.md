# hurl

Hurl is a command line tool that runs HTTP requests defined in a plain text format.

## Description

Hurl lets you run HTTP requests with plain text definitions. It can capture values from HTTP responses and use them in subsequent requests. Hurl is particularly useful for:

- Testing HTTP endpoints
- Capturing data from APIs
- Performance testing
- Integration testing

## Version

- **8.0.1** (2026-05-29) - Built for HarmonyOS aarch64

## Binaries

- `hurl` - HTTP client tool
- `hurlfmt` - hurl file formatter

## Usage

```bash
# Simple GET request
hurl http://example.com/api

# Run hurl file
hurl requests.hurl

# Format hurl file
hurlfmt requests.hurl

# Check version
hurl --version
```

## Build Information

- Build system: cargo (Rust)
- Compiler: rustc 1.95.0
- Platform: HarmonyOS aarch64

## Dependencies

Runtime:
- OpenSSL 1.1.1w
- libcurl 8.7.1

Build:
- Rust 1.95.0
- cargo 1.95.0

## Source

https://github.com/Orange-OpenSource/hurl