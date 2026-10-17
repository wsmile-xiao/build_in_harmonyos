# squashfs-tools-ng 1.3.2 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15 (ohos-aarch64 conan profile)
- Conan 2.29.1 (OHOS adapted)

## Verification

- `conan create` (W3): exit 0 — G2 clean build PASS, G3 system-lib isolation PASS, G4 artifact completeness PASS
- `W3 local CI simulation` (setup.sh + build_and_test.sh): exit 0
- L0: passed (structure, junk check, settings, commands.json)
- L1: passed (test_package runs, tools respond)
- L2: tools executed directly in a clean environment (`env -i`) with no
  conanrun env — all 5 CLI tools answer `--version` and print
  `gensquashfs (squashfs-tools-ng) 1.3.2` style output. This works because
  zstd is linked statically (readelf shows NEEDED libc.so only, no
  libzstd.so.1 — earlier iterations that linked zstd dynamically failed
  here with exit 127).
- L4: static security scan passed
- L5: artifact baseline passed

## Upstream test suite (make check, R51)

Upstream ships 67 registered tests under tests/ (autotools framework).

- Test cases: 67
- Passed: 67
- Failed: 0
- Skipped: 0
- XFAIL: 0

History: the first local run failed 12 xfrm/table/xattr tests with exit 127
(registry zstd/1.5.6 ships only shared libs; test binaries could not find
libzstd.so.1 at runtime). Two fixes followed, each re-verified with a full
build:

1. LD_LIBRARY_PATH injection for all dependency libdirs (make check env).
2. Static zstd linking via zstd/1.5.7.1 (first registry version shipping
   libzstd.a) — the tools no longer depend on libzstd.so.1 at all.

After the fixes all 67 tests pass.

## test_package

The test script verifies all 5 CLI tools (`gensquashfs`, `rdsquashfs`,
`sqfs2tar`, `tar2sqfs`, `sqfsdiff`) answer `--version` with the expected
`squashfs-tools-ng` banner, then performs three functional flows:

1. Round-trip: create a SquashFS image from a source directory with
   gensquashfs, unpack it with rdsquashfs, diff the extracted file.
2. Tar interop: tar -> tar2sqfs (reads tar from stdin) -> sqfs2tar -> tar
   extract -> diff.
3. sqfsdiff: compares two images generated from the same source content.

- Assertions: 12
- Passed: 12
- Failed: 0

## Result

The recipe was verified on an OpenHarmony aarch64 device with 67/67 upstream
tests passing, tools statically linked against zstd (no runtime
libzstd.so.1 dependency), and is eligible for published status.
