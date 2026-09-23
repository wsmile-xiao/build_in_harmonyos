# tinygltf 2.9.3 适配笔记

## 编译环境

- 构建系统：上游 CMakeLists.txt（TINYGLTF_HEADER_ONLY=ON：INTERFACE 目标
  + 安装 4 个头文件与 CMake 导出）
- 编译日期：2026-09-12
- 编译器：Conan OHOS profile 提供的 clang++（C++11）
- 状态：built

## 版本与源码

上游 tag v2.9.3（https://github.com/syoyo/tinygltf），官方 tarball
`https://github.com/syoyo/tinygltf/archive/refs/tags/v2.9.3.tar.gz`，
SHA256 `c34443de2e9afaaf005713f69f5b061101a24ab2e9ee4021d882ac1d7983dbc0`。
tarball 内容：`tiny_gltf.h`（header-only/编译两用主头）、内嵌依赖
`json.hpp`/`stb_image.h`/`stb_image_write.h`、编译模式源 `tiny_gltf.cc`、
`tests/`（tester.cc 内嵌 Catch + 测试资产）、`models/`（glTF 模型资产）、
`examples/`（演示）、顶层 CMakeLists/Makefile。tag v2.9.3 直接指向 commit
`14ba27113ebd507ebeb7cba8ecaeab8df3921b27`。

## 适配方式

配方按 `package_type = "header-library"` + 上游 CMake `TINYGLTF_HEADER_ONLY=ON`
模式：INTERFACE 目标 `tinygltf::tinygltf`，`cmake.install()` 安装
`tiny_gltf.h`、`json.hpp`、`stb_image.h`、`stb_image_write.h` 与 CMake
导出配置；`cpp_info.libs = []`。关闭 loader_example/GL examples 演示构建。

## 上游测试（四维账本）

- N_static（静态声明）：34 —— `tests/tester.cc` 的 `TEST_CASE(` 宏逐项
  计数 34 个用例（内嵌 Catch 框架）。
- N_registered：34（Catch 运行时注册，与静态清点一致）。
- N_executed：68 —— 上游 `tests/Makefile` 构建两个变体程序：`tester` 与
  `tester_noexcept`（`-DTINYGLTF_NOEXCEPTION`），各自完整运行 34 用例，
  34 x 2 = 68 次用例执行。
- 通过：68 次执行全部通过，Catch 输出
  `All tests passed (303 assertions in 34 test cases)`（每变体 303 断言）。
- 未执行/跳过：0。测试资产（tests/*.gltf/*.glb 与 models/）随 tarball
  提供，OHOS 真机以 cwd=tests 运行，无外部依赖。

## 消费者测试

`test_package/test_tinygltf.cpp`：TINYGLTF_IMPLEMENTATION 编译模式，
解析内嵌的最小 glTF 2.0 资产（data-uri buffer），5 项断言：解析成功、
asset 版本 2.0、场景图解析（scene→node→mesh）、POSITION 属性、accessor
componentType/count/type。全部通过。

## 依赖

无（json.hpp 与 stb 头由上游内嵌并随包安装）。

## 路径 B 判断

判断依据（按 AGENTS §6.2 要求记录）：候选知识主题为 header-only+CMake
INTERFACE 导出配方与 Catch 内嵌测试的 makefile-programs 实测模式。查重：
E257/E321/E322/E470 覆盖 header-only 配方，klib/pcg-cpp 先例覆盖
makefile-programs 直编实测模式，均无超出既有条目的新知识增量。结论：
**不走路径 B**，按纯路径 A 交付。
---

**编译结束**: 2026-09-12 08:04
**最终状态**: built
