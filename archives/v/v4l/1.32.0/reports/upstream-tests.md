# v4l 1.32.0 upstream test handling

Date: 2026-07-30
Device: OHOS real device, old SSH port 56267

## Upstream test inventory

The upstream release does not register Meson `test()` entries for this build.
Test assets are source-level tools, scripts, and input corpora:

- `utils/edid-decode/test/*.test`: 24 parser input samples.
- `utils/v4l2-compliance/*`: V4L2 compliance tool sources.
- `utils/cec-compliance/*`: CEC compliance tool sources.
- `contrib/test/meson.build`: 8 always-defined test/example executables
  (`ioctl-test`, `sliced-vbi-test`, `sliced-vbi-detect`, `v4l2grab`,
  `driver-test`, `mc-nextgen-test`, `stress-buffer`, `capture-example`) plus
  optional X11/GL/SDL examples.
- `contrib/test/test-media`: kernel-module/device test runner for `vivid`,
  `vim2m`, `vimc`, `vicodec`, `vidtv`, `visl`, `cec`, and `cec-pwr`.

## Executed on OHOS

Run dir:
`/storage/Users/currentUser/ohos-test-runs/codex-a-v4l-v4l-1.32.0-upstream-edid-r4-20260730-035657-16632`

Procedure:

1. Reused the OHOS Meson build configured with `with_utils=True`.
2. Built only the non-device `utils/edid-decode/edid-decode` target.
3. Signed the resulting OHOS ELF with `binary-sign-tool -selfSign 1`.
4. Ran the executable against all 24 files in `utils/edid-decode/test/*.test`.

Result:

- Raw execution: 23/24 passed.
- Expected-pass corpus: 23/23 passed.
- The single non-zero sample was `vesa-displayid-fixed-length.test`, which the
  upstream README documents as a DisplayID sample that edid-decode cannot yet
  parse. The observed output was `No EDID header found ...`.

## Not executable on this worker

The current OHOS worker cannot run the device/kernel-module upstream tests:

- No `/dev/video*` nodes.
- No `/dev/media*` nodes.
- `modprobe` is missing.
- `udevadm` is missing.
- `/dev/kmsg` is not writable.
- `/proc/config.gz` is not readable.
- The shell user has UID resolution issues (`id: bad uid 20020108`).

This blocks `contrib/test/test-media` and practical `v4l2-compliance` /
`cec-compliance` device validation. Those tests require root-level control of
kernel media test modules and real or virtual V4L2/media/CEC device nodes.

## Utility build probes

`with_utils=True` was probed separately from the default minimal libv4l package.
The full utility set is not the default package surface. Probes found additional
tool-only blockers that are unrelated to the default library package:

- CEC utility generation assumes `perl`; OHOS worker does not provide it.
- Some utility targets assume Linux-style include selection and optional GNU
  `argp` headers.

The default package remains library-focused and is validated by the Conan
consumer test package. The executable upstream tests that can run without
media devices are represented by the EDID corpus above.
