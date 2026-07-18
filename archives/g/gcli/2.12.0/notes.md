# gcli 2.12.0 Adaptation Notes

## Build Strategy

The Homebrew task tracks upstream gcli 2.12.0 from the official release
tarball hosted at `herrhotzenplotz.de`. gcli uses a handwritten `configure`
script and generated `Makefile.in`; it is not GNU autotools, so the recipe runs
the configure script directly instead of using Conan's Autotools helper.

The package is built as a CLI application. The upstream build requires
pkg-config modules named `libcurl` and `libcrypto`. The CI image has libcurl
libraries under `DEFAULT_PREFIX`, but CI build #8038 showed the corresponding
development headers are not always installed. The recipe therefore vendors curl
8.15.0 public headers as build resources, generates a sanitized `libcurl.pc`
that points at those headers plus the system libcurl library, and keeps
libcrypto on the HarmonyOS PC system prefix. Optional interactive or
presentation features remain disabled:

- `--disable-libedit`
- `--disable-libreadline`
- `--disable-liblowdown`
- `--disable-librt`
- `--release`

The generated pkg-config files are prepended to `PKG_CONFIG_PATH`, followed by
the system prefix pkg-config directories. CI build #8078 proved
`curl/8.19.0` is not resolvable from the ohpcd Conan remote, so the recipe must
not declare that dependency. The build uses system libcurl for linking and only
vendors the official curl public headers needed for compilation.

CI build #8121 then showed the same CI image exposes `libcrypto` for linking
but does not expose OpenSSL development headers. Upstream only includes
`openssl/evp.h` for `EVP_Digest()` and `EVP_sha1()` in the GitLab merge request
code path, so the recipe ships a minimal build-only EVP declaration shim under
`res/headers/openssl/evp.h`. The compiled binary still links against the system
`libcrypto`; the shim does not replace cryptographic implementation code.

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
- `CPPFLAGS` includes the vendored resource header directory plus
  `$DEFAULT_PREFIX/include`; `LDFLAGS` and the package run environment include
  `$DEFAULT_PREFIX/lib`, so libcurl/libcrypto link and smoke-test paths stay on
  the CI image's installed libraries without adding an unpublished Conan
  dependency.
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
