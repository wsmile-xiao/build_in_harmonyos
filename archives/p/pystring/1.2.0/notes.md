# pystring 1.2.0 adaptation notes

- Upstream tag: `v1.2.0` from `imageworks/pystring`.
- Source archive SHA-256: `020a603a757ba1e429f4b1ea6feb3afbe0fb34bcafa355032e1f1b8a0019d198`.
- Build system: CMake; no external dependencies or patches.
- Conan defaults to a static library and maps the `shared` option to upstream `BUILD_SHARED_LIBS`.
- CMake installs both public headers under `include/pystring`; the consumer test includes `pystring/pystring.h`.

## HarmonyOS PC validation

- `CONAN_HOME`: `/storage/Users/currentUser/work/psj/ch-pystring`.
- `conan create`: exit code 0.
- Upstream CTest: 2/2 targets passed. The 56 registered `PYSTRING_ADD_TEST` groups passed in the compiled and header-only modes (112 successful group executions); the separate header-only compile-definition target also built.
- Conan consumer test: 4/4 checks passed for `split`, `join`, `strip`, and `upper`.