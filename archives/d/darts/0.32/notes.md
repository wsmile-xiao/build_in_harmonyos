# darts 0.32 OpenHarmony adaptation

## Source

- Upstream: http://chasen.org/~taku/software/darts/
- Archive: http://chasen.org/~taku/software/darts/src/darts-0.32.tar.gz
- SHA256: `0dfc0b82f0a05d93b92acf849368e54bf93f1de8ffb31ba0a21e45ab9e269285`
- Embedded directory: `darts-0.32`
- License: BSD-3-Clause (also ships LGPL text)

## Adaptation

- Autotools project (configure + Makefile). Builds `mkdarts` and `darts` utilities and installs header `darts.h` to `includedir`.
- Disables optional zlib (`--without-zlib`) to avoid extra dependency; upstream feature is optional compression support.
- Patches `config.sub` (1999 vintage) to recognise `aarch64` CPU and `linux-ohos` OS:
  - `0001-config-sub-ohos.patch` adds `linux-ohos` to KERNEL-OS case and OS pattern list, and `aarch64` to CPU types.
- On OHOS sets explicit triplets `--build=aarch64-linux-ohos --host=aarch64-linux-ohos` via AutotoolsToolchain (same pattern as aalib/1.4p5).
- Keeps upstream shared/static logic out – project produces only executables and header, no shared library to worry about system shadowing (R26 not applicable).
- Runs upstream `make check` in `build()` (TESTS=test1.sh).

## Verification

- `make check`: upstream ships `tests/test1.sh` which runs `mkdarts linux.words` -> `darts` query, greps for "not found". Expected 1/1 pass when tools build. On OHOS device the same harness is executed via `autotools.make(target="check")`.
- `test_package/darts_test`: builds small in-memory DoubleArray (5 keys), checks `build()` returns 0, `size()` >0, `exactMatchSearch` for present/absent keys, `commonPrefixSearch`, `save`/`open` round-trip (5 assertions consolidated in one executable, reported as 1 case).

## Notes

- Original `config.guess` does not know OHOS uname output; explicit `--host/--build` avoids guessing.
- Header is header-only (`darts.h`); consumers need only `-I` and no link libs (`cpp_info.libs = []`).
- Utilities `mkdarts` and `darts` install to `libexec/darts` per upstream Makefile.am; package_info exposes `libexec/darts` as bindir for optional use.
