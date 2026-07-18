# gcli 2.12.0 Adaptation Notes

## Build Strategy

The Homebrew task tracks upstream gcli 2.12.0 from the official release
tarball hosted at `herrhotzenplotz.de`. gcli uses a handwritten `configure`
script and generated `Makefile.in`; it is not GNU autotools, so the recipe runs
the configure script directly instead of using Conan's Autotools helper.

The package is built as a CLI application. The upstream build requires
pkg-config modules named `libcurl` and `libcrypto`. There is no published
Conan recipe for the Homebrew curl task in the contest repository, so
the recipe uses the HarmonyOS PC libraries already installed under
`DEFAULT_PREFIX` and generates sanitized `libcurl.pc` and `libcrypto.pc` files
for upstream configure. Optional interactive or presentation features remain
disabled:

- `--disable-libedit`
- `--disable-libreadline`
- `--disable-liblowdown`
- `--disable-librt`
- `--release`

The generated pkg-config files are prepended to `PKG_CONFIG_PATH`, followed by
`$DEFAULT_PREFIX/lib/pkgconfig` and `$DEFAULT_PREFIX/share/pkgconfig`. This
avoids depending on an unpublished `curl` Conan package while still keeping the
build path explicit and reproducible inside the CI image.

## OHOS Notes

- `CCACHE=env` is passed to configure. Upstream stores the `CCACHE` value in
  Makefile command lines; using `env` is a no-op prefix and avoids a hard
  dependency on the `ccache` binary.
- `CPPFLAGS`, `LDFLAGS`, and the package run environment include
  `$DEFAULT_PREFIX/include` and `$DEFAULT_PREFIX/lib` so the system libcurl and
  libcrypto headers/libraries are visible during build and smoke tests.
- The install prefix is `/`, so `make install DESTDIR=<package_folder>` places
  `gcli` under `bin/gcli` and manpages under `share/man`.
- Optional readline/libedit/lowdown support is intentionally disabled because
  the non-interactive command paths do not need them and the extra dependencies
  would expand CI risk.

## Verification

Local verification covers Python syntax, YAML/JSON parsing, diff cleanliness,
and repository pre-PR audit. Remote OHOS CI must run the Conan build and
`test_package`. The test package only runs non-network commands:

- `gcli version`, checking the 2.12.0 version string and libcurl reporting.
- `gcli` with no arguments, checking general usage output.
