# gcli 2.12.0 Adaptation Notes

## Build Strategy

The Homebrew task tracks upstream gcli 2.12.0 from the official release
tarball hosted at `herrhotzenplotz.de`. gcli uses a handwritten `configure`
script and generated `Makefile.in`; it is not GNU autotools, so the recipe runs
the configure script directly instead of using Conan's Autotools helper.

The package is built as a CLI application. The upstream build requires
pkg-config modules named `libcurl` and `libcrypto`. The recipe uses the
uploaded `curl/8.19.0` Conan package for libcurl headers/libraries and keeps
libcrypto on the HarmonyOS PC system prefix. It generates sanitized
`libcurl.pc` and `libcrypto.pc` files for upstream configure. Optional
interactive or presentation features remain disabled:

- `--disable-libedit`
- `--disable-libreadline`
- `--disable-liblowdown`
- `--disable-librt`
- `--release`

The generated pkg-config files are prepended to `PKG_CONFIG_PATH`, followed by
the Conan curl package's pkg-config directory and the system prefix pkg-config
directories. CI build #8038 showed configure could be satisfied by system
libcurl metadata while the later compile still failed on missing
`curl/curl.h`; using the Conan curl package makes the header path explicit for
both configure and Makefile compile rules.

## OHOS Notes

- `CCACHE=env` is passed to configure. Upstream stores the `CCACHE` value in
  Makefile command lines; using `env` is a no-op prefix and avoids a hard
  dependency on the `ccache` binary.
- The recipe patches upstream configure's `find_program()` helper before
  running it. OHOS shell command lookup can return values such as
  `realpath=realpath`, which made the original `[ -x $(command -v ...)]` probe
  fail before configure reached the compiler checks.
- The upstream tarball ships `parser.y` and `lexer.l`, but not generated
  `lex.yy.c`. CI workers provide `yacc` but may not provide `lex`, so the
  recipe patches `Makefile.in` to copy a bundled hand-written `pgen` lexer
  source instead of invoking `lex`.
- `CPPFLAGS`, `LDFLAGS`, and the package run environment include the Conan curl
  package include/lib directories plus `$DEFAULT_PREFIX/include` and
  `$DEFAULT_PREFIX/lib`, so libcurl headers and libcrypto libraries are visible
  during build and smoke tests.
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
