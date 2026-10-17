# qtkeychain 0.14.2 notes

## Scope

This package provides the Qt6Keychain CMake package and `qt6keychain` target
needed by `kmailtransport`.

## Adaptations

- `BUILD_WITH_QT6=ON` builds the Qt 6 library variant.
- `LIBSECRET_SUPPORT=OFF` avoids the optional host libsecret dependency that
  is not part of the current OHOS package baseline.
- `BUILD_TRANSLATIONS=OFF` avoids a mandatory Qt LinguistTools lookup.
- `BUILD_TEST_APPLICATION=ON` keeps the upstream test client building as a
  compile/link smoke test.
- The recipe exposes the packaged Qt6 and ECM CMake module paths explicitly
  because upstream includes ECM modules directly.
- Installed OHOS ELF files are re-signed after CMake installation.

## Verification

- Source archive SHA256 was verified against
  `cf2e972b783ba66334a79a30f6b3a1ea794a1dc574d6c3bebae5ffd2f0399571`.
- OHOS aarch64 `conan create` passed.
- Full package reference:
  `qtkeychain/0.14.2#993659fa9d4671915ab1709b92917033:fe643a6a365d349533fe6eecb9772405e9423933#215d0d817b9bef6094932f83af149f59`
- The upstream `testclient` application built successfully.
- The package installed and signed 1 OHOS ELF file:
  `libqt6keychain.so.0.14.2`.
- The Conan `test_package` found `Qt6Keychain`, linked a CMake consumer,
  ran CTest 1/1, and verified QKeychain fallback store/read/delete behavior.

## Upstream Tests Not Run

- Upstream qtkeychain 0.14.2 does not register CTest entries. The package
  builds the upstream `testclient` application, then the Conan `test_package`
  verifies downstream CMake consumption and QKeychain fallback read/write/delete
  behavior with an isolated `QSettings` store.
