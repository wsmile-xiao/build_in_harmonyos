# libetpan

libetpan is a mail library providing a portable, efficient middleware for different kinds of mail access: IMAP, POP3, SMTP, NNTP, and Maildir/MH.

It supports SSL/TLS (via OpenSSL), libcurl for HTTP-based access, iconv for charset conversion, and zlib for compression.

## Versions

| Version | Status | Build Date | Verified Date |
|---------|--------|------------|---------------|
| 1.9.4 | published | 2026-06-02 | 2026-06-03 |

## Dependencies

- OpenSSL (SSL/TLS support)
- libcurl (HTTP-based mail access)
- zlib (compression)
- iconv (charset conversion)

## Notes

- Berkeley DB (cache support) and SASL are disabled by default
- Pure library package (no executable binaries)
- Requires autoreconf/bootstrap when building from GitHub tarball (no included configure script)