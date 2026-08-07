# qtlanguageserver 6.11.1 adaptation notes

## Build configuration

- Build system: CMake through Conan 2.
- Target platforms: Linux and OHOS.
- OHOS Qt mkspec: `harmonyos-clang`.
- Examples, benchmarks, and manual tests are disabled.
- `QT_BUILD_TESTS` configures the upstream tests and
  `QT_BUILD_TESTS_BY_DEFAULT` makes the normal CMake build generate their
  executables. No upstream test is excluded.
- Build #15413 compiled all four `tst_*` targets and passed the complete upstream
  CTest suite (5/5) on the official OHOS worker. This confirms that the earlier
  missing-executable results were test-build configuration errors rather than
  an OHOS runtime incompatibility.

## Validation

The L1 consumer constructs an LSP trace value and links the packaged libraries.
Build #15584 again passed the full upstream suite, then failed because the
CMakeDeps-generated consumer config requested `qtbaseConfig.cmake`. The qtbase
package intentionally exposes its installed `Qt6Config.cmake` instead. This
recipe now exposes the installed `Qt6LanguageServerPrivateConfig.cmake`, and the
consumer links `Qt6::LanguageServerPrivate`. A fresh CI run is required only to
confirm that native Qt CMake package path; the upstream source is a Path A
adaptation candidate and does not satisfy Path B failure criteria.
