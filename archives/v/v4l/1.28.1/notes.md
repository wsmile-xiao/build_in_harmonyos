# v4l 1.28.1 adaptation notes

## Environment

- Upstream project: v4l-utils
- Build system: Meson
- Date: 2026-09-28
- Status: built on OHOS (recipe ported from 1.32.0)

## Build flow

The Conan recipe downloads upstream `v4l-utils-1.28.1.tar.xz` and configures a
minimal library-focused Meson build. Optional applications and feature-heavy
subsystems are disabled by default. The recipe reuses the 1.32.0 OHOS adaptation
with one difference (see finding #5).

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
| 5 | OHOS lacks `perl` and `argp` in the runner image; unlike 1.32.0, 1.28.1 no longer references `intl` at all in `meson.build`. | Upstream Meson treats `perl`/`argp` as required in some paths even for the minimal library build. | OHOS builds patch `prog_perl` to optional, neutralize the `argp` probe, add the `include` include dir (the `if linux` guard does not fire on OHOS), define the missing `V4L2_PIX_FMT_NV12_16L16` fourcc fallback, and gate the CEC subdirs on `prog_perl.found()` (they use perl code generation). The 1.32.0 `dep_intl` patch is dropped because 1.28.1 has no `intl` dependency. |
| 6 | The OHOS UAPI headers do not define `V4L2_PIX_FMT_NV12_16L16`. | `libv4lconvert.c` fails to compile. | Define the upstream fourcc fallback when the macro is absent. |
| 7 | Meson install skips symlink creation on OHOS. | Consumers link via `libv4l*.so` but the loader needs SONAME files such as `libv4l2.so.0`. | Package real copies of `.so`, `.so.0`, and intermediate SONAME aliases. |
| 8 | Installed/copied OHOS ELF files must be signed after packaging. | The loader reports missing or unloadable shared libraries even when `LD_LIBRARY_PATH` is correct. | Package step signs all ELF files under `lib/` and `bin/` with `binary-sign-tool -selfSign 1`. |
| 9 | `utils/meson.build` has no `v4l-utils` top-level guard and unconditionally enters `libcecutil`, which uses `prog_perl` for code generation. | With `perl` absent, configure fails on OHOS. | OHOS gates the four CEC subdirs (`libcecutil`, `cec-ctl`, `cec-follower`, `cec-compliance`) on `prog_perl.found()`. |

## Verification

Local preflight (recipe parse/export):

```bash
python -m py_compile archives/v/v4l/1.28.1/conanfile.py archives/v/v4l/1.28.1/test_package/conanfile.py
conan inspect archives/v/v4l/1.28.1
conan export archives/v/v4l/1.28.1
git diff --check -- archives/v/v4l/1.28.1
```

OHOS real-device verification:

- To be filled after `finish` (conan create + test_package on OHOS aarch64).
- Expected consistent with 1.32.0: L0/L1/L4/L5 pass, L2 skip (no bin/ dir), L1e destructive negative test pass.

Upstream test handling:

- Meson registered tests: none for this upstream build.
- EDID parser corpus: expected comparable to 1.32.0 (23/24 raw pass; the single
  non-zero sample is documented upstream as not yet parsable).
- Device/kernel-module tests (`test-media`, `v4l2-compliance`, `cec-compliance`)
  cannot run on the current worker (no `/dev/video*`, no `/dev/media*`, no
  `modprobe`, no `udevadm`, no writable `/dev/kmsg`).

Pending optional verification on a suitable device-test host:

- Run optional device-level tests on a machine exposing video/media nodes.
- R40 adaptation completeness requires manual confirmation for real V4L2/media
  capture/control, pixel conversion, buffer management, and compliance tests on
  a host with suitable `/dev/video*` or `/dev/media*` devices.
