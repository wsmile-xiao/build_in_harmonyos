# pcg-cpp 0.98 适配笔记

## 编译环境

- 构建系统：上游 Makefile（顶层 + test-high/；header-only 库，install 仅复制头文件）
- 编译日期：2026-09-12
- 编译器：Conan OHOS profile 提供的 clang++（C++11）
- 状态：built

## 版本与源码

上游 tag v0.98（https://github.com/imneme/pcg-cpp），官方 tarball
`https://github.com/imneme/pcg-cpp/archive/refs/tags/v0.98.tar.gz`，
SHA256 `dfe94583f529bf9c7bc4a65265f3c5c504b7964bd9b865f9e6115eca4c3f917c`。
tarball 内容：`include/`（pcg_random.hpp、pcg_extras.hpp、pcg_uint128.hpp）、
`test-high/`（42 个 check-* 测试程序 + expected/ golden + run-tests.sh）、
`sample/`（6 个演示程序）、顶层 Makefile、README.md、LICENSE.txt（Apache-2.0）。

## 适配方式

配方按 `package_type = "header-library"` 打包：`include/*.hpp` 安装到
`include/` 根（保持 `#include <pcg_random.hpp>` 上游惯例），无库二进制。
`cpp_info.libs = []`，声明 `cmake_file_name=pcg-cpp` /
`cmake_target_name=pcg-cpp::pcg-cpp`。

## 上游测试（四维账本）

- N_static（静态声明）：42 —— `test-high/Makefile` TARGETS 逐项计数 42 个
  check-* 程序；`sample/` 的 6 个演示程序无断言，不属于上游测试边界，
  不计入。
- N_registered：42（Makefile 注册层，同 TARGETS）。
- N_executed：41 —— `run-tests.sh` 执行其中 41 个：40 个输出写入 actual/
  与 expected/ golden 逐文件 diff；check-pcg64_unique 以 /dev/null 冒烟
  运行（有执行、输出未校验）。
- 未执行/跳过：1 —— check-pcg32_unique 未被上游 run-tests.sh 调用
  （属上游测试边界现状，非本适配跳过；该程序仍被编译）。
- 通过判据说明：上游 `run-tests.sh` 的 diff 失败分支同样以退出码 0 结束
  （脚本以 echo 结尾），不能依赖其退出码；配方在运行脚本后以 Python 对 expected/ 与 actual/ 的 40 个 .out
  逐文件字节级对比为机械判据（外部 diff 不可移植：CI worker 的 busybox
  diff 不支持 -x 选项），并校验 actual/ 下 .out 文件数恰为 40。真机实测：42 程序全部编译、40 个 golden
  对比全部一致（aarch64 为小端 + 原生 __int128，与 golden 生成环境语义
  一致，输出逐字节相同）。

## 上游测试参数要点

- `make` 命令行变量优先于 makefile 内 `+=`：传 `CXXFLAGS`/`CPPFLAGS` 时必须
  自含 `-std=c++11` 与 `-I../include`，否则上游追加被覆盖导致编译失败。
- `CC = $(CXX)`（cheat）保证链接使用 C++ 编译器；只需显式传 `CXX`。

## 消费者测试

`test_package/test_pcg.cpp`：以库使用者身份编译链接已安装包，4 项断言：

1. `pcg32 rng(42u, 54u)` 前 6 个输出复现上游 golden（
   0xa15c02b7 0x7b47f409 0xba1d3330 0x83d2f293 0xbfa4784b 0xcbed606e，
   取自 test-high/actual/check-pcg32.out Round 1 实测值）；
2. `pcg64 rng(42u, 54u)`（上游 check-pcg64 定义 TWO_ARG_INIT）前 6 个输出复现上游 golden（0x86b1da1d72062b68 等，
   取自 actual/check-pcg64.out Round 1 实测值）；
3. `backstep(3)` 回退后重放值一致；
4. `pcg_extras::seed_seq_from<std::random_device>` 重播种生效
   （重播种后输出与原序列不同）。

## 依赖

无。

## 路径 B 判断

判断依据（按 AGENTS §6.2 要求记录）：

- 候选知识主题：makefile-programs 类上游测试的 golden-diff 机械判据
  （脚本退出码不可信时以独立 diff 退出码判定）。
- 知识库查重：`knowledge/graph/index.tsv` 中 klib 先例（archives/k/klib，
  makefile-programs 模式：make 编译全部测试目标并逐个运行统计）已覆盖
  编排方式；run-tests.sh 退出码陷阱为单库脚本特性，通用性不足以独立成条；
  header-only 配方模式已有 E257/E321/E322/E470 覆盖。
- 结论：无跨仓库复用的新知识增量，**不走路径 B**，按纯路径 A 交付。
---

**编译结束**: 2026-09-12 04:34
**最终状态**: built
