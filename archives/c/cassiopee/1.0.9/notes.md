# Cassiopee 1.0.9

- Upstream: https://github.com/osallou/cassiopee-c, tag `1.0.9`.
- Build system: CMake.
- Direct Conan requirements are `boost/1.90.0.4` and `glog/0.7.1`; `cppunit/1.15.1` is declared through `build_requirements()` for the upstream test suite only.
- The original CMake file required CMake 2.8 and injected `/usr/local/lib`. The patch raises the minimum to CMake 3.5 and removes the host-specific link directory so Conan dependency targets are used.
- The upstream project includes 13 CppUnit test methods registered in `test/test.cxx`; all are built and run by `ctest`.
- The consumer test links the installed `cassie` library, constructs `CassieIndexer`/`CassieSearch`, and verifies three matches.
- HarmonyOS default build uses a static Cassiopee library (`shared=False`) because the upstream CMake layout emits a relative `../lib/libcassie.so` DT_NEEDED entry that the HarmonyOS loader does not resolve from the test executable.
---

**编译结束**: 2026-09-07 12:51
**最终状态**: built
