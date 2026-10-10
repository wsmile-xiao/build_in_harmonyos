# libvmdk

libvmdk is a library to access the VMware Virtual Disk (VMDK) format
(project status: experimental, licence LGPLv3+). It reads sparse, monolithic
and split VMDK disk images — descriptor files, extent/grain tables and
(compressed) grain data — and is the basis of the `vmdkinfo`/`vmdkmount`
tools.

Adapted versions: `20240510` and `20260714` (both from the upstream GitHub
release asset channel, `libvmdk-alpha-<version>.tar.gz` — the alpha asset is
the only published release asset for these tags; the codeload git tarball of
tag `20260714` is a bare source snapshot without the generated `configure`
and without the 13 bundled libyal components, so it is not usable).

## OHOS adaptation (common to both versions)

- Pure C library built with Autotools (`configure` / `Makefile.in` are shipped
  in the release tarball, no bootstrap needed). The 13 bundled libyal
  components (`libbfio`, `libcdata`, `libcerror`, `libcfile`, `libclocale`,
  `libcnotify`, `libcpath`, `libcsplit`, `libcthreads`, `libfcache`,
  `libfdata`, `libfvalue`, `libuna`; plus the top-level `common/` shared
  support code) are built in-tree as standalone copies and are not Conan
  dependencies; the one external Conan dependency is `zlib/1.3.2` (grain
  decompression: `libvmdk_compression.c` / `libvmdk_deflate.c`), wired through
  `AutotoolsDeps` (CPPFLAGS/LDFLAGS auto-detection; the shipped shared
  `m4/zlib.m4` rejects an explicit `--with-zlib=<DIR>` value — its DIR branch
  sets the success state to `zlib` while the final gate is not satisfied by
  it, so the explicit form is not used).
- The shipped `configure` contains two `umask 077` statements. On the
  HarmonyOS HMDFS the resulting 0700 temporary directory cannot be written to
  even by its creator, so the recipe rewrites those two occurrences to
  `umask 022` in the build copy and keeps `umask 022` for the whole build.
- The bundled `config.guess` cannot identify this build host (`uname -s` =
  "HarmonyOS"): 20240510 ships the 2023-06-23 vintage and 20260714 ships the
  2025-07-10 vintage — both fail (the latter with "unable to guess system
  type"), so the recipe passes `--build/--host=aarch64-unknown-linux-gnu`
  explicitly for OHOS (the 2025 `config.sub` would accept `linux-ohos`, the
  guess stage is what fails).
- Source-tree scripts are started through `CONFIG_SHELL`
  (`/data/service/hnp/bin/bash`) rather than executed directly.
- The Python bindings (`pyvmdk`) are disabled (`--disable-python`); the
  delivered artefacts are the shared library, the headers and the
  `vmdkinfo`/`vmdkmount` tools.
- Upstream tests run inside `make check` in the recipe `build()`, so the
  `conan create` log carries the upstream test readings.

## Upstream tests per version

- `20240510` (shell-entry framework): `TESTS` registers 3 entry scripts +
  `check_PROGRAMS` registers 21 C programs = 24. The release tarball does not
  ship the `tests/input/` fixtures; `test_vmdkinfo.sh` skips by its own rule
  (`exit 77`) while `test_library.sh` falls back to running its input-driven
  programs without input (23 passed + 1 skip).
- `20260714` (autotest framework): `check_AUTOTESTS` registers 3 suites
  (`test_library`/`test_manpages`/`test_tools`, generated from `*.at` by
  `autom4te` at build time) + `check_PROGRAMS` registers 21 C programs = 24.
  `autom4te` comes from the OHOS hnp toolchain (`/data/service/hnp/bin`,
  autoconf 2.72), so the recipe prepends that directory to `PATH` before
  `make check`. Readings: 19 executed and passed + 5 upstream-rule skips
  (3 manpages because `MANPAGE_LINTER=no` by upstream default; the
  handle/support WITH_INPUT cases do not expand because the release asset
  ships no `tests/input/` fixtures — `generate_test_inputs.sh` emits an empty
  `test_inputs_*.at` and the `m4_foreach_w` over an empty list registers
  nothing).

## Delivered artefacts

- `lib/libvmdk.so.1.0.0` (default shared build)
- `include/libvmdk.h`, `include/libvmdk/*.h`
- `bin/vmdkinfo`, `bin/vmdkmount` (declared in `commands.json`)
- `lib/pkgconfig/libvmdk.pc`
- `licenses/COPYING`, `licenses/COPYING.LESSER`

## References

- https://github.com/libyal/libvmdk
- https://github.com/libyal/libvmdk/wiki/Home
- https://github.com/libyal/libvmdk/wiki/Building
