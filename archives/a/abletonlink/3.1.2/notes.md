# abletonlink 3.1.2 适配笔记

## 编译环境
- 构建系统: cmake（header-only 库，`Ableton::Link` 为 INTERFACE target）
- 编译日期: 2026-08-11
- 编译器: clang/clang++（OHOS aarch64，libc++）
- 状态: built（真机预检通过后由 HMBS 提交发布）

## 编译步骤

```bash
conan create . --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

- `source()`: 下载官方 tag tarball（Link-3.1.2）+ asio 1.28.0（release tarball 不含 asio-standalone 子模块，空目录）
- `build()`: cmake configure（`LINK_BUILD_TESTS=ON`）→ 构建 LinkCoreTest/LinkDiscoveryTest → 直接运行两个 Catch2 测试程序并输出 `HMBS_UPSTREAM_TEST_RESULT`
- `package()`: 拷贝 `include/ableton` + asio 头文件 + LICENSE

## 上游测试用例审计（来源：src/ 目录源码统计）

| 测试程序 | 用例数 | 来源（TEST_CASE 计数） |
|----------|--------|------------------------|
| LinkCoreTest | 16 | src/ableton/link/*.cpp 15 个 + src/ableton/tst_Link.cpp 1 个 |
| LinkDiscoveryTest | 9 | src/ableton/discovery/tst_InterfaceScanner/Payload/PeerGateway/PeerGateways/UdpMessenger 各 1 + v1/tst_Messages.cpp 4 |
| **合计** | **25** | grep -rho "TEST_CASE(" src --include="*.cpp" \| wc -l = 25 |

测试框架：Catch2 v2（`third_party/catch/catch.hpp`，随 tar 包附带，无需外部依赖）。测试未注册 ctest，直接运行可执行文件，退出码 0 + "All tests passed (N assertions in M test cases)" 视为通过。发现/通过数由 `_parse_catch2()` 从框架真实输出解析，不写死。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方 GitHub tarball 中 `modules/asio-standalone` 为空目录 | git submodule 内容不入 tar 归档，而 `AsioStandaloneConfig.cmake` 依赖该路径 | conandata.yml 增加 asio 1.28.0 独立 source，`source()` 里解压到 `modules/asio-standalone/`（strip_root），与 `AsioStandaloneConfig` 预期路径一致 |
| 2 | OHOS 下 `LINK_PLATFORM_*` 未定义，Config.hpp 无平台分支 | `AbletonLinkConfig.cmake` 只认 `APPLE/WIN32/CMAKE_SYSTEM_NAME MATCHES "Linux|kFreeBSD|GNU"`；OHOS 工具链映射 `CMAKE_SYSTEM_NAME=HarmonyOS` 不匹配 | patches/0001：为 `OHOS|HarmonyOS` 增加分支，定义 `LINK_PLATFORM_LINUX=1`（复用 Linux 平台层：ClockMonotonicRaw/getifaddrs/ThreadFactory，OHOS 均支持；不追加 atomic/pthread 链接，由 OHOS libc 提供） |
| 3 | 上游 `-Weverything -Werror` 在 clang 下告警即错 | ConfigureCompileFlags.cmake 对 clang 启用 -Werror | patches/0002：移除 clang/GNU 分支的 `-Werror`（与 vcpkg no-werror.patch 同思路） |
| 4 | 上游示例 LinkHut 依赖 PortAudio/ASIO 音频驱动 | examples/ 与 tests 在同一 CMake 工程，OHOS 无 PortAudio | `cmake.build(target=[...])` 只构建测试目标，不构建示例/扩展 |
| 5 | test_package 编译报 `'ableton/Link.hpp' file not found` | Conan 2 `copy()` 用 fnmatch 按文件相对路径匹配 pattern，`copy(self, "ableton", ...)` 只匹配名为 `ableton` 的文件，匹配不到 `ableton/Link.hpp`，头文件一个都没拷进包 | `package()` 改为 `copy(self, "*", src=include, dst=package/include, keep_path=True)` 整目录拷贝（asio 同改）；对照 cereal 等已合入配方写法 |

## 源码修改

- patches/0001-ohos-platform-config.patch：AbletonLinkConfig.cmake 增加 OHOS/HarmonyOS 平台分支
- patches/0002-remove-werror.patch：ConfigureCompileFlags.cmake 移除 -Werror

## 依赖版本

- asio 1.28.0（standalone，随包提供，无需 conan 依赖）
- Catch2 v2（third_party/catch，构建测试用，不打包）

## 验证结果

```bash
# 真机预检（hmbs 自动执行）：conan create 内联运行 LinkCoreTest + LinkDiscoveryTest
# 预期输出：All tests passed (N assertions in 25 test cases)，HMBS_UPSTREAM_TEST_RESULT status=passed
# test_package：test_abletonlink 5 个断言全部通过，HMBS_TEST_PACKAGE_RESULT passedCount=5
```

## 注意事项

- 库为 header-only，`package_type = "header-library"`，`cpp_info.libs` 为空
- `package_info()` 按 os 设置 `LINK_PLATFORM_*` 宏（OHOS/Linux → LINK_PLATFORM_LINUX），下游编译必需
- 包内随附 asio 头文件（`include/asio.hpp` + `include/asio/`），保证下游 `#include <ableton/Link.hpp>` 直接可编译
- 上游测试数字（25 用例、断言数）由真机框架输出为准，PR 正文不预填
