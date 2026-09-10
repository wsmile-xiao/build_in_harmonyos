# cloop 3.14.1.3-nmu1 adaptation notes

## Scope

This is a Path B knowledge-extension adaptation. The Debian NMU source contains both a Linux kernel module and user-space utilities. HarmonyOS PC receives the user-space utilities only; attempting to build `cloop.ko` is outside the platform boundary.

## Source and dependency

- Source: Code7R/cloop `debian/sid`, commit `e6104fb74bda34e184fe92fa080099b0c4c96627`
- Source archive SHA256: `9df0dc8525b4e26017b7d546fcf5f8dded61c2045c3c7e65f80a2ccb592f65a8`
- Direct Conan dependency: `zlib/1.3.1`

## Adaptation findings

1. The bundled advancecomp `config.guess` reports `cannot guess build type` on `aarch64` HarmonyOS. The recipe passes explicit `--build` and `--host` values.
2. The generated Autoconf scripts create `confstatXXXXXX` with `umask 077`. HMDFS preserves the restrictive mode and then rejects writes to the generated directory. The patch changes this generated-script mode to `022`.
3. The old C++ source calls `bind` without global qualification. OHOS libc++ exposes `std::bind`, producing an overload-resolution failure. `::bind` selects the POSIX socket API.
4. The OHOS sysroot does not define Linux `loff_t`. The extractor's offset array and counters use `int64_t`, retaining the 64-bit serialized layout.
5. The recipe copies `advfs` into both command names and explicitly restores executable bits because HMDFS may reject hard-link replacement and may not preserve mode bits when copying files.

## Verification

- User-space build: `advancecomp-1.15/advfs` and `extract_compressed_fs` compiled with clang, `-j1`.
- Consumer test: an 8192-byte input was compressed with a 65536-byte block and extracted; the original prefix matched and the remaining bytes were verified to be zero padding.
- Upstream regression: the upstream `make check-local` target was attempted. The distributed Makefile invokes an obsolete `advfs` command syntax (`check.zip` as an input), so it fails before functional assertions. This is recorded rather than counted as a pass.
- No upstream test files were modified.
---

**编译结束**: 2026-09-09 16:52
**最终状态**: built
