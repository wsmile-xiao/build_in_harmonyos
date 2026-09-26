# libvmdk

libvmdk is a library to access the VMware Virtual Disk (VMDK) format
(project status: experimental, licence LGPLv3+). It reads sparse, monolithic
and split VMDK disk images — descriptor files, extent/grain tables and
(compressed) grain data — and is the basis of the `vmdkinfo`/`vmdkmount`
tools.

## OHOS adaptation

- Pure C library built with Autotools (`configure` / `Makefile.in` are shipped
  in the release tarball, no bootstrap needed). The 13 bundled libyal
  components (`libbfio`, `libcdata`, `libcerror`, `libcfile`, `libclocale`,
  `libcnotify`, `libcpath`, `libcsplit`, `libcthreads`, `libfcache`,
  `libfdata`, `libfvalue`, `libuna`; plus the top-level `common/` shared
  support code) are built in-tree as standalone copies and are not Conan
  dependencies; the one external Conan dependency is `zlib/1.3.2` (grain
  decompression: `libvmdk_compression.c` / `libvmdk_deflate.c`), wired through
  `AutotoolsDeps` (CPPFLAGS/LDFLAGS auto-detection; the shipped shared
  `m4/zlib.m4` 20240314 rejects an explicit `--with-zlib=<DIR>` value — its
  DIR branch sets the success state to `zlib` while the final gate tests
  against `yes`, which is never assigned, so the explicit form is not used).
- The shipped `configure` contains two `umask 077` statements. On the
  HarmonyOS HMDFS the resulting 0700 temporary directory cannot be written to
  even by its creator, so the recipe rewrites those two occurrences to
  `umask 022` in the build copy and keeps `umask 022` for the whole build.
- The bundled `config.guess` / `config.sub` (timestamp 2023-06-23 vintage,
  same generation as libvsgpt 0-20240504 and libsmraw 20240506) do not
  recognise HarmonyOS, so the recipe passes
  `--build/--host=aarch64-unknown-linux-gnu` explicitly for OHOS.
- Source-tree scripts cannot be executed directly on the device; `configure`
  is started through `CONFIG_SHELL` (`/data/service/hnp/bin/bash`) and the
  upstream `make check` entries through `LOG_COMPILER`.
- The Python bindings (`pyvmdk`) are disabled (`--disable-python`); the
  delivered artefacts are the shared library, the headers and the
  `vmdkinfo`/`vmdkmount` tools.
- Upstream tests run inside `make check` in the recipe `build()`, so the
  `conan create` log carries the upstream test readings. The release tarball
  does not ship the `tests/input/` fixture directory; `test_vmdkinfo.sh`
  skips by its own rule (`exit 77`) while `test_library.sh` falls back to
  running its input-driven programs without input, and `test_tools.sh` needs
  no fixtures.

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
