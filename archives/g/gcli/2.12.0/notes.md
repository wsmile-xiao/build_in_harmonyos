# gcli 2.12.0 Adaptation Notes

## Build Strategy

The Homebrew task tracks upstream gcli 2.12.0 from the official release
tarball hosted at `herrhotzenplotz.de`. gcli uses a handwritten `configure`
script and generated `Makefile.in`; it is not GNU autotools, so the recipe runs
the configure script directly instead of using Conan's Autotools helper.

The package is built as a CLI application. The upstream build requires
pkg-config modules named `libcurl` and `libcrypto`. The recipe builds a private
static libcurl 8.15.0 from the official curl release tarball and points
`libcurl.pc` at that private install prefix. OpenSSL and zlib come from
published Conan recipes (`openssl/3.5.6` and `zlib/1.3.1`), so the build no
longer depends on worker-local copies of `libcurl`, `libssl`, `libcrypto`, or
`libz`. Optional interactive or presentation features remain disabled:

- `--disable-libedit`
- `--disable-libreadline`
- `--disable-liblowdown`
- `--disable-librt`
- `--release`

The generated pkg-config files are prepended to `PKG_CONFIG_PATH`, followed by
the system prefix pkg-config directories. CI build #8078 proved
`curl/8.19.0` is not resolvable from the ohpcd Conan remote, so the recipe must
not declare that dependency. CI build #8121 then showed some workers have
linkable OpenSSL libraries without OpenSSL headers, and CI build #8138 showed
other workers have no linkable `libcurl`, `libssl`, or `libcrypto` in
`DEFAULT_PREFIX/lib`. Building private curl against Conan openssl/zlib removes
that worker variance. CI build #8211 then showed curl 8.15.0's bundled
`config.sub` rejects `aarch64-unknown-linux-ohos`; before configuring curl, the
recipe wraps that helper to accept `*-linux-ohos` and delegate all other inputs
to the original upstream script. CI build #8287 then reached curl
`config.status` and failed because configure's `umask 077` made temporary awk
helper files unreadable on HMDFS. The recipe changes that private curl
configure umask to `022` before running it. CI build #8307 then built and
packaged gcli successfully, but failed during the test graph because Conan had
skipped the openssl/zlib binaries and `package_info()` tried to join a `None`
package folder. The run environment now prepends dependency library paths only
when Conan exposes the dependency package folder.

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
- `CPPFLAGS` includes the private curl, Conan OpenSSL, Conan zlib, resource,
  and `$DEFAULT_PREFIX/include` directories. `LDFLAGS` includes the matching
  private/Conan library directories plus `$DEFAULT_PREFIX/lib`.
- `package()` signs the installed `gcli` binary when the HarmonyOS
  `binary-sign-tool` is available, so `test_package` can execute it on CI.
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

The Python smoke helper uses explicit `SystemExit` failures instead of
`assert`, so the checks remain active even if Python is invoked with
optimization flags.
