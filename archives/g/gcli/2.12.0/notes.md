# gcli 2.12.0 Adaptation Notes

## Build Strategy

The Homebrew task tracks upstream gcli 2.12.0 from the official release
tarball hosted at `herrhotzenplotz.de`. gcli uses a handwritten `configure`
script and generated `Makefile.in`; it is not GNU autotools, so the recipe runs
the configure script directly instead of using Conan's Autotools helper.

The package is built as a CLI application. The recipe keeps the required
networking dependencies, `curl/8.19.0` and `openssl/1.1.1w`, and disables
optional interactive or presentation features:

- `--disable-libedit`
- `--disable-libreadline`
- `--disable-liblowdown`
- `--disable-librt`
- `--release`

gcli's configure script checks for pkg-config modules named `libcurl` and
`libcrypto`. Conan packages provide the dependency folders, and the recipe
adds those pkg-config directories to `PKG_CONFIG_PATH`. It also generates a
small `libcrypto.pc` shim for the Conan OpenSSL package so configure does not
depend on a system `/usr/local` OpenSSL installation.

## OHOS Notes

- `CCACHE=env` is passed to configure. Upstream stores the `CCACHE` value in
  Makefile command lines; using `env` is a no-op prefix and avoids a hard
  dependency on the `ccache` binary.
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
