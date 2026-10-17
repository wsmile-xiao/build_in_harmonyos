# libwandder

`libwandder` is the LibtraceTeam C library for DER and BER encoding and
decoding. The generic API is `libwandder.h`. The ETSI LI helpers are
`libwandder_etsili.h`.

## Versions

| Version | Status |
| --- | --- |
| 2.0.22 | built |

Homepage: https://github.com/LibtraceTeam/libwandder

Upstream tag for this package version is `2.0.22-1`.

## OHOS adaptation

- The GitHub tag archive has `configure.ac` and `Makefile.am` and no
  generated `configure`. The recipe compiles the five sources named by
  `src/Makefile.am` (`encoder.c`, `decoder.c`, `itemhandler.c`,
  `libwandder_etsili.c`, `libwandder_etsili_ber.c`) with the profile C
  compiler.
- Build requirements that are already published: `uthash/2.3.0` (public
  header `libwandder_etsili.h` includes `uthash.h`) and `openssl/3.5.7`
  (`EVP_*` in the ETSI sources). `libm` and `libpthread` are system
  libraries, matching `configure.ac`.
- Upstream 2.0.22 has no `tests/` tree and no automake `TESTS` or
  `check_PROGRAMS`. `test_package/test_wandder.c` links the packaged
  library and exercises the generic encode/decode API plus the ETSI
  decoder constructor.

## Reference

- Upstream: https://github.com/LibtraceTeam/libwandder
