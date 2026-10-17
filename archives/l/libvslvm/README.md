# libvslvm

libvslvm is a library to access the Linux Logical Volume Manager (LVM2)
volume system format (project status: experimental, licence LGPLv3+). It
parses the LVM2 on-disk metadata (`LABELONE` physical volume label, metadata
areas and the LVM2 metadata text) and exposes volume groups, physical
volumes, logical volumes, segments and stripes.

## OHOS adaptation

- Pure C library built with Autotools (`configure` / `Makefile.am` are shipped
  in the upstream release tarball, no bootstrap needed). The 14 bundled libyal
  components (`libbfio`, `libcdata`, `libcerror`, `libcfile`, `libclocale`,
  `libcnotify`, `libcpath`, `libcsplit`, `libcthreads`, `libfcache`,
  `libfdata`, `libfvalue`, `libuna`, `libvslvm` proper) are built in-tree as
  standalone copies, so the recipe has no external Conan dependency.
- The shipped `configure` contains two `umask 077` statements. On the HarmonyOS
  HMDFS the resulting 0700 temporary directory cannot be written to even by its
  creator (`config.guess` fails with `can't create .../dummy.c: Permission
  denied`), so the recipe rewrites those two occurrences to `umask 022` in the
  build copy and keeps `umask 022` for the whole build.
- The bundled `config.guess` / `config.sub` (timestamp 2023-06-23) do not
  recognise HarmonyOS and this release's `config.sub` rejects `linux-ohos`
  (same-family libvsgpt 20240504 measured `Invalid configuration
  'aarch64-unknown-linux-ohos': OS 'ohos' not recognized`), so the recipe
  passes `--build/--host=aarch64-unknown-linux-gnu` explicitly for OHOS.
- Source-tree scripts cannot be executed directly on the device; `configure`
  is started through `CONFIG_SHELL` (`/data/service/hnp/bin/bash`) and the
  upstream `make check` entries through `LOG_COMPILER`.
- The Python bindings (`pyvslvm`) are disabled (`--disable-python`); the
  delivered artefacts are the shared library, the headers, `vslvminfo` and
  `vslvmmount`. All fuse-specific code of `vslvmmount` sits inside
  `#if defined( HAVE_LIBFUSE )` guards, so without libfuse the tool builds in
  the upstream "no mount support" form (`-V`/`-h` still work).
- Upstream tests run inside `make check` in the recipe `build()`, so the
  `conan create` log carries the upstream test readings.

## Delivered artefacts

- `lib/libvslvm.so.1.0.0` (default shared build)
- `include/libvslvm.h`, `include/libvslvm/*.h`
- `bin/vslvminfo` and `bin/vslvmmount` (declared in `commands.json`)
- `lib/pkgconfig/libvslvm.pc`
- `licenses/COPYING`, `licenses/COPYING.LESSER`

## References

- https://github.com/libyal/libvslvm
- https://github.com/libyal/libvslvm/wiki/Home
- https://github.com/libyal/libvslvm/wiki/Building
