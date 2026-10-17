# liblzxcomp 20050705 verification report

## Environment

- OHOS aarch64 target: clang 15.0.7 (OHOS SDK), Conan 2.29.1 (OHOS adapted)
- Profile: ohos-aarch64 (`ci/conan/profiles/ohos-aarch64`)
- Local dev: x86_64 WSL (Ubuntu, gcc 11.4.0) used for native runtime execution of
  the same patched sources and for an end-to-end `conan create` (aarch64 binaries
  cannot run locally: qemu guest loader `/lib/ld-linux-aarch64.so.1` absent,
  OHOS sysroot libc is a link stub)

## Verification

- `conan create archives/l/liblzxcomp/20050705 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`: **exit 0**
  - 3 patches applied (0001 lz_nonslide.c, 0002 lz_nonslide.h, 0003 lzx_config.h)
  - `make CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j1` -> `liblzxcomp.a`
  - test_package compiled + linked with the packaged library
- **Upstream test `lzx_test.c` — N=1/1 executed, PASS**
  - In-tree copy: `test_package/lzx_test.c`, byte-identical to
    `lzx_compress/lzx_test.c` (sha256 `217d2002d7f71586ddf1d45c6fbdb1d05055fd29d7df5b4deb763c98a061dad2`)
  - Built as target `lzx_test2`, matching upstream Makefile target `lzx_test2`
    (links `$(OBJS2)` = the nonslide objects packaged in `liblzxcomp.a`)
  - Executed by `test_package/conanfile.py::test()` with a CMake-generated
    deterministic corpus on stdin, so it runs on every CI build (OHOS aarch64)
  - Native x86_64 run: `compressed: 896, uncompressed 163840, ratio 99.453125`,
    RC=0, out 900 bytes for 145600 bytes input
  - Full evidence: `reports/upstream-test-evidence.md`
- L1 consumer test (HARMONYOS-specific, `test.c`): 512KiB repetitive input,
  memory backend, real API `lzx_init` -> `lzx_compress_block` -> `lzx_finish`
  - native run `in=524288 out=1372` => **PASS** (compresses, no crash)
- L1e R34 destructive check: `lib/` + `include/` moved away => CMake configure
  fails ("Library 'lzxcomp' not found in package"), `conan test` exits non-zero
  => test genuinely depends on the package
- L1c: upstream has no `check`/`ctest` target (Makefile only defines
  `lzx_test`/`lzx_test2`), so there is no upstream suite to run in `build()`
- L2: no bin/ artifacts (library only), skipped
- L4 checksec: no dangerous patch functions
- L5: lib/ has content, include/ has the 3 public headers
- R38: not a CLI tool -> commands.json not required
- Patches:
  - 0003-lzx_config.h: byte-order via `__BYTE_ORDER__` (was `#if BYTE_ORDER == BIG_ENDIAN`, silently true on little-endian)
  - 0002-lz_nonslide.h: add `typedef unsigned char u_char;` for musl/OHOS libc
  - 0001-lz_nonslide.c: fix 64-bit heap overflow in `memset(lentab, 0, sizeof(*prevtab) * chars)` (size should be `sizeof(*lentab)`)

## Packaged headers

`include/` ships `lzx_compress.h`, `lzx_constants.h` (consumer API) and
`lzx_config.h` (byte-order config required by the upstream `lzx_test.c` harness
and fixed by patch 0003).

## Known limits

- `lzx_config.h` big-endian branch cannot be exercised: all current OHOS targets
  are little-endian (the patched detection uses compiler builtins, so the branch
  is a no-op on AArch64 little-endian)
- liblzxcomp is compression-only (upstream provides no decoder), so no
  decompress round-trip assertion is possible inside this package
- `options.shared=True` silently degrades to the static archive: the upstream
  Makefile has no `.so` target (recorded as a P3 audit note, not a build failure)
