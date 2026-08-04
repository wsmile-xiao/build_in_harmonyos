# mcrypt 2.6.8 upstream test inventory

Date: 2026-07-31

## Release test inventory

The 2.6.8 release source was inspected on the OHOS old-port worker after the
Conan `source()` step downloaded and unpacked
`mcrypt-2.6.8.tar.gz`.

No official test entries were found:

- `Makefile.am` / `Makefile.in`: no `TESTS`, `check_PROGRAMS`, or
  `check-local`.
- `src/Makefile.am` / `src/Makefile.in`: no `TESTS`, `check_PROGRAMS`, or
  `check-local`.
- No dedicated `tests/` directory is present in the release source.

Current official upstream test count: `0/0`.

## OHOS execution status

Initial old-port execution was blocked before package-level tests could run:

- SSH port: old port `56267`.
- Runner mode: `heavy` with `--try-lock`.
- run_dir:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-mcrypt-mcrypt-2.6.8-conan-r4-llvm-tools-20260730-104946-25250`.
- L0: pass.
- `configure` result: failed with `*** libmcrypt was not found`.

The old-port worker has no target-side `libmcrypt-config`, `mcrypt.h`,
`libmcrypt.a`, `mhash.h`, or `libmhash.a` under `$HOME/usr/local`. The local
repository also had no `libmcrypt` or `mhash` archive recipe available in that
job-local Conan cache, so this run was recorded as dependency-chain blocked.

After adapting and building the dependency chain in the same new-port job-local
Conan cache, new-port r11 first completed the stream-mode package validation:

- SSH port: new port `33332`.
- Runner mode: `heavy` with `--try-lock`.
- Lock wait: 0 seconds.
- run_dir:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-mcrypt-mcrypt-2.6.8-newport-r11-chain-rev008d-20260731-163403-10827`.
- Exit code: 0.
- Full ref:
  `mcrypt/2.6.8#008d0494b34271acf42d727094ead70b:8e6b4daae512b833db9495d8b0e8baa3acf64547#57cc24d5db5de60974d1af03950534d8`.
- Dependency refs:
  - `zlib/1.3.1#90ec87a7f2894cf25103a42512d394d6:6b129b068851896169fae42d399fa922d239ce8a#9c9ba7bb9d5b88079ba56f57303339c9`
  - `mhash/0.9.9.9#974b33885624a6e6ddd418a702a32ebb:21b17f8b2bc0e9511e276e3d57a23893067cefe5#3d98d49d3194718e8b5434e2493a3461`
  - `libmcrypt/2.5.8#2820bfa0ce1d46c81cbf222b30627530:21b17f8b2bc0e9511e276e3d57a23893067cefe5#9e537cb022689b229eccc56201e46c27`

New-port r23 is the current validation after removing runtime-generated source
rewrites and adding file-path package coverage:

- SSH port: new port `33332`.
- Runner mode: `heavy` with `--try-lock`.
- Lock wait: 0 seconds.
- run_dir:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-2.6.8-mcrypt-2.6.8-local-r1-conan-20260731-224359-55995`.
- Exit code: 0.
- Full ref:
  `mcrypt/2.6.8#1232e6d32243d0abac7c9ac8efcd04d8:8e6b4daae512b833db9495d8b0e8baa3acf64547#84ce92feec5cab317729dc0d43bd52b5`.
- Dependency refs:
  - `zlib/1.3.1#90ec87a7f2894cf25103a42512d394d6:6b129b068851896169fae42d399fa922d239ce8a#9c9ba7bb9d5b88079ba56f57303339c9`
  - `mhash/0.9.9.9#974b33885624a6e6ddd418a702a32ebb:21b17f8b2bc0e9511e276e3d57a23893067cefe5#3d98d49d3194718e8b5434e2493a3461`
  - `libmcrypt/2.5.8#2820bfa0ce1d46c81cbf222b30627530:21b17f8b2bc0e9511e276e3d57a23893067cefe5#9e537cb022689b229eccc56201e46c27`

## Added consumer test

`test_package/test_mcrypt.py` executes the packaged `mcrypt` binary and verifies:

- `mcrypt --version` reports `2.6.8`.
- stdin/stdout encryption/decryption roundtrip succeeds with the packaged binary.
- File-path encryption/decryption roundtrip succeeds with the packaged binary.

Current new-port r23 output:

```text
Mcrypt v.2.6.8 (aarch64-unknown-linux-ohos)
mcrypt stdin/stdout roundtrip ok
mcrypt file path roundtrip ok
```

Added test pass rate: `3/3 (100.00%)`.

Manual old-port pre-fix probing exposed a file-path crash when the operand was
placed after upstream's variable-length `-k` key list. The current package-level
test uses the unambiguous file-before-key CLI order and covers the file-path CLI
path directly. The recipe also carries a formal source patch that removes
upstream's undefined `fflush()` calls on read-only input streams.
