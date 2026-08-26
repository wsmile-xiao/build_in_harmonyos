# libdivsufsort 2.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-25
- 编译器: clang/clang++
- 状态: published

## 上游信息

- 仓库: https://github.com/y-256/libdivsufsort
- Tag: 2.0.1
- 源码 URL: https://github.com/y-256/libdivsufsort/archive/refs/tags/2.0.1.tar.gz
- SHA256: `9164cb6044dcb6e430555721e3318d5a8f38871c2da9fd9256665746a69351e0`
- 许可证: MIT
- 描述: A lightweight suffix-sorting library (SA-IS algorithm)

## 上游测试调查

libdivsufsort 2.0.1 上游 **没有正式测试套件（0 个）**：
- 无 `enable_testing()` 调用
- 无 `add_test()` 注册
- 无 `tests/` 或 `test/` 目录
- 无 `ctest` 集成

上游正式测试数量：**0**

源码树中所有 `.c` 文件（共 9 个）：
| 文件 | 用途 |
|------|------|
| lib/divsufsort.c | 核心库实现 |
| lib/sssort.c | suffix-sort 子模块 |
| lib/trsort.c | tr-sort 子模块 |
| lib/utils.c | 工具函数 |
| examples/suftest.c | 后缀数组构造 + sufcheck 验证 |
| examples/bwt.c | BWT 变换 (divbwt) |
| examples/unbwt.c | 逆 BWT (inverse_bw_transform) |
| examples/mksary.c | 后缀数组构建工具 |
| examples/sasearch.c | 后缀数组二分搜索 (sa_search) |

上游另有 **5 个 example 程序**（suftest / bwt / unbwt / mksary /
sasearch），是上游唯一的功能验证产物。`suftest.c` 内部调用
`divsufsort()` + `sufcheck()`，构成对核心算法的验证链。

> ⚠️ examples **不计入**上游正式测试数量（正式测试 = 0）。
> examples 是功能性验证程序，在 conanfile.py 的 `build()` 中实际执行，
> 与 test_package 消费者测试独立。

## 编译步骤

```bash
# Conan 构建 (conan create 自动执行)
cmake -DBUILD_SHARED_LIBS=OFF \
      -DBUILD_EXAMPLES=ON \
      -DBUILD_DIVSUFSORT64=ON \
      -DUSE_OPENMP=OFF \
      -DWITH_LFS=ON
cmake --build .
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| - | 无 | 上游 CMake 原生支持 OHOS 交叉编译 | 无需补丁 |

## 库产物

上游 CMake 通过 `BUILD_DIVSUFSORT64` 选项同时构建两个独立库：

| 库名 | 头文件 | 索引类型 | 说明 |
|------|--------|----------|------|
| divsufsort | divsufsort.h | saidx_t (int32_t) | 32 位索引，默认构建 |
| divsufsort64 | divsufsort64.h | saidx64_t (int64_t) | 64 位索引，需 BUILD_DIVSUFSORT64=ON |

Conan recipe 暴露两个 components：
- `libdivsufsort::divsufsort` — 32 位索引库
- `libdivsufsort::divsufsort64` — 64 位索引库

## 验证结果

### 上游 examples (5 个，非正式测试)
suftest, bwt, unbwt, mksary, sasearch — 在 conanfile.py `build()` 中
于 HarmonyOS PC 实际执行（非仅编译检查）。

验证输入：`banana_bandana`（无尾换行，15 字节）。

| # | example | 验证内容 | 结果 |
|---|---------|----------|------|
| 1 | suftest input.txt | `divsufsort()` + `sufcheck()` 退出 0 | PASS |
| 2 | bwt input.txt input.bwt | `divbwt()` 生成 framed BWT 文件 | PASS |
| 3 | unbwt input.bwt restored.txt | `inverse_bw_transform()` 恢复原文，与 input.txt 字节一致 | PASS |
| 4 | mksary input.txt input.sa | 生成非空二进制后缀数组文件 | PASS |
| 5 | sasearch ana input.txt input.sa | `sa_search("ana")` 结果排序后 = [1, 3, 11] | PASS |

**Upstream examples: 5/5 PASS**（OHOS 实测）。

> examples 是功能性验证程序，**不计入**上游正式测试数量。
> 上游正式测试 = 0；上游 examples = 5。

### test_package 消费者测试（1 个，14 个断言）
test.c 对 "banana" 字符串执行完整验证链：
1. `divsufsort()` 构造后缀数组，验证 SA=[5,3,1,0,4,2]
2. `sufcheck()` 验证后缀数组正确性
3. `divbwt()` BWT 变换，验证输出 "nnbaaa"，pidx=4
4. `inverse_bw_transform()` 逆变换，验证恢复原始字符串
5. `divsufsort_version()` 版本字符串非空

共 14 个断言，全部通过。test_package 现有断言未改动。

## 依赖版本

无外部依赖（纯 C 库，仅依赖标准 C 头文件）。

## 注意事项

- 上游 CMake 不生成 CMake config 文件 (`*-config.cmake`)，消费者通过
  Conan CMakeDeps 生成的 `libdivsufsort-config.cmake` 进行 find_package。
- `VERSION` 文件内容为 "2.0.0"（上游标记），但 tag 为 2.0.1；这是上游
  的已知状态，不影响功能。
