# cpp-peglib 1.15.0 适配记录

## 基本信息

- 上游仓库：https://github.com/yhirose/cpp-peglib
- 上游版本：1.15.0
- Conan 引用：`cpp-peglib/1.15.0`
- 构建系统：CMake
- 语言：C++17
- 适配路径：路径 A（基础适配）

## W0/W0b/lang-preflight

- W0：运行 `bash ci/scripts/preflight_check.sh cpp-peglib/1.15.0`，无依赖声明，预检通过。
- W0b：仓库已有同库更高版本归档 `cpp-peglib/1.17.0`（commit 21d65a8be1 已合入 main），
  历史 notes 记录：CMake header-only INTERFACE 库、顶层测试由 gtest_discover_tests 注册独立
  用例、上游含独立 rust-peglib 子项目且被顶层 CMake 排除。本配方与 1.17.0 同构生成，
  历史踩坑命令逐项比对遵循（无平台 patch、无自定义编译参数）。
- 官方源码下载：`https://github.com/yhirose/cpp-peglib/archive/refs/tags/v1.15.0.tar.gz`，
  SHA256 为 `5bf1b6bf854e9751658ec85a7cba1beeb81fa6a6baff2af6369a2e1be0a2b99a`，已本地下载核对。
- lang-preflight 完整源码树检测为 `rust`（证据：嵌套 `rust-peglib/Cargo.toml`，检测器的
  `_manifest_scan()` 在递归文件集合中发现任意 Cargo.toml 后优先返回 Rust，CLI 无排除目录参数）。
  与 1.17.0 记录同坑：该 Rust 子项目由顶层 `CMakeLists.txt` 明确排除（顶层只对 test/、lint/、
  example/、pl0/、benchmark/ 调用 add_subdirectory()）。因此按本包真实构建范围对顶层 CMake 的
  C++ 测试子目录 `test/` 执行无副作用的 `detect_language()` 预检，结果为 `cpp`
  （CMakeLists.txt project(test)，17 个 `.cc` 文件占 100%）。未修改检测器、未伪造完整源码树结果。

## 软件类型与配方

cpp-peglib 的顶层 CMake 定义 `peglib` 为 `INTERFACE` 目标，并安装单个 `peglib.h`。因此配方
不声明库文件，`package_info()` 使用空 `cpp_info.libs` 和 CMake interface target；生产包不需要
`commands.json`。

配方启用 C++17 和上游 `BUILD_TESTS=ON`，关闭 benchmark、examples、lint、PL/0 等非生产目标；
`build()` 运行 `cmake.test()`，由上游 `gtest_discover_tests()` 执行独立测试用例。上游测试的
GoogleTest 仍由上游 CMake FetchContent 获取，未将尚未验证发布状态的 gtest 作为生产依赖。

## 上游测试统计

- 上游测试源文件：17 个 `test/*.cc`。
- **计数口径（贯穿 MANIFEST / notes / PR 表格）：上游源码注册的 TEST/TEST_F 数量 = 503**
  （`grep -rhoE 'TEST(_F|_P)?\s*\(' test/*.cc`，与 PC 鸿蒙化审查实测口径一致）。
- 构建后由 `gtest_discover_tests()` 展开为独立 CTest 用例，**CTest 实际注册并执行 502 个**
  （与 1.17.0 的 521→520 现象同因：gtest_discover_tests 展开差异），502/502 全部通过。
- 上游仓库内的 `rust-peglib/` 不在顶层 CMake 测试范围内。

## 源码修改与补丁

没有修改上游源码或测试文件，没有生成补丁。当前配方直接使用官方源码包和上游 CMake 测试定义。

## 远程 CI 网络问题修复（googletest FetchContent）

远程 HarmonyOS CI 首次构建（PR #9375 / Worker #43829）失败，根因**不是配方或平台编译问题**：
主源码经 CI 镜像（gh-proxy.com）下载成功，但上游 `test/CMakeLists.txt` 通过 FetchContent
**直连 github.com 下载 googletest**（`03597a01ee50ed33e9dfd640b249b4be3799d395.zip`）
超时——Worker 网络受限（已知可达 zlib.net，github.com 443 连接超时），而该 URL 硬编码在
上游测试 CMake 中，不在 conandata.yml，CI 的 mirror fallback 不会重写它。

修复：配方不修改上游文件，而是：
1. `build()` 预下载 googletest 到构建目录（优先 gh-proxy.com 镜像，与 CI 主源码镜像同源；
   github.com 直连作为回退）；
2. `generate()` 通过 `FETCHCONTENT_SOURCE_DIR_GOOGLETEST` 把上游 FetchContent 指向
   本地预下载目录，跳过网络下载。

验证：本地 linux-native conan create 日志确认
`Sources correctly downloaded from https://gh-proxy.com/https://github.com/google/googletest/...`，
CTest 502/502 与消费者测试均通过；远程 CI 重跑以实际构建结果为准。

## 验证记录（本地 Ubuntu x86_64）

本地环境非 HarmonyOS PC 设备（无 OHOS 工具链），使用 linux-native profile 完成配方逻辑与
上游测试验证：

- conan create：生产包构建成功，仅安装 `peglib.h` 与 LICENSE；
- 上游 CTest：502/502 PASS（`100% tests passed, 0 tests failed out of 502`，CTest 实际执行数）；
- Conan consumer：1/1 PASS，输出 `cpp-peglib consumer test passed`。

HarmonyOS PC 设备（aarch64）与远程 CI 验证待设备/CI 回填（与 1.17.0 相同，设备验证由
HarmonyOS PC worker 执行；配方无平台相关代码，1.17.0 设备验证通过记录可作强参考）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake header-only 配方（参考 1.17.0 同构） |
| conandata.yml | 官方源码 URL + SHA256 |
| test_package/ | 消费者 C++ 测试（peg::parser API 实测） |
| MANIFEST.yml | 上游测试声明（503 cases 口径） |
---

**编译结束**: 2026-09-10 02:17
**最终状态**: built
