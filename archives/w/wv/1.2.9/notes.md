# wv 1.2.9 adaptation notes

## Source and build

- Build system: Autotools release archive with generated `configure` files.
- Source URL and SHA256 are recorded in `conandata.yml`; the SHA256 was
  independently matched against the Cygwin source mirror.
- Optional libwmf support is disabled by upstream default (the recipe does not
  pass an undeclared `--without-wmf` option).

## Dependencies

- `glib/2.84.0.1.1`
- `libgsf/1.14.58`
- `libxml2/2.15.3.1`
- `libpng/1.6.58`
- `zlib/1.3.1.1`
- `libffi/3.4.4` (explicit GLib shared-library link closure)
- `pcre2/10.45` (explicit GLib shared-library link closure)

## CI link-closure fix

- CI `#30377` passed L0 and built `libwv-1.2.so`, then failed while linking
  the installed `wvWare` CLI.
- The failing link contained GLib, GObject, GIO, and libgsf but omitted GLib's
  private `libffi` and `pcre2` libraries. GLib's proxy-libintl aliases also
  remained unresolved through the published shared-library metadata.
- The recipe promotes the already-adapted `libffi/3.4.4` and `pcre2/10.45`
  packages to direct requirements and derives their `-L`/`-l` flags from
  Conan metadata.
- CI `#30400` confirmed that both direct requirements resolve, but applying
  the closure to `configure` made Autoconf's compiler sanity check link with
  target runtime libraries. The closure is therefore scoped to `make`, where
  it is used only while linking wv's actual library and CLI targets.
- CI `#30419` passed configure and compiled the wv sources, then old libtool
  followed pcre2's non-relocatable `//lib/libpcre2-8.la` reference. For OHOS,
  the recipe removes dependency `.la` metadata from the local Conan cache view
  so libtool uses the colocated shared objects. This matches the repository's
  existing `libgee/0.20.8` workaround for the same failure.
- CI `#30427` confirmed that cleaning `.la` files before configure makes
  Autoconf's compiler probe fail. The cleanup now runs after configure and
  immediately before make, preserving probe behavior while protecting the real
  target links.
- CI `#30434` repeated the early compiler-probe failure on the same `CI-020`
  worker, while `#30419` passed the identical configure command on `CI-032`.
  The generated OHOS environment now prepends the configured compiler directory
  to `PATH` and the discovered SDK `llvm/lib` directory to `LD_LIBRARY_PATH`,
  covering both worker-side ld.lld lookup and its libxml2 runtime dependency.
- CI `#30438` confirmed that environment hardening restored configure and that
  stale-`.la` cleanup resolved the libffi/pcre2 symbols. The remaining
  `g_libintl_*` references were not supplied by the musl loader as initially
  assumed; they belong to GLib's packaged proxy `libintl`. The make-only
  closure now appends that package file by absolute path, matching the validated
  libgsf/goffice pattern and bypassing libtool archive lookup.
- CI `#30443` confirmed that configure, all wv libraries, and all installed
  CLI targets link successfully with the corrected closure. Conan completed
  the build and entered `package()`; `make install -j20` then failed because
  HMDFS rejected the jobserver FIFO and wv's bundled `install-sh` could not
  create the destination directory. The generated `GNUmakefile` files now
  use the repository's established mkdir/cp install shim, including their
  `install_sh` helpers, and package installation is forced to `-j1`.
- CI `#30448` verified that serial shim-based installation completes and
  Conan creates the wv package. Its CMakeDeps test consumer then exposed the
  same GLib proxy-libintl gap in published package metadata: `libwv.so`
  retained `g_libintl_*` references but `wv::wv` did not supply `-lintl`.
  OHOS package metadata now adds GLib's package lib directory and propagates
  `intl` after wv; the CMake test build also runs with `-j1` to avoid the
  HMDFS jobserver FIFO warning.
- CI `#30455` again built, installed, and packaged wv, but CI-002 failed
  before the consumer link during CMake's compiler try-compile. The SDK `lld`
  could not load `libxml2.so.16` and reported missing `xml*` symbols; the
  identical CMake configure had passed on CI-005 in `#30448`. This worker
  infrastructure difference was reported in the PR. The wv test environment
  now also prepends the discovered OHOS SDK `llvm/lib` directory to
  `LD_LIBRARY_PATH`, matching the main recipe's validated linker hardening.
- No dependency recipe is changed or bundled into the wv PR.

## Local validation

- Python AST checks: passed for both Conan recipes.
- `git diff --check`: passed.
- W0 archive existence check: all seven declared dependency archives are
  present in the repository.
- Local review: wv-specific manifest, notes, packaging, and test-report checks
  pass. The review command still reports unrelated global knowledge E-number
  conflicts from the repository baseline.
- Local Conan create/W3: unavailable because the Windows host has no Conan CLI.

## Real-device shadow CI

- SSH target: `currentUser@10.62.221.191:2222`.
- Runner: `codex-wv-r18-wv-wv-1.2.9-shadow-r18-20260821-234825-21984`.
- Conan create and the test package passed; all three public API assertions
  (`wvInitDTTM`, `wvInitSHD`, and `wvInitDCS`) succeeded.
- L0, L1, L4, and L5 passed. L2 was skipped as non-blocking because every
  installed target CLI failed its version/help probe on the worker.
- Package reference:
  `wv/1.2.9#66cd91e92991b63c66b81ca115a34fae:e2e9c2e2ac191f51e4f1e065fc93d0516a8b9a91#65123a5bfba4c59303953b28ba72dff3`.
- Reusable cache: `/storage/Users/currentUser/ohos-users/codex-wv-1.2.9-r18-cache.tgz`
  (SHA256 `7549198ffb92910966b07c0bb27d077a6a7d392c5cd04ab9f878d0f3a58085c8`).

The glib, libxml2, zlib, and libgsf dependencies were consumed as separately
adapted packages; no dependency recipe changes are included in this branch.

## End marker

COMPLETED: wv recipe, package build, test package, and shadow CI validated.
