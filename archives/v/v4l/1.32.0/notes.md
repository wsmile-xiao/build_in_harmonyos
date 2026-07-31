# v4l 1.32.0 adaptation notes

## Environment

- Upstream project: v4l-utils
- Build system: Meson
- Date: 2026-07-30
- Status: built on OHOS

## Build flow

The Conan recipe downloads upstream `v4l-utils-1.32.0.tar.xz` and configures a
minimal library-focused Meson build. Optional applications and feature-heavy
subsystems are disabled by default.

Key options:

```bash
-Dbpf=disabled
-Dgconv=disabled
-Djpeg=disabled
-Dlibdvbv5=disabled
-Dqv4l2=disabled
-Dqvidcap=disabled
-Dv4l2-tracer=disabled
-Dv4l-utils=false
-Dv4l-plugins=false
-Dv4l-wrappers=false
-Ddoxygen-doc=disabled
```

## Platform findings

| # | Finding | Impact | Handling |
|---|---------|--------|----------|
| 1 | Upstream is tightly coupled to Linux V4L2/media kernel UAPI headers and ioctl behavior. | Windows local builds are not representative. | Recipe validation allows only Linux and OHOS. |
| 2 | Full utilities pull optional Qt, BPF, DVB, gconv, JPEG, json-c, udev/systemd, and device runtime behavior. | A full package would need many extra dependencies and device checks. | Default recipe uses a minimal libv4l profile. |
| 3 | Device behavior requires `/dev/video*` or `/dev/media*`. | Link and negative-path tests do not prove capture/control behavior. | Test package references libv4l symbols and calls `v4l2_open("/dev/null")` to exercise the library error path without requiring a video device. |
| 4 | Windows tar extraction reports invalid argument on some linked source entries. | Local `conan create` on Windows is not a useful acceptance test. | Local verification stops at recipe parse/export. |
| 5 | OHOS lacks `perl`, `argp`, and `intl` in the runner image. | Upstream Meson treats them as required in some paths even for the minimal library build. | OHOS builds patch those probes to optional dependencies. |
| 6 | The OHOS UAPI headers do not define `V4L2_PIX_FMT_NV12_16L16`. | `libv4lconvert.c` fails to compile. | Define the upstream fourcc fallback when the macro is absent. |
| 7 | Meson install skips symlink creation on OHOS. | Consumers link via `libv4l*.so` but the loader needs SONAME files such as `libv4l2.so.0`. | Package real copies of `.so`, `.so.0`, and intermediate SONAME aliases. |
| 8 | Installed/copied OHOS ELF files must be signed after packaging. | The loader reports missing or unloadable shared libraries even when `LD_LIBRARY_PATH` is correct. | Package step signs all ELF files under `lib/` and `bin/` with `binary-sign-tool -selfSign 1`. |
| 9 | Full utility builds assume CEC `perl` code generation and Linux-only include selection. | `with_utils=True` probes fail before device tests can run. | OHOS gates CEC utility subdirs on `prog_perl.found()` and includes upstream `include/` for utility targets. |

## Verification

Local preflight completed on the workspace branch:

```bash
python -m py_compile archives/v/v4l/1.32.0/conanfile.py archives/v/v4l/1.32.0/test_package/conanfile.py
conan inspect archives/v/v4l/1.32.0
conan export archives/v/v4l/1.32.0
git diff --check -- archives/v/v4l
```

OHOS real-device verification:

- Runner: old SSH port, heavy mode with `--try-lock`.
- Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-v4l-v4l-1.32.0-conan-oldport-r11-final-20260730-040335-19307`
- Full package reference: `v4l/1.32.0#e5817ff90eee6a420462265172ce3da0:f48ae6fda648e9644f211e4d6336d7799cc5a207#d440f8fb9defb1d26ea8ccab513d65f5`
- Result: `conan create` and `test_package` passed.
- CI summary: `L0=pass`, `L1=pass`, `L2=skip(no bin/ dir)`, `L4=pass`, `L5=pass`.
- L1e destructive negative test passed, confirming the test genuinely depends on packaged headers and libraries.

Upstream test handling:

- Report: `reports/upstream-tests.md`.
- Meson registered tests: none for this upstream build.
- Non-device EDID parser corpus: built and signed `utils/edid-decode/edid-decode`
  on OHOS, then ran all 24 `utils/edid-decode/test/*.test` inputs.
- EDID result: 23/24 raw pass; 23/23 expected-pass samples pass. The only
  non-zero sample is documented upstream as not yet parsable.
- Device/kernel-module tests (`test-media`, `v4l2-compliance`,
  `cec-compliance`) were identified but cannot run on the current worker
  because it has no `/dev/video*` or `/dev/media*`, no `modprobe`, no `udevadm`,
  no writable `/dev/kmsg`, and no root-level media module control.

Pending optional verification on a suitable device-test host:

- Run optional device-level tests on a machine exposing video/media nodes.
- R40 adaptation completeness requires manual confirmation for real V4L2/media
  capture/control, pixel conversion, buffer management, and compliance tests on
  a host with suitable `/dev/video*` or `/dev/media*` devices.
