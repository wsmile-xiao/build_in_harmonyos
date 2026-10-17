# kcontacts 6.14.0 notes

## Scope

This package provides `KF6::Contacts` for Akonadi contact-related downstream
libraries. Version 6.14.0 exists alongside 6.18.0 so consumers that exact-pin
the KF6 6.14 family (mauikit/4.0.2, kio/6.14.0) can resolve their full KF6
dependency graph; Conan 2 rejects a cross-family double exact pin, so the
6.14-aligned recipe is required to unblock communicator-4.0.2.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` enables the KDE Frameworks build on OHOS.
- `USE_QML=OFF` keeps the package focused on the contact library needed by the
  Akonadi chain.
- `BUILD_TESTING=ON` keeps upstream CTest coverage enabled.
- Requires are aligned to the KF6 6.14 family (`kcodecs`, `kconfig`,
  `kcoreaddons`, `ki18n` at 6.14.0); `qtbase/6.11.1`, `ecm/6.26.0` and
  `shared-mime-info/2.5.1` are shared with the 6.18.0 recipe.
- `ki18n_install(po)` is disabled by `patches/0001-CMakeLists.txt.patch`
  because the Qt Linguist tools component is not part of the qtbase package
  used here. The same patch as 6.18.0 applies unchanged; in 6.14.0 the context
  matches verbatim with a pure line offset.
- `cmake_system_name=OHOS` plus a `CMAKE_USER_MAKE_RULES_OVERRIDE` defining
  `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG` gives `libKF6Contacts.so.6` a
  real `DT_SONAME` (no CMake Platform/HarmonyOS module; the
  soname-flag draft in `knowledge/drafts/`). The test_package adds
  `test_ohos_soname.cpp`, which parses the consumer's own `DT_NEEDED` and
  asserts the linkage stayed SONAME-based (relative entry, no absolute
  slash-qualified path that musl could never re-resolve).
- Installed package ELF files are re-signed after `cmake --install` for OHOS
  runtime loader compatibility.
- Runtime verification uses symlinks to dependency `.so*` files instead of
  copying them, preserving OHOS code signatures while satisfying relative
  library lookup paths.
- CMake configure/build/install and the Conan test_package configure/build
  prepend the active OHOS SDK `llvm/lib` only for host tool execution so SDK
  `lld` can load its matching `libxml2.so.16` on CI workers without leaking
  that host runtime path into CTest target execution.
- The test_package `test()` recreates the legacy `~/.conan2/...` cache-root
  prefixes as symlinks when the active cache root differs (best-effort, no-op
  when paths already match) so absolute-path `DT_NEEDED` entries baked into
  already-published dependency packages stay resolvable on this machine.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `64fd6f2692dc5bea9bc720f52bfdb2880771d82db27e1c9c0f61ac846e503729`
  (https://download.kde.org/stable/frameworks/6.14/kcontacts-6.14.0.tar.xz).
- The translation patch was applied to the unpacked 6.14.0 source and the
  result diff-checked: only `ki18n_install(po)` and the following blank line
  are removed.

OHOS `conan create` verification (authoritative CI,
`ci/conan/build_and_test.sh`, profile `ohos-aarch64`, 2026-09-21):

- Upstream CTest: 30/30 runnable entries passed
  (`kcontacts-addresstest` and `kcontacts-addressformattest` excluded; their
  iso-codes geographic data surface is absent from the OHOS device image —
  environment limitation, same exclusion set and outcome as 6.18.0).
- Conan `test_package`: 2/2 passed, including the OHOS-specific
  `test_kcontacts_ohos` check, which printed
  `PASS: SONAME-based DT_NEEDED (libKF6Contacts.so.6, 5 NEEDED entries, none absolute)`.
- Package install signed 1 OHOS ELF file.
- Full package reference:
  `kcontacts/6.14.0#75cb3a45ccb590d332b4ea44cfac3c01:7e850bd8a9b615282808dac316c3f84a7aff7b79#c7527089392c16fdae768eced3ebd901`.
- CI gates: L0 pass, L1 pass (upstream tests + test_package, negative test
  confirmed), L2 skip (library package, no bin/), L4 pass, L5 pass.
- Runner evidence: `logs/ci-run.log` (round 3), `ci-metadata.json`
  (build_trace.runner `manual`, timestamp 2026-09-21T05:55:45Z).
