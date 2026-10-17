# mhash 0.9.9.9 adaptation notes

## Status

OHOS true-device verification passed on 2026-07-30.

- Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-mhash-mhash-0.9.9.9-conan-r7-test-package-20260730-115812-21953`
- Full reference: `mhash/0.9.9.9#974b33885624a6e6ddd418a702a32ebb:21b17f8b2bc0e9511e276e3d57a23893067cefe5#e63f71718400508af68f2e1e99daa400`
- L0/L1/L4/L5/L1e: pass
- L2: skip, library package has no `bin/` directory.

## Build approach

- Source: SourceForge release tarball `mhash-0.9.9.9.tar.gz`.
- Upstream build system: Autotools.
- Recipe strategy: build static `libmhash.a` with public headers for downstream packages such as `mcrypt`.
- `config.guess` and `config.sub` are patched in `build()` when `settings.os=OHOS`.
- OHOS `configure` is invoked through the job-local shell and receives explicit LLVM binutils paths.
- Stale Autotools outputs shipped in the release tarball are removed after source extraction.
- OHOS `CPP` and `CXXCPP` are set explicitly because old Autoconf otherwise falls back to `/lib/cpp`.
- Out-of-source builds add both build and source include directories so generated `mhash_config.h` and source `mutils/*.h` headers are both visible.
- Autotools helper scripts such as `install-sh` use the job-local shell on OHOS.

## Upstream tests

The release source registers 5 official tests under `src/Makefile.am`:

- `hash_test.sh`
- `hmac_test`
- `keygen_test`
- `rest_test`
- `frag_test`

The recipe runs `make check` after building.

OHOS r7 result: 5/5 passed. `hash_test.sh` originally depends on `perl` only to
generate one-million `a` characters for standard digest vectors. The OHOS
worker does not provide `perl`, so the recipe replaces that generator with an
equivalent `python3` command while keeping the upstream vectors and expected
digests unchanged.

## Consumer test

The Conan `test_package` builds a small C program against `mhash::mhash` and
verifies the MD5 digest of `abc`.

OHOS r7 result: 1/1 passed, including the runner L1e destructive negative test.
