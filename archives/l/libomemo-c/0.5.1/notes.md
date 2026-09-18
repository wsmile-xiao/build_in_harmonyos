# libomemo-c 0.5.1 - OHOS adaptation notes

Build system: CMake, 10 ctest entries via Check framework.
Vendored protobuf-c runtime to avoid conancenter chain.
All 10 upstream tests pass on OHOS aarch64 (ctest --output-on-failure 10/10).
Consumers smoke test via test_package 1/1.
