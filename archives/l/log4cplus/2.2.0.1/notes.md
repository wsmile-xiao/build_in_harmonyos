# log4cplus 2.2.0.1 adaptation notes

- Official release: `REL_2_2_0_1`.
- Source archive SHA-256: `374175c22fabe752eb1c20138e732b69ae191e641f92d32c9432985cd860a2df`.
- CMake optional Qt4, Qt5, iconv, and logging-server paths are disabled for the OHOS recipe.
- The required build dependency is the platform `Threads` package; no Conan dependency is declared.
- Cross-built CTest binaries are compiled but are not executed by the OHOS Conan build step.
- Conan OHOS profiles must bind `CMAKE_SYSTEM_NAME=OHOS`, the `aarch64-linux-ohos`
  compiler target, and `tools.build:sysroot`; otherwise the Windows linker can
  be selected for both the package and its test consumer.
- Native OHOS workers may provide no explicit `tools.build:sysroot`; the recipe
  only requires that setting for `cross_building(self)` and otherwise uses the
  platform compiler's default sysroot. This keeps host cross-build protection
  without rejecting the platform's native profile.
- `LOG4CPLUS_SOURCE_ARCHIVE` is a task-local offline source override only. The
  official URL and SHA-256 remain in `conandata.yml`, and Conan `get()` still
  verifies the local archive.
