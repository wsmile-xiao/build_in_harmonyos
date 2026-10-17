# uacme

Lightweight ACME (RFC 8555) client, packaged for OpenHarmony PC.

| Item | Value |
|---|---|
| Upstream | https://github.com/ndilieto/uacme |
| Version | 1.8.1 |
| Source | `refs/tags/upstream/1.8.1` (pristine release) via codeload.github.com |
| SHA-256 | `de7588577f8298dcb0d42dfaa9452a918fa692c4e165060207ac22f72fb0425d` |
| Language | C99 |
| Build system | GNU Autotools |
| Status | built |

## Source note

Upstream has no GitHub release assets, and the plain `refs/tags/v1.8.1`
archive ships neither `configure` nor `.tarball-version`, so it builds as
`PACKAGE_VERSION=UNKNOWN`. The pristine release channel documented in
`README.md:51-58` is the `upstream/latest` branch, tagged `upstream/1.8.1`;
that archive is used here and carries `configure` with `PACKAGE_VERSION='1.8.1'`.

## Dependencies

- `curl/8.15.0` - libcurl with HTTPS (mandatory)
- `openssl/3.5.6.1` - the selected TLS backend

## Binaries

- `uacme` - the ACME client
- `ualpn` - the optional tls-alpn-01 responder (upstream default: built)

## Tests

uacme ships **no automated tests**: `make check` is an empty target and no
`tests/` directory or CI configuration exists in any upstream branch. The
`test_package` performs the real offline check - running the installed
`uacme -V`, which initialises libcurl and the TLS backend.
