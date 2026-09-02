# tl-generator 0.4.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists，header-only INTERFACE library）
- 编译日期: 2026-09-01
- 编译器: clang/clang++ 15.0.4（OHOS SDK），libc++ 15.0.4
- 目标平台: HarmonyOS PC (OHOS) aarch64（conan profile: ohos-aarch64）
- 构建工具: cmake 4.1.2 / make 4.4.1 / conan 2.29.1
- 状态: built

## 源码
- 官方源: `https://github.com/TartanLlama/generator` tag `v0.4.0`
- sha256: `5eb4189fae1b60bc8b7f09cd8dc8982c567ca22efce9a804a7ccc62d13e188ef`
- 结构: 单头文件 `include/tl/generator.hpp`（C++20 协程 generator，ranges 兼容）

## 适配要点
1. **Header-only 配方**：上游为纯头文件库（CMake `add_library(generator INTERFACE)`），
   无 .a/.so 产物。conanfile.py 采用 `package_type = "header-library"`，`package_id()` clear、
   `no_copy_source`，package() 仅复制 `include/tl/*.hpp` 与 LICENSE。
2. **上游测试在 build() 中运行**：`tests/test.cpp` 为 Catch2 v2 套件（4 cases, 45 assertions）。
   在 build() 内用 clang++ -std=c++20 编译并运行，作为 L1 上游测试门禁。
3. **OHOS 工具链限制（std::views）**：环境 libc++ 15.0.4 未实现 C++20 ranges
   （`__cpp_lib_ranges` 未定义，`std::views::take` 不可用）。上游 `iota` 用例使用
   `std::views::take(10)`，改为等价的手工 take 循环（语义不变：取前 10 个 iota 值并与
   计数器比对）。其余用例原样通过。
4. **test_package 消费者测试**：真实调用 `tl::generator<int>`（firstn）与
   `tl::generator<std::vector<std::string>>`（split_lines），编译运行于 OHOS aarch64。

## 编译步骤（本地适配验证）

```bash
# 消费者冒烟编译运行（header-only）
clang++ -std=c++20 -I<src>/include consumer.cpp -o consumer && ./consumer
# 输出: OK: iterated 20 values

# 上游完整测试（Catch2 v2.13.9 单头文件）
clang++ -std=c++20 -I<src>/include -I<catch2>/single_include <src>/tests/test.cpp -DCATCH_CONFIG_MAIN -o tlg-tests && ./tlg-tests
# 输出: All tests passed (45 assertions in 4 test cases)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `std::views` not in namespace std | OHOS libc++ 15 无 `__cpp_lib_ranges` | iota 用例改为手工 take 循环（等语义） |
| 2 | conan-init 生成 autotools 模板 | 模板默认 autotools | 重写为 header-library CMake 配方 |
| 3 | github 直连超时 | 网络到 github.com 不可达 | 下载走 gh-proxy 镜像；conandata 仅保留官方单 URL（R39），镜像 fallback 由 CI 下载层负责 |
| 4 | clang 对无扩展名源文件报 linker error | test.cpp.adapted 无 .cpp 后缀 | 复制为 .cpp 再编译 |

## 依赖版本
- 无第三方运行时依赖（header-only，仅需 C++20 协程支持）

## 验证结果
```bash
# 上游测试：All tests passed (45 assertions in 4 test cases)
# test_package：test_tl-generator: ALL PASSED
```
---

**编译结束**: 2026-09-01 16:48
**最终状态**: built
