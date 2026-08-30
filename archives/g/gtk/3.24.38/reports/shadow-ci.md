# HarmonyOS aarch64 shadow CI report

## Result

- Issue: AtomGit #32
- Package: `archives/g/gtk/3.24.38`
- Tested commit: `b2ae5d886217040a2b271e11d8398282febdf330`
- Runner: `local-ohos-shadow-device1`
- Device: HarmonyOS, HongMeng Kernel 1.12.0, aarch64
- Toolchain: clang 15.0.4, Python 3.12.9, Conan 2.29.1
- Completed: 2026-08-20 12:43:10 UTC
- Final status: pass

The run was serialized through the device-global Shadow CI lock. The lock was
released after completion.

## Input verification

- Shadow input archive SHA-256: `ef4a966d36807fe001ecd0b1f30be498cf7fa825ca2382a26db3d1328dbf1f9b`
- `ci/conan/setup.sh`: `d93c97005abe8e5c3cc8bd1076815b3a34654a523fc8c4dc8a2415a68e8367b7`
- `ci/conan/build_and_test.sh`: `74c2f2ab0720f96dea325229fe2abe565f78b55463571319e72e07ceae1fc4b7`
- `ci/conan/profiles/ohos-aarch64`: `63085cfa7a03f55f2c490939df0f924a73e08005ca77db1bd851ce2c2e08d18e`
- Recipe: `0d639c76e89e92b2f17e242977ca8bfd754ded05cbffaafe1e6eb9ae5ce025d3`
- Input verification record: `d3ddc263d8c7fc4ecd033fb18d2a1a107c6e239b9b70949e8c877fa7166a471f`
- Environment fingerprint: `21c170d4701a962239b088e02d67ed2604e06c4da120715a3129b6728d4390d9`
- Setup log: `61e5c6e0b38313b87ba9b17573bec3ec8c6859d0d1f68438e7ef070f3821bc49`
- Build log: `da2169dddf01836ebee6b56846821fac18fcdf86f761066b1821b9fe22e0eb7b`
- Gate results: `c133933448138962779f5d466bcb28dc995f7492108d759ff8f30cc6dc554459`

Preflight run:
`/storage/Users/currentUser/ohpc-ci-shadow/runs/b2ae5d886217-20260820T123607Z-preflight-1805`

Final run:
`/storage/Users/currentUser/ohpc-ci-shadow/runs/b2ae5d886217-20260820T123639Z-run-1951`

## Upstream tests

- The upstream GTK+ 3.24.38 source inventory contains 453 test cases according
  to the contest review; the Broadway-only HarmonyOS configuration concretely
  registers 237 of them.
- Meson completed all 1,321 build steps with `tests=true`.
- Meson introspection reported and enforced exactly 237 registered tests.
- The recipe selected and incrementally self-signed 219 Meson project/test ELF
  files; every signed output contained exactly one `.codesign` section.
- Seven display-independent upstream tests passed serially: bitmask, rbtree,
  typename, C++ keywords, RGBA, gtk-builder-tool simplify, and settings.
- Log marker: `Validated 237 upstream registrations and passed 7 OHOS-safe tests`.

The separate full-device sweep scheduled all 237 registrations: the default
set produced `7 OK / 185 TIMEOUT / 0 FAIL`, and the 45-test flaky set produced
`0 OK / 45 TIMEOUT / 0 FAIL`. The 230 timeouts require a connected Broadway
browser output client and are not reported as passed. Full commands, suite
counts, and logs are documented in `reports/upstream-test-inventory.md`.

## Package tests and gates

- Conan `test_package`: pass; linked `gtk3::gtk3`, validated runtime 3.24.38,
  resolved `GtkWindow` without opening a display, and printed
  `PASS gtk+ 3.24.38 type=GtkWindow`.
- Consumer ELF signing and `.codesign` verification: pass.
- R34 destructive dependency test: pass after moving package `lib/` and
  `include/` away.
- L0: pass, all checks passed.
- L1: pass, `test_package` executed.
- L2: skip, the library-only package has no `bin/` directory.
- L4: pass, patches clean.
- L5: pass, `lib/` has content.
- Build summary: one package, one success, zero failures.

## Failure progression and repair

Earlier runs established the forced HarfBuzz graph, the GLib generator path
rewrite, and the resource-preprocessor removal described in `notes.md`. The
upstream-test expansion then exposed two recipe-local issues:

- Run `3674a1ab10e1-20260820T121416Z-run-23386` completed 1,321 build steps but
  failed because Conan's applied build environment hid the runner's bare
  `meson` command. The recipe now resolves Meson before applying that
  environment and passes its absolute path to introspection and test commands.
- Run `774f3126635c-20260820T122627Z-run-39098` completed the build and reached
  registration validation, but compared suite-qualified command selectors with
  Meson's bare introspection names. The recipe now removes the suite prefix only
  for the existence check while retaining the proven command selectors.

The final run passed the 237-registration guard, 219-target signing, all seven
enforced upstream tests, installation, package signing, the Conan consumer,
R34, and every applicable CI gate.
