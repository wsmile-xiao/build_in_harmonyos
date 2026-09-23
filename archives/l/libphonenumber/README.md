# libphonenumber

Google 维护的国际电话号码解析、格式化与校验库。本目录收录其 C++ 实现在
HarmonyOS PC（aarch64）上的 Conan 适配配方。

- 上游仓库：<https://github.com/google/libphonenumber>
- 构建系统：CMake（构建入口为源码子目录 `cpp/`）
- 许可证：Apache-2.0

## 版本

- 8.13.51：首轮适配，`REGENERATE_METADATA=OFF`（使用预生成元数据，无需 Java），
  `USE_BOOST=OFF` + `USE_STDMUTEX=ON`，上游 gtest 套件 `libphonenumber_test` 在
  `build()` 内真实运行并输出机器证据。

## 依赖

- abseil-cpp/20260107.1
- protobuf/33.6（含可运行的 protoc；OHOS 适配版，已被已发布 grpc/1.70.0 在官方 CI 完整构建验证）
- icu4c/78
- googletest/1.12.1（测试）
