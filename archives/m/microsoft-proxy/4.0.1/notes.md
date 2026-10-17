# microsoft-proxy 4.0.1 适配笔记（R01 第一轮完整适配）

## 官方来源核验（2026-09-02）

- 官方仓库: https://github.com/microsoft/proxy（"A library that accelerates C++
  development by means of runtime polymorphism"）
- 正式版本: 4.0.1，release tag 为 `4.0.1`（**无 `v` 前缀**；`v4.0.1` 返回 404）
  - 发布: 2025-10-05T07:31:31Z | "Proxy 4.0.1 Release"
- 官方源码 tarball: https://github.com/microsoft/proxy/archive/refs/tags/4.0.1.tar.gz
  - SHA-256: `78e1d88c36d2e7ee8f8dc47f112cdb96b8838dfd4177e104b53d9b64ed9b2357`
  - 与 GitHub API 完整源码树逐字节一致（diff -r CONTENT_IDENTICAL）
- 许可证: MIT（头文件头部 "Copyright (c) Microsoft Corporation. Licensed under the MIT License."）
- 形态: **header-only C++20**，CMake `INTERFACE` 库（`msft_proxy4::proxy` 目标），
  安装头文件 + `msft_proxy4Config.cmake`（`find_package(msft_proxy4)` 可用）

## 配方要点

- `package_type = "header-library"`，`CMakeToolchain` + `CMake` configure/build/install
- OHOS 交叉编译：`CMAKE_SYSTEM_NAME=Linux`、`CMAKE_SYSTEM_PROCESSOR=aarch64`（R32）
- `BUILD_TESTING=OFF` / `PROXY_BUILD_MODULES=OFF`（测试经 test_package 单独验证）
- `cpp_info`: `cmake_file_name=msft_proxy4`、`cmake_target_name=msft_proxy4::proxy`
- test_package：`example`（上游 API 真实调用）+ `ohos_test`（鸿蒙专项，见下）

## OHOS 工具链适配补丁（patches/0001-ohos-libcxx-format-and-ranges-compat.patch）

根因：OHOS SDK26 libc++ 15.0.4 在 `__config` 定义
`_LIBCPP_HAS_NO_INCOMPLETE_FORMAT`（`<format>` 为空 stub，无 `std::formatter`/
`std::format_context`）与 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES`
（无 `std::ranges::uninitialized_copy`），且不提供 `<memory_resource>` 头。
proxy.h 用 `__has_include(<format>)` 探测（stub 存在 → 误判可用）并直接使用
`std::ranges::uninitialized_copy`，导致 OHOS 下编译失败。

补丁（libc 能力探测类，R8 例外，非平台宏，全工具链可编译）：
1. format 守卫改用标准特性宏 `defined(__cpp_lib_format) && __cpp_lib_format >= 202110L`
   （4 处：1 个 include + 3 个 format skill/适配器块）
2. 5 处 `std::ranges::uninitialized_copy(a, b)` → 等价的经典算法
   `std::uninitialized_copy(std::begin(a), std::end(a), b)`（OHOS libc++ 提供）

验证：`conan create`（ohos-aarch64 profile）exit 0；test_package 编译并运行输出
`circle/square/proxy test_package OK`；`ohos_test` 输出 `PASS`。

## 上游测试台账（统计口径与通过率）

全量发现 249 个独立 gtest TEST_CASE（12 个测试源文件，`grep -cE "^TEST(_F|_P)?\("` 逐文件枚举）：
- 可运行并全部通过 107 个（6 文件：fmt_format 2、lifetime 65、reflection 4、regression 2、
  rtti 26、view 8；proxy_traits 为纯编译期断言 0 用例，编译通过）
- 硬阻塞 142 个（5 文件，**工具链能力缺口，非本库缺陷**）：
  - creation 51 / integration 2：缺 `<memory_resource>` 头（OHOS libc++ 无）
  - dispatch 74 / format 2：使用 `std::format`（`<format>` 为 stub）
  - invocation 13：`std::ranges::for_each` 缺失 + `<memory_resource>`
- **全量通过率 = 107 / 249 = 43.0%**（实际运行子集 100%：107/107）
- 另：freestanding 自定义 main 测试编译并运行通过（rc 0）；benchmarks/ 为基准非用例；
  modules/（C++20 module 测试）默认 `PROXY_BUILD_MODULES=OFF` 不构建
- 恢复条件：OHOS SDK/libc++ 补齐 `<format>`/ranges 算法/`<memory_resource>`
  （阻塞为工具链侧，162 个用例与库本身无关）

## 鸿蒙专项测试（新增，非空壳）

`test_package/ohos_test.cpp`（R34 实质 API 调用）：
- 编译期验证 OHOS 工具链下 `__cpp_lib_format` 未定义（format skill 正确禁用）
- 运行时验证 facade 派发（raw pointer + make_proxy 就地持有）、trivial copy
  （补丁后经典 `std::uninitialized_copy` 路径）、swap/trivial relocate 路径
- conan create 实际执行输出：`microsoft-proxy OHOS-specific test PASS`

## 状态

- 已完成配方/补丁/元数据/测试台账；W2 结构完整性（test_package、conanfile.py、
  测试源、MANIFEST.yml 齐备）；W3 本地 conan create 验证通过
- 依赖：header-only 无第三方依赖，R36 依赖发布检查不适用（W0 通过）
- 待完成：finish 归档、知识候选查重与路径判定、commit/push/PR
---

**编译结束**: 2026-09-03 00:17
**最终状态**: built
