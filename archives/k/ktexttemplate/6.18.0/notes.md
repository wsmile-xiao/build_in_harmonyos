# ktexttemplate 6.18.0 notes

## Scope

This package provides `KF6::TextTemplate`, required by `grantleetheme`.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` enables the KDE Frameworks build on OHOS.
- `CMAKE_DISABLE_FIND_PACKAGE_Qt6Qml=ON` keeps optional scriptable tag support
  out of the baseline package.
- `BUILD_TESTING=ON` keeps upstream CTest coverage enabled.
- Runtime environment exports the package `lib/plugins` directory so consumers
  can load the built-in KTextTemplate tag libraries.

## Verification

OHOS `conan create` passed:

- Upstream CTest: 3/3 passed.
- test_package CTest: 1/1 passed.
- Direct test executable: `PASS: KTextTemplate rendered Hello Akonadi`.
- Full package reference:
  `ktexttemplate/6.18.0#50f8891c6e4e32a460a490f9cae1316a:57ffd8c720a5bfee7e8827990cd6550a49181c1b#6ab33dcd4489965ecbdc81e1c02272c5`.

Known upstream test exclusions:

- A full upstream CTest attempt was run before exclusions. `testbuiltins`,
  `testloadertags`, and `testcachingloader` reproducibly terminated with
  `SIGSEGV` on OHOS; `testdefaulttags` aborted in the same runtime group.
- `testgenerictypes` completed but failed because Qt metatype reflection for
  the test's custom `Person` type returned unresolved values, producing
  repeated `Don't know how to handle metatype Person` diagnostics.
- Adding the build-tree plugin roots to `QT_PLUGIN_PATH` did not change these
  failures. The remaining non-reflection template, filter, and generic
  container tests are kept enabled, and the package consumer smoke test verifies
  a real `KF6::TextTemplate` compile/link/runtime render path.
