# OpenSSL 1.1.1w notes

## Build

The recipe uses OpenSSL's Perl-based `Configure` flow with the custom
`openharmony-aarch64` target added by patch.

Important OHOS settings:

- `no-asm` for portable OHOS builds.
- `CC=clang` is passed to `Configure`; otherwise OpenSSL 1.1.1w generates a
  Makefile that falls back to `gcc`, which is unavailable on OHOS CI workers.
- Static libraries are built by default.

## Upstream tests

`build()` runs the real upstream test harness:

```bash
make test
```

OpenSSL 1.1.1w has 159 upstream test recipe entries under `test/recipes/`.
These are counted as upstream tests for PR reporting, instead of reporting only
a hand-picked smoke-test subset.

## Consumer test

`test_package` builds and runs `test_openssl.c` with 3 runtime assertions:

1. OpenSSL version query.
2. SHA256 digest calculation.
3. SSL context creation.
