# ud/1.1.0 for HarmonyOS PC

`ud` is the small C command-line UNIX-day converter from
https://github.com/xyproto/ud. This recipe packages its official `v1.1.0`
tag for HarmonyOS PC AArch64.

The upstream CMake file unconditionally changes `CMAKE_C_COMPILER` to `gcc`
after `project()`. The target has Clang but no GCC; this causes a build failure
even when `-DCMAKE_C_COMPILER=clang` was supplied. The recipe removes that
override and maps the invalid CMake standard value `18` to C17 (the same ISO
2018 revision), leaving the program source unchanged. Its installed-package
consumer tests all three date-input formats,
UNIX-day conversion, pre-epoch behavior, help/version, and invalid input.

See `1.1.0/notes.md` for native verification and limitations.
