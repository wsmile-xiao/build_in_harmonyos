# kwallet 6.18.0 notes

## Scope

This package provides the `KF6::Wallet` API library needed by `libkgapi`.

## Adaptations

- `BUILD_KSECRETD=OFF` skips the Secret Service daemon and its runtime stack.
- `BUILD_KWALLETD=OFF` skips the KWallet daemon.
- `BUILD_KWALLET_QUERY=OFF` skips the command-line query tool and DocTools
  documentation path.
- `BUILD_TESTING=OFF` avoids daemon-oriented upstream test and example
  targets; the API-only build does not register useful standalone CTest
  entries.
- `WITH_X11=OFF` keeps the package on the headless OHOS baseline.
- `KF_IGNORE_PLATFORM_CHECK=TRUE` enables KDE Frameworks CMake on OHOS.
- Installed OHOS ELF files are re-signed after CMake installation.

## Verification

- Source archive SHA256 was verified against
  `c8630e1b280b9aee44f3367302fce381370a611557f1941908b9286e3891d163`.
- OHOS aarch64 `conan create` passed.
- Full package reference:
  `kwallet/6.18.0#eb70a335fca52fa55be3bf901b59e09c:f83ab4bceea08d7b54ab55567ce33285498afb4f#1bfd5b96d99ff2759d8048f1ce67bbf5`
- The package installed and signed 1 OHOS ELF file:
  `libKF6Wallet.so.6.18.0`.
- The Conan `test_package` found `KF6Wallet`/`KF6::Wallet`, linked a CMake
  consumer, ran CTest 1/1, and verified basic KWallet API names.

## Upstream Tests Not Run

- Upstream daemon/runtime tests require a full KWallet service environment and
  optional runtime dependencies intentionally excluded from this API-only
  package.
