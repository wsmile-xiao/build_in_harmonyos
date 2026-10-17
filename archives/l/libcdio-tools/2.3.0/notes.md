# libcdio-tools 2.3.0 packaging notes

## Scope

This package ships only the upstream libcdio 2.3.0 command-line tools:

- `cd-drive`
- `cd-info`
- `cd-read`
- `iso-info`
- `iso-read`
- `mmc-tool`

It depends on the existing mature `libcdio/2.3.0` Conan package. The recipe
does not vendor, rebuild, or repackage the libcdio libraries.

## Source

- Official URL: `https://github.com/libcdio/libcdio/releases/download/2.3.0/libcdio-2.3.0.tar.gz`
- SHA256: `37bcb13296febbcff9dc4485834bac09212cb463c31fcea52f70ee1dd3a5a5de`

The recipe intentionally records only the official upstream release URL.

## OpenDesk Verification

- Final job id: `20260924-154132-7dfcec-libcdio-tools-2.3.0-v4`
- Device: HarmonyOS aarch64, HongMeng Kernel 1.12.0
- Command: `conan create pkg -pr:b=<ohos-aarch64> -pr:h=<ohos-aarch64> --build=missing`
- `CREATE_EXIT=0`
- `TEST_PACKAGE_RESULT=PASS assertions=12 tools=6 behaviors=5`

The test package invokes the installed executables from the built package. It
does not test an in-tree copy or an empty placeholder.

Verified tool behavior:

- all six installed tools execute `--version` and report `2.3.0`
- `cd-drive --quiet` reports the compiled driver list
- `cd-info` analyzes the upstream CUE/BIN fixture with exact output comparison
- `cd-read` reads MODE1 sectors with exact output comparison
- `iso-info` lists the upstream ISO-9660 image with exact output comparison
- `iso-read` extracts an upstream file with byte-for-byte comparison

## Upstream Test Boundary

`make check` is not run inside this tool package. Upstream's check suite
rebuilds and exercises the in-tree libcdio libraries, driver tests, and example
programs, so those tests belong to `libcdio/2.3.0`. Repeating them here would
test a second local library build rather than the installed dependency used by
these tools.

The tool package instead runs consumer-level assertions against the installed
executables. No upstream check counts are claimed.

## Not Verified

Device operations in `mmc-tool` require a real MMC optical device. Only its
installed `--version` behavior was verified in this run. No claim is made about
MMC media operations.

## Failed Predecessors

- `20260924-153436-77dc8b-libcdio-tools-2.3.0-v2`, `CREATE_EXIT=1`.
  Conan's `get()` rejected an unsupported `mirrors` keyword. The source
  candidates were changed to the URL-list form supported by
  `conan.tools.files.get()`.
- `20260924-153903-5d189d-libcdio-tools-2.3.0-v3`, `CREATE_EXIT=1`.
  `cd-info.c` could not find the upstream-private `cdio_assert.h`. The direct
  clang compile now adds the upstream `lib/driver` include directory.
- `20260924-154132-7dfcec-libcdio-tools-2.3.0-v4`, `CREATE_EXIT=0`, passed.
