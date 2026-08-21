# audiofile 0.3.6

`audiofile` is an Autotools C/C++ library for common audio file formats.

The recipe deliberately configures `--disable-flac`: FLAC is optional upstream
functionality and enabling it would require a separate packaged FLAC dependency.
The retained upstream suite contains 35 tests under `test/` and one
`libaudiofile/UnitTests` target, all invoked through `make check` in `build()`.

The consumer test writes a two-channel 16-bit WAV file through the public
`audiofile.h` API, reads it back, and checks its format, metadata, and samples.

## HarmonyOS validation (2026-08-21)

Real-machine `conan create` on OHOS/armv8 (clang 15, libc++, HongMeng Kernel
1.12.0) passes with EXIT=0. All 35 upstream tests pass and the test_package
WAV round-trip passes (100% tests passed, 0 tests failed out of 1).

Five portability patches were required, each addressing a distinct OHOS
platform limitation; none of them change upstream library behaviour.

### Patches

| Patch | Problem | Fix |
|---|---|---|
| 0001-config-ohos | 2012-era `config.guess`/`config.sub` do not recognise OHOS | Add `aarch64:HarmonyOS:*:*` to `config.guess` and `ohos-linux` triplet to `config.sub` |
| 0002-configure-umask | HMDFS `mktemp` creates tmp dirs with a different owner; `umask 077` makes them unwritable for the build user (`Permission denied` on `subs1.awk`) | `umask 077` -> `umask 000` in `configure`'s tmp directory creation |
| 0003-gtest-tr1-tuple | Bundled gtest 1.6.0 uses `<tr1/tuple>`; OHOS clang 15 + libc++ does not provide it (`fatal error: 'tr1/tuple' file not found`) | Set `GTEST_HAS_TR1_TUPLE=0` to force C++11 `<tuple>` |
| 0004-test-pathmax-narrowing | (1) OHOS musl libc does not expose `PATH_MAX` via `<limits.h>` (`use of undeclared identifier 'PATH_MAX'`); (2) `Sign.cpp` C++11 narrowing (`-kMinInt24` int32_t -> uint32_t) | (1) Define `PATH_MAX 4096` in 12 test files; (2) add `static_cast<uint32_t>` |
| 0005-test-tmpdir | Tests hardcode `/tmp` which is read-only on OHOS (`could not create temporary file`) | Use `$TMPDIR` (falling back to `.`) so `mkstemp` can create temp files |

### Additional recipe changes

- `generate()` adds `-lc++` to `extra_ldflags`: `sfcommands` mix C and C++
  (`AudioFormat.cpp`), but the C linker driver omits `-lc++` on OHOS, causing
  `undefined symbol: operator new(unsigned long)` etc.
- Source retrieval uses the checksum-pinned upstream GNOME release archive;
  the recipe does not depend on a workstation or device-local mirror.

### Build/test summary

| Item | Result |
|---|---|
| `conan create` (ohos-aarch64) | EXIT=0 |
| `make check` (35 non-FLAC tests) | All 35 passed |
| `libaudiofile/UnitTests` | Compiled and linked with patched gtest |
| `test_package` (WAV round-trip) | 100% tests passed, 0 tests failed out of 1 |

### Reproduction

```
git fetch elklu02 feat/audiofile-0.3.6
git switch --detach elklu02/feat/audiofile-0.3.6

conan create archives/a/audiofile/0.3.6 \
  -pr:h ci/conan/profiles/ohos-aarch64 \
  -pr:b ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --build=missing
```
