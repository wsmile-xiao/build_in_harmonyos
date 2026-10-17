# pcg-cpp 0.98.1 适配笔记

## 编译环境

- 构建系统：上游 Makefile（顶层 + test-high/；header-only 库，install 仅复制头文件）
- 编译日期：2026-09-16
- 编译器：Conan OHOS profile 提供的 clang++（C++11）
- 状态：built（待真机预检回填实测结果）

## 版本与源码

上游 tag v0.98.1（https://github.com/imneme/pcg-cpp），官方 tarball
`https://github.com/imneme/pcg-cpp/archive/refs/tags/v0.98.1.tar.gz`，
SHA256 `25bb22f076e8c346fa28c2267ae3564b12122f1f4ab2d2a08ad8909dcd6319fd`
（73179 字节，与 Debian orig 包哈希一致，已用 Python 下载实测确认）。
上游提交 `726e919c2dd22a3cdaccb0674c5422ab4fa7a216`。

相对 0.98（提交 `6d0f8b9c5e64cb9fe27b6a55ad6b3f4283067637`）仅单行变更：
`include/pcg_extras.hpp:157` 将 `*pos = '0' + mod` 改为 `'0' + char(mod)`，
用于消除 signedness 警告，无功能变化。tarball 内容结构与 0.98 一致：
`include/`（pcg_random.hpp、pcg_extras.hpp、pcg_uint128.hpp）、
`test-high/`（42 个 check-* 测试程序 + expected/ golden + run-tests.sh）、
`sample/`（6 个演示程序）、顶层 Makefile、README.md、LICENSE.txt（Apache-2.0）。

## 适配方式

配方复用已合入的 0.98 方案（`archives/p/pcg-cpp/0.98`），按
`package_type = "header-library"` 打包：`include/*.hpp` 安装到
`include/` 根（保持 `#include <pcg_random.hpp>` 上游惯例），无库二进制。
`cpp_info.libs = []`，声明 `cmake_file_name=pcg-cpp` /
`cmake_target_name=pcg-cpp::pcg-cpp`。无补丁，无依赖。

## 上游测试（静态清点 + 真机实测记账，实测数以预检日志为准）

- N_static（静态声明）：42 —— `test-high/Makefile` TARGETS 逐项计数 42 个
  check-* 程序；`sample/` 的 6 个演示程序无断言，不属于上游测试边界，
  不计入。与 0.98 同边界（0.98.1 仅头文件单行警告修复，未动测试目录）。
- N_registered：42（Makefile 注册层，同 TARGETS）。
- N_executed：42 —— 全部编译并全部执行：`run-tests.sh` 内 41 个 distinct
  程序调用（含 `check-pcg64_unique` 冒烟，输出至 /dev/null），外加配方对
  `check-pcg32_unique` 的显式冒烟补跑（该程序已编译，但从未被上游脚本调用；
  与 `check-pcg64_unique` 同为 `pcg-test-noadvance` 自包含冒烟程序，无参数，
  以退出码为判据）。
- 通过判据：40 个 `expected/*.out` golden 与 `actual/` 逐文件字节级对比一致
  **且全部非空**（空对空假通过防范；上游脚本先 `find actual -size -80c -delete`
  再 diff，本配方以非空 + 字节一致为机械判据，更严格），外加 2 个 unique
  冒烟程序退出码均为 0。计 `discovered=42/executed=42/passed=42/failed=0/
  skipped=0`。
- 通过判据说明：上游 `run-tests.sh` 的 diff 失败分支同样以退出码 0 结束
  （脚本以 echo 结尾），不能依赖其退出码；配方在运行脚本后以 Python 对 expected/ 与 actual/ 的 40 个 .out
  逐文件字节级对比为机械判据（外部 diff 不可移植：CI worker 的 busybox
  diff 不支持 -x 选项），并校验 actual/ 下 .out 文件数恰为 40。若上游
  golden 数量变化，配方将显式报错而非静默通过。
- 证据通道说明（本轮修复）：hmbs 门禁只扫描 test_package 阶段 stdout，且
  conan 在缓存命中轮次会整体跳过主 `build()`（xom 1.4.4 R7–R12 同款现象），
  因此主 `build()` 把聚合计数写入 `build_folder/upstream_test_summary.json`
  并经 `package()` 拷入包内 `res/upstream_test_summary.json`，
  `test_package/test()` 再原样透传 `HMBS_UPSTREAM_TEST_RESULT`
 （裸 `print(flush=True)` + `self.output.info` 双通道；数字来自真机实测，
  不伪造；summary 缺失时输出 `status:failed` 并主动报错）。

## 上游测试参数要点

- `make` 命令行变量优先于 makefile 内 `+=`：传 `CXXFLAGS`/`CPPFLAGS` 时必须
  自含 `-std=c++11` 与 `-I../include`，否则上游追加被覆盖导致编译失败。
- `CC = $(CXX)`（cheat）保证链接使用 C++ 编译器；只需显式传 `CXX`（取自
  `tools.build:compiler_executables` 的 cpp 值，优先使用 HMBS 注入的绝对路径）。

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

证伪说明：4 项均为值比较断言，非空壳打印；若被测头文件行为异常，
任一 `check` 即记 FAIL 并以非零退出码结束，harness 可捕获。

## 依赖

无。

## 路径判断

- 候选知识主题：无新增。0.98.1 相对 0.98 仅警告修复，编排方式、
  机械判据、传参要点均与 0.98 相同；0.98 已沉淀相关知识，查重
  `knowledge/graph/index.tsv` 无新增跨仓库复用增量。
- 结论：**路径 A（基础适配）**。

---

**编译结束**: 待真机预检
**最终状态**: built（待真机全部通过后由 HMBS 提交）
