# komihash 5.34 适配笔记

## 编译环境

- 构建系统：无（单头文件库，ISO C99，自动提供 C++ 兼容）
- 编译日期：2026-09-12
- 编译器：Conan OHOS profile 提供的 clang
- 状态：built

## 版本与源码

上游 tag 5.34（https://github.com/avaneev/komihash），官方 tarball
`https://github.com/avaneev/komihash/archive/refs/tags/5.34.tar.gz`，
SHA256 `c1a0c8228f3211d0c908dfe7249b9a98e2bea46ef342d241036f78c20d01c4d1`。
tarball 内容：`komihash.h`（1442 行，KOMIHASH_VER_STR "5.34"）、`testvec.c`
（version 5.9）、README.md、LICENSE、hash_comparison.png。无构建系统文件。

## 适配方式

配方按 `package_type = "header-library"` 打包：`komihash.h` 安装到
`include/` 根，保持上游 `#include "komihash.h"` 使用惯例；无库二进制。
`cpp_info.libs = []`，声明 `cmake_file_name=komihash` /
`cmake_target_name=komihash::komihash` 供 CMakeDeps 消费。

## 上游测试（四维账本）

- N_static（静态声明）：1 —— 上游唯一测试入口为 `testvec.c`；无测试框架、
  无断言宏（grep `assert(`/`TEST` 均为 0），静态测试程序数按可执行测试
  入口计 1。
- N_registered：1 —— 无构建系统注册层，testvec.c 即唯一可执行测试目标。
- N_executed：1 —— `build()` 内用 OHOS profile 编译器
  （`tools.build:compiler_executables` 的 `c`，回退 clang）以
  `-O2 -std=c99` 编译并运行，退出码 0。
- 未执行/跳过：0。
- 通过判据说明：testvec 是打印型向量程序（不自带断言），运行判据 =
  编译成功 + 退出码 0 + 输出结构完整（3 个 `komihash UseSeed` 段、
  15 个字符串向量行、51 个 `bulk(` 向量行、3 个 `komirand Seed1/Seed2`
  段，配方内逐一校验）。上游未随 tarball 提供 golden 输出文件，
  真实值断言由消费者测试以 README 官方参考向量
  `komihash("This is a test of komihash.", seed=0) = 5b13177fc68b4f96`
  补齐。

## 消费者测试

`test_package/test_komihash.c`：以库使用者身份编译链接已安装包，6 项断言：

1. 单发 `komihash` 与 README 参考向量一致；
2. `KOMIHASH_VER_STR == "5.34"`；
3. 流式接口（`komihash_stream_init/update/final`，输入拆两半）与单发一致；
4. `komirand` 连续两次输出不同；
5. `komirand` 更新种子状态；
6. `komihash_seedless` 与 `komihash(seed=0)` 一致（头文件文档明确
   "using the default seed of 0"）。

## 依赖

无。

## 路径 B 判断

判断依据（按 AGENTS §6.2 要求记录）：

- 候选知识主题：无构建系统单头库的 header-library 配方模式（build() 直编
  上游测试程序）。
- 知识库查重：`knowledge/graph/index.tsv` 中 E257（no-op build for
  header-only）、E321（header-only-lite Conan2 迁移）、E322（header-only
  CMake INTERFACE 配方）、E470（cppitertools header-only 配方）已系统覆盖
  该模式；klib（archives/k/klib）已提供 build() 内直编上游测试的完整先例。
- 结论：本任务无超出既有条目的跨仓库复用新知识增量，查重命中已有条目，
  **不走路径 B**，按纯路径 A 交付。
---

**编译结束**: 2026-09-12 01:01
**最终状态**: built
