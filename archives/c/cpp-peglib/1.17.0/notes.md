# cpp-peglib 1.17.0 适配记录

## 基本信息

- 上游仓库：https://github.com/yhirose/cpp-peglib
- 上游版本：1.17.0
- Conan 引用：`cpp-peglib/1.17.0`
- 构建系统：CMake
- 语言：C++17
- 适配路径：路径 A（基础适配）

## W0/W0b/lang-preflight

- W0：运行 `bash ci/scripts/preflight_check.sh cpp-peglib/1.17.0`，结果为无依赖声明，预检通过。
- W0b：仓库中没有 cpp-peglib 历史归档或历史 `notes.md`，无可迁移命令或历史坑点。
- 官方源码下载：`https://github.com/yhirose/cpp-peglib/archive/refs/tags/v1.17.0.tar.gz`，SHA256 为 `48145b73d080d4cad950ca6f89d5ccd3373ba4017ab488733f532a0d74afc67a`，已在本地下载核对。
- lang-preflight 的完整源码树检测为 `rust`，证据是嵌套路径 `rust-peglib/Cargo.toml`；检测器的 `_manifest_scan()` 会在递归文件集合中发现任意 `Cargo.toml` 后优先返回 Rust，CLI 没有排除目录参数。该 Rust 子项目由顶层 `CMakeLists.txt` 明确排除：顶层只对 `test/`、`lint/`、`example/`、`pl0/`、`benchmark/` 调用 `add_subdirectory()`，没有 `add_subdirectory(rust-peglib)`；Rust 仅在 `justfile` 的独立 cargo 命令中出现。因此按本包真实构建范围对顶层 CMake 的 C++ 测试子目录 `test/` 执行了无副作用的 `detect_language()` 预检，结果为 `cpp`，`CMakeLists.txt project(test)`，17 个 `.cc` 文件占 100%。未修改检测器、未伪造完整源码树结果，也未生成 feedback 文件。

## 软件类型与配方

cpp-peglib 的顶层 CMake 定义 `peglib` 为 `INTERFACE` 目标，并安装单个 `peglib.h`。因此配方不声明库文件，`package_info()` 使用空 `cpp_info.libs` 和 CMake interface target；生产包不需要 `commands.json`。

配方启用 C++17 和上游 `BUILD_TESTS=ON`，关闭 benchmark、examples、lint、PL/0 等非生产目标；`build()` 运行 `cmake.test()`，由上游 `gtest_discover_tests()` 执行独立测试用例。上游测试的 GoogleTest 仍由上游 CMake FetchContent 获取，未将尚未验证发布状态的 gtest 作为生产依赖。

## 上游测试统计与设备结果

- 上游测试源文件：17 个 `test/*.cc`。
- 设备 CTest 实际注册并执行 520 个 cases，`100% tests passed, 0 tests failed out of 520`。
- CMake 测试目标：`peglib-test-main` 一个，使用 `gtest_discover_tests()` 展开为独立 CTest 用例。
- 上游仓库内的 `rust-peglib/` 不在顶层 CMake 测试范围内。

## 源码修改与补丁

没有修改上游源码或测试文件，没有生成补丁。当前配方直接使用官方源码包和上游 CMake 测试定义。

## 验证记录

最终本地提交：`b0f1a29040dcf6e97816da46205489307a622ed0`，设备远端 worktree
已核对为同一 SHA。设备执行的 Conan create 完成生产包、上游 CTest 和
test_package：

- 上游 CTest：520/520 PASS，日志为 `$HOME/tmp/import-deps-100-odd-cpp-peglib-create.log`；
- Conan consumer：1/1 PASS，输出 `cpp-peglib consumer test passed`；
- 包为 C++17 header-only INTERFACE 库，只安装 `peglib.h`，没有 CLI 或
  `commands.json`；
- CMake 报告 `System is unknown to cmake`（OHOS 平台未被该 CMake 版本内置）
  以及 jobserver fifo 权限警告，但配置、构建和测试退出码均为 0。
