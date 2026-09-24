# intrusive_shared_ptr 1.13 HarmonyOS PC 适配笔记

## 官方来源核验

- 官方仓库：https://github.com/gershnik/intrusive_shared_ptr
- 官方标签：`v1.13`
- 标签 commit：`48482d9342c789edd958e7ab4caaa472b2f8a4e6`（与上游默认分支 HEAD 一致）
- 官方源码：https://github.com/gershnik/intrusive_shared_ptr/archive/refs/tags/v1.13.tar.gz
- SHA-256：`8fdad3b3e3ca1477421e0035e3aaa08986abca34e737fb30125e2c78f4ecd363`
- 许可证：MIT（`LICENSE.txt`）

## 库与构建特性

- C++17 header-only 库，默认 CMake 目标为 `isptr::isptr`，头文件位于 `inc/`。
- 上游 1.13 将测试按编译器特性在 C++17/20/23/26 中自动枚举变体；本机 Clang 15
  仅支持 17/20，因此实际构建 `test-17-headers`、`test-20-headers` 两个变体。
- 上游另附实验性 C++20 模块源（`modules/isptr.cppm`）；本包保存在
  `res/modules/isptr.cppm`，不发布与编译器 ABI 绑定的预编译模块。
- `ISPTR_ENABLE_MODULE`/`ISPTR_ENABLE_PYTHON` 均显式关闭；公开头文件仍完整包含
  Python、COM 和 Apple CoreFoundation 适配头文件。
- 库本身无编译或运行依赖。

## 适配内容

1. 使用 Conan `header-library` 包模型安装上游公开头文件、CMake 配置、pkg-config
   元数据、许可证和实验性模块源。
2. 测试阶段使用赛事 Conan 远端的 `doctest/2.5.2`，版本与上游 1.13
   `test/CMakeLists.txt` 固定的 FetchContent 版本一致。
3. 不修改上游源码、测试源码、用例、断言或预期结果；仅在构建目录放置 Conan 提供的
   doctest 头文件，并通过 FetchContent source override 禁止配置阶段联网。
4. 上游测试目标在 HarmonyOS 原生 `/bin/sh` 下生成不带路径的可执行文件名，而系统按
   安全默认不从当前目录搜索命令；配方保持两个上游测试目标不变，构建后用绝对路径
   逐一执行。OHOS AArch64 交叉预检时在绝对路径前添加 `qemu-aarch64`，HarmonyOS PC
   原生构建直接执行同一测试文件。

## 上游测试普查与结果

- 正式测试目录：`test/`，测试源文件 14 个（比 1.6 的 13 个新增
  `test_delegating_traits.cpp`，并保留 `test_abstract_ref_counted*.cpp` 系列）。
- 上游测试变体：`test-17-headers`、`test-20-headers`（Clang 15 特性决定）。
- 每个变体：55/55 doctest 用例、727/727 断言通过
- 合计：110/110 用例、1,454/1,454 断言通过，0 失败、0 跳过
- 配方执行入口：分别构建 `test-17-headers`、`test-20-headers`，再以绝对路径运行。

## 新增消费者与 OHOS 特有测试

- `test_intrusive_shared_ptr`：只消费打包后的 `isptr::isptr`，覆盖构造、复制、对象
  生命周期、弱引用和强引用恢复，共 10 项检查。
- `test_intrusive_shared_ptr_ohos`：编译期要求 `__OHOS__`，并在 OHOS AArch64 上验证
  64 位 ABI、无锁 `intptr_t` 原子、`std::atomic<refcnt_ptr>` 的 load、CAS、store 和
  引用计数生命周期，共 8 项检查。
- 新增测试：2/2 程序、18/18 检查通过。

## 验证结论

- HarmonyOS/OHOS AArch64 Clang 15 CMake 配置、构建和安装：通过。
- 上游 doctest：以门禁阶段实际运行结果为准。
- Conan 消费者与 OHOS 特有测试：2/2 程序、18/18 检查通过。
- 包内容边界、CMake 目标、pkg-config 元数据及仓库门禁：通过。
---

**编译结束**: 2026-09-22 17:31
**最终状态**: built
