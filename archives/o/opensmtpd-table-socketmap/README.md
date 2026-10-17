# opensmtpd-table-socketmap

OpenSMTPD socketmap table backend. Proxies table lookups via Unix domain socket using the socketmap protocol.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 1.1.1-r0 | built | 2026-08-17 |

## Description

`table-socketmap` is an OpenSMTPD table backend that uses the socketmap protocol to proxy table lookups to an external server via a Unix domain socket. It reads requests from stdin using the stdio table protocol and forwards them to the configured socket.

## Build System

- Autotools (configure.ac + Makefile.am)
- Source tarball does not include generated autotools files; requires `autoreconf -vfi`
- Binary installed to `libexec/smtpd/table-socketmap`

## License

MIT
