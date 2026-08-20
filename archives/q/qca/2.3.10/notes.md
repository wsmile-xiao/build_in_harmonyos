# qca 2.3.10 OpenHarmony PC notes

## Scope

This package adapts QCA 2.3.10, the Qt Cryptographic Architecture library. The baseline package builds the Qt 6 core library and installs the CMake/pkg-config metadata.

## Dependency boundary

QCA is a Qt library. The recipe consumes `qtbase/6.11.1` and `qtcore5compat/6.11.1` as Conan dependencies and points CMake at their package folders. No system Qt prefix is required. The OHOS qtbase package does not ship Qt6Core5Compat, so this PR adds a `qtcore5compat/6.11.1` recipe built from the official Qt `qt5compat-everywhere-src-6.11.1.tar.xz` module; QCA's existing `QTextCodec` and `QRegExp` usage keeps compiling against it.

## Build

Main CMake options:

```text
-DBUILD_WITH_QT6=ON
-DBUILD_TESTS=ON
-DBUILD_TOOLS=OFF
-DBUILD_PLUGINS=none
```

Upstream unit tests are enabled with `BUILD_TESTS=ON`; helper tools and optional crypto plugins remain disabled for the baseline package, while the core `qca-qt6` library remains enabled. The `cms` unit test is registered only when OpenSSL is available, so the registered count is 24 without OpenSSL and 25 with OpenSSL. OpenDesk round6 target log on head `18dbbb78e` reports `100% tests passed` (`24/24`); the current head `20efe1699e` changes test statistics/docs only and also builds Qt6Core5Compat from the new dependency recipe before compiling QCA, so current-head pass rate is pending revalidation.

## Tests

The recipe runs upstream CTest with `ctest --output-on-failure` when target execution is available.

The `test_package` compiles and links a small downstream consumer by finding Qt6 directly, then creates `QCA::Initializer` when the target can run. Runtime library paths come from the qtbase and qtcore5compat dependencies.
