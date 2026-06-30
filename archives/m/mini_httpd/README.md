# mini_httpd

**Description**: mini_httpd is a small, lightweight HTTP server from ACME Labs. It is designed to be simple and minimal, suitable for embedding in other applications or for serving static content.

## Version History

| Version | Status | Date |
|---------|--------|------|
| 1.30 | built | 2026-06-10 |

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
3. **TMPDIR**: Use `$HOME/tmp` instead of `/tmp` (read-only on OHOS)
4. **DESTDIR support**: Makefile modified to support staged installation

## Binaries

- `/usr/local/sbin/mini_httpd` - HTTP server
- `/usr/local/sbin/htpasswd` - Password file management utility