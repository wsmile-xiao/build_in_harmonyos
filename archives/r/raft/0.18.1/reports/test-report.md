# Test Report: raft 0.18.1

## conan create
- [x] Source download
- [x] configure (--disable-uv for OHOS compat)
- [x] make (all source files compiled)
- [x] package (libraft.so + libraft.a + headers)
- [x] test_package (raft_configuration_init/add/encode API)

## Result
- conan create: PASS
- test_package: PASS (100% tests passed, 0 failed)
- OS: OHOS aarch64
- Compiler: clang 15.0.4
