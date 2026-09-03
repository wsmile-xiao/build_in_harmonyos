# kcontacts 6.18.0 notes

## Scope

This package provides `KF6::Contacts` for Akonadi contact-related downstream
libraries.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` enables the KDE Frameworks build on OHOS.
- `USE_QML=OFF` keeps the package focused on the contact library needed by the
  Akonadi chain.
- `BUILD_TESTING=ON` keeps upstream CTest coverage enabled.
- `ki18n_install(po)` is disabled because the Qt Linguist tools component is not
  part of the qtbase package used here.
- Installed package ELF files are re-signed after `cmake --install` for OHOS
  runtime loader compatibility.
- Runtime verification uses symlinks to dependency `.so*` files instead of
  copying them, preserving OHOS code signatures while satisfying relative
  library lookup paths.
- CMake configure/build/install and the Conan test_package configure/build
  prepend the active OHOS SDK `llvm/lib` only for host tool execution so SDK
  `lld` can load its matching `libxml2.so.16` on CI workers without leaking that
  host runtime path into CTest target execution.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `a532c47c3c2c8182b2ae9e783ff521311896251c2a1ddbe364b3491f94c100b6`.
- The translation patch was checked against the unpacked 6.18.0 source.

OHOS `conan create` verification passed:

- Runner:
  `codex-a-kcontacts-kcontacts-6.18.0-r2-20260827-204232-31359`.
- Upstream CTest: 30/30 runnable entries passed.
- Excluded upstream tests: `kcontacts-addresstest` and
  `kcontacts-addressformattest`; both require iso-codes data that is not
  available in the current OHOS package profile.
- Conan `test_package`: 1/1 passed and printed
  `PASS: KContacts addressee = Ada Lovelace <ada@example.test>`.
- Package install signed 1 OHOS ELF file.
- Full package reference:
  `kcontacts/6.18.0#94c9b32e116a5f3272fa717d1c8e1696:e9b4950a14f6d9b40836421f7041c28c44eba86a#d7f8698c8853ffe821db89c0ac9c7bef`.
