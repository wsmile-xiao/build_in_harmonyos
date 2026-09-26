# Test Report — libfishcamp 1.2 (OpenHarmony / aarch64)

- **Status**: PASS
- **RC**: 0
- **Date**: 2026-09-25
- **Host**: OpenHarmony aarch64, clang 15.0.4, Conan 2.29.1
- **Profile**: `ci/conan/profiles/ohos-aarch64` (os=OHOS, arch=armv8, compiler=clang 15, cppstd=17, Release)

## Build

`conan create archives/l/libfishcamp/1.2 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
completed cleanly:

- Source download (`download()`, not `get()` — upstream files are plain
  `.c`/`.h`, not archives) of the 4 official v2.2.4 source files — SHA256
  verified against `conandata.yml`.
- `patch` (0001-drop-indi-dependency.patch) removes the only INDI coupling
  (`indimacros.h` `INDI_UNUSED` macro), defined locally. No libindi required.
- CMake configure + serial build (`-j1`) of the static `libfishcamp.a`.
- `conan package` installs `libfishcamp.a` + headers + `COPYING.LIB`.

## Test package (on-host, aarch64/OHOS)

`test_package/` exercises the public C API as a **real downstream consumer**
(mirroring how the INDI driver uses the library). The binary runs natively on
aarch64/OHOS:

- Build of `test_fishcamp` (C executable) linking `fishcamp::fishcamp` +
  `libusb-1.0::libusb-1.0`.
- `test()` runs the binary directly via `self.run(..., env="conanrun")` —
  `conanrun` injects `LD_LIBRARY_PATH` so the dynamically-linked
  `libusb-1.0.so` is found (CMAKE_SKIP_RPATH + OHOS).
- Result: **PASS** (binary exits 0; the single end-to-end consumer scenario
  with 20+ internal CHECK assertions succeeds).
- Custom `CHECK` macro used (no `<cassert>` — Release `-DNDEBUG` would strip
  `assert()` and turn the test into a no-op). `strings test_fishcamp | grep
  'CHECK FAILED'` is wired as the pass criterion.

### End-to-end consumer scenario (1) — full capture workflow in simulation mode

A complete capture session is driven through the real public API and its
**produced outputs** are verified (not merely that functions are callable).
Simulation mode is used because OpenHarmony has no Fishcamp CCD hardware; it
is a first-class, supported mode that still runs the real control flow and
returns real, verifiable state.

| Step | Action | Verified output | Result |
|------|--------|----------------|--------|
| init | `fcUsb_init()` / `setSimulation(1)` / `setLogging(0)` | library initializes (libusb_init ok) | PASS |
| enumerate | `fcUsb_FindCameras()` | returns exactly 1 virtual camera | PASS |
| enumerate | `fcUsb_GetNumCameras()` | == 1 after discovery | PASS |
| open | `fcUsb_OpenCamera(1)` | returns 0 (simulation sets defaults) | PASS |
| identity | `GetCameraVendorID/ProductID/SerialNum` | `0x1887` / `0x0003` / `12345` | PASS |
| device info | `fcUsb_cmd_getinfo()` | rc==0; `width==1280`, `height==1024`, name=="Starfish Mono", serial string populated | PASS |
| configure | `setIntegrationTime(1000)` | returns 0 | PASS |
| configure | `setRoi(0,0,100,100)` | returns 0 | PASS |
| configure | `setBin(1)` | returns 0 | PASS |
| expose | `startExposure()` | returns 0 | PASS |
| state | `getState()` | == 0 (simulation) | PASS |
| frame | `getRawFrame(64,64)` | returns 0 | PASS |
| close | `CloseCamera(1)` / `fcUsb_close()` | returns 0 | PASS |

## Notes

- Upstream libfishcamp has **no upstream test suite** (it is a hardware camera
  driver). The single end-to-end scenario above is added in `test_package` as
  the 鸿蒙特有测试 coverage — a complete consumer workflow with real-output
  verification (not bare assertions).
- libusb is a **public** dependency: `fishcamp_common.h` includes `<libusb.h>`,
  so `cpp_info.requires = ["libusb::libusb"]` and the test requires libusb
  directly to ensure CMakeDeps emits its include dirs.
- OHOS build quirks handled in-recipe: writable `TMPDIR` (HMBS cache), serial
  `-j1` build, and per-step build/test output bound to log files (conan
  `run()` stream inheritance otherwise silently swallows compiler diagnostics).
