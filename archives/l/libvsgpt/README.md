# libvsgpt

libvsgpt is a library to access the GUID Partition Table (GPT) volume system
(project status: experimental, licence LGPLv3+). It reads both the GPT and the
protective/hybrid MBR partition entries and provides partition handles for
reading the partition data.

## OHOS adaptation

- Pure C library built with Autotools (`configure` / `Makefile.am` are shipped
  in the release tarball, no bootstrap needed). The 13 bundled libyal
  components (`libbfio`, `libcdata`, `libcerror`, `libcfile`, `libclocale`,
  `libcnotify`, `libcpath`, `libcsplit`, `libcthreads`, `libfcache`,
  `libfdata`, `libfguid`, `libuna`) are built in-tree as standalone copies, so
  the recipe has no external Conan dependency.
- The shipped `configure` contains two `umask 077` statements. On the HarmonyOS
  HMDFS the resulting 0700 temporary directory cannot be written to even by its
  creator (`config.guess` fails with `can't create .../dummy.c: Permission
  denied`), so the recipe rewrites those two occurrences to `umask 022` in the
  build copy and keeps `umask 022` for the whole build.
- The bundled `config.guess` / `config.sub` (timestamp 2023-06-23) do not recognise
  HarmonyOS and this release's `config.sub` rejects `linux-ohos` (`Invalid configuration
  'aarch64-unknown-linux-ohos': OS 'ohos' not recognized`), so the recipe passes
  `--build/--host=aarch64-unknown-linux-gnu` explicitly for OHOS.
- Source-tree scripts cannot be executed directly on the device; `configure` is
  started through `CONFIG_SHELL` (`/data/service/hnp/bin/bash`) and the
  upstream `make check` entries through `LOG_COMPILER`.
- The Python bindings (`pyvsgpt`) are disabled (`--disable-python`); the
  delivered artefacts are the shared library, the headers and `vsgptinfo`.
- Upstream tests run inside `make check` in the recipe `build()`, so the
  `conan create` log carries the upstream test readings.

## Delivered artefacts

- `lib/libvsgpt.so.1.0.0` (default shared build)
- `include/libvsgpt.h`, `include/libvsgpt/*.h`
- `bin/vsgptinfo` (declared in `commands.json`)
- `lib/pkgconfig/libvsgpt.pc`
- `licenses/COPYING`, `licenses/COPYING.LESSER`

## References

- https://github.com/libyal/libvsgpt
- https://github.com/libyal/libvsgpt/wiki/Home
- https://github.com/libyal/libvsgpt/wiki/Building
