# wv 1.2.9 test report

## Local preflight

- Conan recipe Python AST: pass.
- `git diff --check`: pass.
- W0 dependency archive presence: pass.

## PR CI regression

- CI `#30377`: L0 passed, including R38 `commands.json` and the exact
  `feat/wv-1.2.9` branch check.
- `libwv-1.2.so` linked successfully, but the `wvWare` executable failed with
  unresolved `g_libintl_*`, `ffi_*`, and `pcre2_*` symbols inherited from
  GLib's shared libraries.
- Fix: explicit Conan requirements and OHOS `LIBS` closure for libffi, pcre2,
  and the proxy `libintl` packaged by GLib.
- CI `#30400`: L0 passed and both direct requirements resolved; configure then
  failed because a configure-wide `LIBS` value polluted Autoconf's compiler
  sanity link. The closure is now passed only to `make` for real wv targets.
- CI `#30419`: configure and source compilation passed; libtool then rejected
  pcre2's relocated `//lib/libpcre2-8.la` reference. The OHOS build now drops
  dependency `.la` metadata from the local cache view after configure so
  linking uses the available shared objects.
- CI `#30427`: pre-configure cleanup executed but made Autoconf's compiler
  probe fail. Cleanup is now scoped between successful configure and make.
- CI `#30434`: the same `CI-020` worker repeated the compiler-probe failure;
  `CI-032` had passed the identical configure command in `#30419`. The OHOS
  environment now supplies the compiler tool directory and SDK linker runtime
  directory explicitly.
- CI `#30438`: configure and libwv linking passed; libffi/pcre2 errors were
  gone. The final wvWare link retained only `g_libintl_*` errors because the
  musl loader does not provide GLib's proxy aliases. The closure now uses the
  absolute `libintl.so` or `libintl.a` from the GLib package.
- CI `#30443`: configure, library compilation, and every CLI link passed;
  Conan reported the package binary built and reached `package()`. Installation
  then failed when parallel make could not create its HMDFS jobserver FIFO and
  the bundled `install-sh` failed to create `share/wv`. The OHOS build now
  rewrites generated `Makefile` and `GNUmakefile` install commands to the
  proven mkdir/cp shim, including `install_sh` directory helpers, and
  `autotools.install()` runs with `-j1`.
- CI `#30448`: package installation completed via the shim and Conan created
  the package. The test package reached its CMake link, where `wv::wv` did not
  propagate GLib's proxy `libintl` and lld rejected `g_libintl_*` references
  retained by `libwv.so`. OHOS consumer metadata now exports the GLib package
  library search path plus `intl`, preserving link order after wv. The test
  package build is also forced to `-j1` to avoid the non-fatal HMDFS jobserver
  FIFO warning.
- CI `#30455`: the main package again completed, but CI-002 failed in
  test_package CMake's compiler try-compile before reaching `wv::wv`. The OHOS
  SDK `lld` could not load `libxml2.so.16` and every required `xml*` symbol
  was missing. CI-005 had passed the same configure in `#30448`, so the worker
  inconsistency was reported in the PR. The test environment now prepends the
  discovered SDK `llvm/lib` directory to `LD_LIBRARY_PATH`, mirroring the
  main recipe's working environment.
- Local AST, YAML, R38, whitespace, dependency-presence, and generated-link-
  flag probes passed. Native OHOS CI revalidation is pending.

## Real-device shadow CI

- SSH target: `currentUser@10.62.221.191:2222`.
- Runner ID: `codex-wv-r18-wv-wv-1.2.9-shadow-r18-20260821-234825-21984`.
- Conan create: pass.
- Test package: pass, 3 assertions and 0 failures.
- L0 quality gate: pass.
- L1 build and package validation: pass.
- L2 installed target CLI probe: non-blocking skip; no installed CLI could
  execute its version/help command on the worker.
- L4 package inspection: pass.
- L5 consumer validation: pass.
- Package reference:
  `wv/1.2.9#66cd91e92991b63c66b81ca115a34fae:e2e9c2e2ac191f51e4f1e065fc93d0516a8b9a91#65123a5bfba4c59303953b28ba72dff3`.
