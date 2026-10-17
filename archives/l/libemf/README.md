# libEMF

libEMF implements a POSIX/GCC-compatible subset of the ECMA-234 Graphics
Device Interface (GDI) so that programs running on systems without a native
GDI (Grace, gnuplot, ...) can generate Enhanced Metafile (`.emf`) files.  The
package provides the `libEMF` library with its C API (`include/libEMF/emf.h`),
the bundled GDI/wine type headers, and the `printemf` metafile reader tool.

## OHOS adaptation

- Builds the official 1.0.14 release with its shipped Autotools files, with
  three portability patches (see `1.0.14/conandata.yml`): the HarmonyOS uname
  branch in `config.guess`, the `ohos` triplets in `config.sub`, and `umask
  022` for the `config.status` temporary directory.
- Runs the upstream `make check` suite inside the package build: three shell
  tests that compare the generated metafiles byte-for-byte against the golden
  files in `tests/emfs/`.
- Ships the shared library (`libEMF.so.1`) plus `bin/printemf`; the tool is
  declared in `commands.json`.
- `printemf` needs `--enable-editing` (upstream default: off) before it prints
  metafile contents; with the default configuration it validates that a
  metafile can be read and returns non-zero otherwise.

## Dependencies

None.  libEMF only uses the C/C++ runtime and POSIX threads (`-lpthread`
detected by the bundled `configure`); the optional Doxygen documentation
generator is not needed for the build.

## References

- https://sourceforge.net/projects/libemf/
- https://sourceforge.net/projects/libemf/files/libemf/1.0.14/
