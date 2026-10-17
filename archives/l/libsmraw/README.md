# libsmraw

libsmraw is a library to access the (Windows) Split RAW image format
(project status: experimental, licence LGPLv3+). It reads storage media
images stored as a single RAW file or split across multiple segment files
(`.000`/`.001`/… or fixed-size parts) and provides handles for reading the
image data, the basis of the `smrawmount`/`smrawverify` tools.

## OHOS adaptation

- Pure C library built with Autotools (`configure` / `Makefile.am` are shipped
  in the release tarball, no bootstrap needed). The 14 bundled libyal
  components (`libbfio`, `libcdata`, `libcerror`, `libcfile`, `libclocale`,
  `libcnotify`, `libcpath`, `libcsplit`, `libcthreads`, `libfcache`,
  `libfdata`, `libfvalue`, `libhmac`, `libuna`; plus the top-level `common/`
  shared support code) are built in-tree as standalone copies, so the recipe
  has no external Conan dependency.
- The shipped `configure` contains two `umask 077` statements. On the
  HarmonyOS HMDFS the resulting 0700 temporary directory cannot be written to
  even by its creator (`config.guess` fails with `can't create .../dummy.c:
  Permission denied`), so the recipe rewrites those two occurrences to
  `umask 022` in the build copy and keeps `umask 022` for the whole build.
- The bundled `config.guess` / `config.sub` (timestamp 2023-06-23 vintage,
  same generation as libvsgpt 0-20240504) do not recognise HarmonyOS, so the
  recipe passes `--build/--host=aarch64-unknown-linux-gnu` explicitly for OHOS.
- Source-tree scripts cannot be executed directly on the device; `configure`
  is started through `CONFIG_SHELL` (`/data/service/hnp/bin/bash`) and the
  upstream `make check` entries through `LOG_COMPILER`.
- The Python bindings (`pysmraw`) are disabled (`--disable-python`); the
  delivered artefacts are the shared library, the headers and the
  `smrawmount`/`smrawverify` tools.
- Upstream tests run inside `make check` in the recipe `build()`, so the
  `conan create` log carries the upstream test readings. The release tarball
  does not ship the `tests/input/` fixture directory, so upstream
  `test_smrawverify.sh` skips by its own rule (`exit 77`).

## Delivered artefacts

- `lib/libsmraw.so.1.0.0` (default shared build)
- `include/libsmraw.h`, `include/libsmraw/*.h`
- `bin/smrawmount`, `bin/smrawverify` (declared in `commands.json`)
- `lib/pkgconfig/libsmraw.pc`
- `licenses/COPYING`, `licenses/COPYING.LESSER`

## References

- https://github.com/libyal/libsmraw
- https://github.com/libyal/libsmraw/wiki/Home
- https://github.com/libyal/libsmraw/wiki/Building
