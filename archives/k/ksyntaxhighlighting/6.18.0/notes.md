# ksyntaxhighlighting 6.18.0 notes

## Scope

This package provides `KF6::SyntaxHighlighting`, required by expanded
KTextAddons and later KDE PIM text-editing libraries.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` enables the KDE Frameworks build on OHOS.
- `KF_SKIP_PO_PROCESSING=ON` is paired with
  `0001-Skip-poqm-translation-install.patch` because the current Qt package does
  not provide the Qt Linguist toolchain needed by `ECMPoQmTools`.
- `BUILD_EXAMPLES=OFF` with `0002-Add-BUILD_EXAMPLES-option.patch` keeps
  example applications out of the library package.
- `BUILD_TESTING=ON` keeps the normal upstream CTest suite enabled.
- `BUILD_QCH=OFF` skips optional API documentation generation.
- `QRC_SYNTAX=ON` bundles syntax and theme definitions into the library so
  consumers do not need external syntax data files.
- `perl/5.42.2` is a build tool requirement because the released source uses
  Perl generators for merged syntax definition files.
- Runtime verification stages dependency libraries beside test executables for
  OHOS loader behavior around relative shared-library lookups.

## Verification

- Source archive SHA256 was verified against
  `8be8057221a982c8d1fe42f95454fac9610eb51975226c6652689293cd335bfd`.
- OHOS aarch64 `conan create`: passed.
- Full package reference:
  `ksyntaxhighlighting/6.18.0#b19b5e2a737a274fb5e230cc0a781d6a:57ffd8c720a5bfee7e8827990cd6550a49181c1b#97599434dccaaab4613942bfc1373342`.
- Upstream CTest: passed 6/6 default tests:
  `wildcardmatcher_test`, `repository_test`, `theme_test`,
  `testhighlighter_test`, `htmlhighlighter_test`, and `folding_test`.
- Conan `test_package`: passed CTest 1/1 and direct execution. The consumer
  found `KF6SyntaxHighlighting`/`KF6::SyntaxHighlighting` and loaded the
  built-in C++ syntax definition and Breeze Light theme.

## Upstream Tests Not Run

- Appstream metadata validation was not registered because `appstreamcli` is
  not available in the build environment.
- `highlighter_benchmark` and `repository_benchmark` are registered only for
  the upstream `BENCHMARK` CTest configuration. They are built, but excluded
  from normal test execution because upstream marks them as benchmarks that do
  not add functional library coverage.
