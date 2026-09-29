# libmcfp 2.1.1 — 适配记录

> 上游: https://github.com/mhekkel/libmcfp/archive/refs/tags/v2.1.1.tar.gz （tag v2.1.1）
> sha256: 2edf570b25772a14395b7efc8c354e012b0b2c45d1cb00471cf2a5cad796fd45
> 工程类型: CMake (>= 3.28), C++23，从 src/*.cpp 编译真实库（libmcfp.a）+ 可选 C++20 module 库；BSD-2-Clause
> 用途: mcfp::config::instance() 单例收集命令行与 INI 配置（cif-tools 等下游硬依赖）

## 结论快照
- 产物: 编译库 libmcfp（lib/libmcfp.a）+ 头文件 include/mcfp/*.hpp + CMake 配置（lib/cmake/mcfp，
  find_package/mcfp 目标 mcfp::mcfp）。`package_type: library`，运行依赖无（纯编译依赖 fast_float）。
- 上游自动化测试: test/unit-test.cpp（35 TEST_CASE）+ test/lib-test.cpp（2 TEST_CASE）= 37 个
  Catch2 用例，conan build() 内置 ctest 全量运行（BUILD_TESTING=ON）。test-main.cpp 为框架运行器；
  unit-test-gaps.cpp 无 TEST_CASE 且未被 CMake 引用（未实例化，不计入用例数）。
- 消费者验证: test_package 真实编译链接 libmcfp::libmcfp 并 parse CLI（-n 7 --text hello -i a -i b）。

## 与 1.4.2 的历史差异（关键）
1. **1.4.2 是 header-only INTERFACE 库；2.1.1 编译真实库**：src/mcfp.cpp、options.cpp、text.cpp、
   charconv-fast_float.cpp → libmcfp.a，`target_compile_features(mcfp PUBLIC cxx_std_23)`（C++23）。
2. **新增 fast_float 依赖**：上游 `try_compile(STD_CHARCONV_COMPILING, CXX_STANDARD 23)` 探测
   `std::from_chars` 浮点解析；OHOS libc++（clang 15）的 float/double 重载为 deleted → 探测失败 →
   上游 `CPMFindPackage(FastFloat v8.0.2)` 从 github.com 拉取（CI 禁网）。
   方案：`requires fast_float/8.0.1`（ohpcd 已发布）+ 补丁 0001 改为 `find_package(fast_float CONFIG
   QUIET)` 优先（CPM 仅兜底），目标名 FastFloat::fast_float → fast_float::fast_float。
3. **测试依赖仍走 Catch2**：上游 test/CMakeLists.txt `CPMFindPackage(Catch2 3.4.0)` → 补丁 0002
   `find_package(Catch2 CONFIG QUIET)` 优先 + `requires catch2/3.8.1`（ohpcd 已发布）。
4. **MCFP_BUILD_CXX_MODULE=OFF**：上游默认构建 C++20 module 库（mcfp-module），clang 15 module
   支持为实验性，置 OFF；经典 `mcfp::mcfp` 目标不受影响。
5. CMakeToolchain 在 OHOS 置 `CMAKE_SYSTEM_NAME=Linux`（Linux-like 目标，同 fast_float / mcfp 1.4.2）。

## OHOS 关键适配（详见 conanfile.py）
1. `validate()` os 白名单 Linux/OHOS（R32）。
2. `BUILD_TESTING=ON` + 补丁 0001/0002 消除 configure 期 GitHub 网络拉取。
3. `package_info`: `cpp_info.libs=["mcfp"]`；上游安装段原样执行（lib/cmake/mcfp）。
4. test_package 消费者：find_package(libmcfp CONFIG) + target libmcfp::libmcfp，真实调用公开 API。

## 依赖关系
- 编译: fast_float/8.0.1（仅 OHOS 浮点 from_chars 缺失路径）+ catch2/3.8.1（test-only）。
- 运行: 无外部动态库（静态链接 libmcfp + 标准库）。

## 验证记录（true-device Harmony verify 后回填）
- [x] HARMONY_VERIFY conan create PASS（含 build() 内 ctest 全量运行与 test_package 消费者运行）
- [x] 上游 37 TEST_CASE 全量通过（unit-test 35 + lib-test 2）
- [x] test_package 消费者冒烟输出确认（num=7/text=hello/items=2）
---

**编译结束**: 2026-09-28 12:09
**最终状态**: built
