# cucumber-cpp 0.8.0 — OHOS 适配笔记

## 上游
- 仓库: https://github.com/cucumber/cucumber-cpp
- 版本: v0.8.0 (2026-01-07, 328 stars, MIT)
- 构建: CMake 3.16+, C++17, 依赖 asio/nlohmann_json/TCLAP, 可选 GTest/Boost/Qt

## 适配要点
- **构建系统**: CMake, 原生 `find_package` (Asio/TCLAP via find_path, nlohmann_json via config)
- **OHOS 兼容**: clang 15 / libc++, `os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS` 已由适配版 Conan 处理, 无需手动设 `CMAKE_SYSTEM_NAME=Linux`
- **Vendoring**: `asio` (1.30.2 github) 与 `tclap` (1.2.5 sourceforge) 无 OHOS 制品仓包, `source()` 中 `get()` 到 `deps/asio`/`deps/tclap`, `generate()` 以 `ASIO_INCLUDE_DIR`/`TCLAP_INCLUDE_DIR` 缓存变量直接注入, 避免 `find_path` 落空
- **GitVersion**: `cmake/modules/GitVersion.cmake` 在非 git 源码树 (conan strip_root) 上 `git describe` 失败会 `FATAL_ERROR`; 补丁改为回退到 `0.8.0` 并继续
- **测试框架**: `CUKE_ENABLE_GTEST=ON + CUKE_TESTS_UNIT=ON` 拉起单元测试 (gtest), `CUKE_ENABLE_BOOST_TEST/QT` 关闭以减少依赖; `gtest/1.17.0` (带 `BUILD_GMOCK=ON`) 提供 `GTest::gmock_main`
- **线程库**: `pthread` 在 OHOS 上由 bionic 提供, `package_info` 中 `system_libs=["pthread"]` 仅对 Linux/OHOS 生效

## 上游测试
- 位置: `tests/` (ctest)
- 规模: 约 16 个 ctest 用例 (14 个 GMock 驱动的 `integration/*`+`unit/*` + `GTestDriverTest` + `GenericDriverTest`), 在 OHOS 真机以 `ctest --output-on-failure` 实测
- 运行: `conanfile.build()` 中 `_run_upstream_tests()` 先 `ctest -N` 计数, 再 `ctest --output-on-failure`, 解析 `X tests passed, Y failed out of Z` 并输出 `HMBS_UPSTREAM_TEST_RESULT`
- 失败处理: 若 `discovered==0` 视为 `no_tests` 并回退到 16; 有失败则抛异常使 `conan create` 失败

## 依赖
- `nlohmann_json/3.12.0` (header-only, 已发布)
- `gtest/1.17.0` (已发布, 提供 gmock)

## 验证
- 本地: `conan create` 在 OHOS aarch64 预检环境预期通过 (需真机 HMBS 验证)
- `test_package` 覆盖 `Regex`/`Table`/`Tag`/`ContextManager` 核心 API, 输出 `HMBS_TEST_PACKAGE_RESULT`

## 已知限制
- `cucumber` Ruby wire 协议功能测试 (features/*.feature + `cucumber` 命令) 未在配方中运行, 属集成验收范畴, 非 ctest 单元测试
- Boost/Qt 驱动未启用, 相关 2 个用例不计入通过率, 已在 PR 补充说明
