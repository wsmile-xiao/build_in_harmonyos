# mini_httpd

**Description**: mini_httpd is a small, lightweight HTTP server from ACME Labs. It is designed to be simple and minimal, suitable for embedding in other applications or for serving static content.

## Version History

| Version | Status | Date |
|---------|--------|------|
| 1.30 | built | 2026-07-15 |

## Source

- **URL**: https://www.acme.com/software/mini_httpd/
- **License**: BSD-like (see source)

## Features

- Lightweight HTTP server
- CGI support
- Virtual hosting
- Basic authentication (htpasswd utility)
- HTTPS support (with OpenSSL)

## OpenHarmony Adaptation

mini_httpd requires platform-specific adaptations for OpenHarmony:

1. **int64_t type**: System headers define int64_t, avoid redefinition
2. **getpass() function**: Not available on OpenHarmony, fallback implementation needed
3. **TMPDIR**: Use `getenv("TMPDIR")` with fallback to `/tmp` (portable, CI-friendly)
4. **Install paths**: Conan recipe overrides BINDIR/MANDIR via make variables (no Makefile patch needed)

## Binaries

- `bin/mini_httpd` - HTTP server
- `bin/htpasswd` - Password file management utility