# audiowmark 0.6.5

Audiowmark is built with its Autotools project and packages the `audiowmark`
command-line tool. Single-precision FFTW (`fftw3f`), libsndfile, libgcrypt,
libzita-resampler, and mpg123
are supplied by Conan. Automake and Libtool are Conan build requirements for
`autoreconf`. FFmpeg/HLS and documentation are disabled because they are optional.

On OHOS, the generated `configure` script must be explicitly invoked with the
profile-provided `CONFIG_SHELL`, because the kernel does not execute scripts
through their shebang. The explicit `aarch64-unknown-linux-ohos` build triplet
also bypasses `config.guess`, which does not recognize HarmonyOS.

The `mpg123` Conan package publishes `mpg123.pc`, while audiowmark's
`configure.ac` requires `libmpg123`. The recipe copies the generated file to
`libmpg123.pc` in Conan's generator directory before configure runs.

The zita-resampler check uses `AC_LIB_HAVE_LINKFLAGS` rather than pkg-config,
so the recipe passes the Conan package folder through
`--with-libzita-resampler-prefix`.

Audiowmark requires the single-precision FFTW API (`fftw3f` and `fftwf_*`
symbols), so it depends on `fftw3f/3.3.10` rather than the double-precision
`fftw` package.

On OHOS shared build storage, Autoconf's generated `config.status` cannot
write files created with `umask 077`. The recipe regenerates with umask `000`
and replaces that generated temporary-file umask with `000` before configure.

OHOS armv8 validation completed successfully. All 14 upstream test targets
passed after the three pipe-based scripts were adapted to equivalent file-based
commands. The test package also passed its version assertion and file-based
watermark round-trip assertion (2/2).

```bash
conan create archives/a/audiowmark/0.6.5 \
  -pr:h ci/conan/profiles/ohos-aarch64 \
  -pr:b ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --build=missing
```
