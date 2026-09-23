# sonnet 6.18.0 notes

## Scope

This package provides `KF6::SonnetCore` and `KF6::SonnetUi` for
`ktextwidgets`, which is required by `akonadi-contacts`.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` enables the KDE Frameworks build on OHOS.
- `SONNET_USE_QML=OFF` avoids Qt Quick components that are not required by the
  Akonadi contact chain.
- `SONNET_NO_BACKENDS=ON` allows building the framework libraries without
  Aspell/Hspell/Hunspell/Voikko backend plugins.
- `BUILD_DESIGNERPLUGIN=OFF` and `BUILD_EXAMPLES=OFF` keep optional tooling out
  of the package.
- `BUILD_TESTING=ON` keeps upstream CTest coverage enabled.

## Verification

OHOS `conan create` passed:

- Upstream CTest: 5/5 passed.
- test_package CTest: 1/1 passed.
- Direct test executable: `PASS: Sonnet UI meta-object = Sonnet::Highlighter`.
- Full package reference:
  `sonnet/6.18.0#3e6f6dee8064b5b034a1363d673ac2c4:57ffd8c720a5bfee7e8827990cd6550a49181c1b#a42c24c703609b61ca53244b037587c9`.

Known upstream test exclusion:

- `sonnet-test_highlighter` starts Qt Widgets platform integration and aborts
  because the current OHOS qtbase package does not provide the `offscreen`
  platform plugin. The non-widget Sonnet upstream tests are kept enabled.
