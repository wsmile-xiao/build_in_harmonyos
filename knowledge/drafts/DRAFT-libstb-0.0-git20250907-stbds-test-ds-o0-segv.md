# test_ds 在 clang-15/OHOS -O0 下 SIGSEGV（草稿）

- **来源**：libstb 0.0-git20250907.fede005 路径 B 上游套件真机执行
- **日期**：2026-09-15
- **证据**：真机隔离作业实测矩阵（`$HOME/tmp/libstb-pathb/`，10.62.178.77）、
  stb_ds.h 与 archives/s/stb_ds/0.67 包源码 diff 为空（逐字节一致）

## 现象

上游 `tests/test_ds.c` 以 `-DDS_TEST`（STBDS_UNIT_TESTS + STBDS_SMALL_BUCKET +
8 组 churn）编译运行：

```text
clang++ -O2 -std=c++17 -DDS_TEST → rc=0   "Ok!"
clang++ -O2 -std=gnu++14 -DDS_TEST → rc=0 "Ok!"
clang++ -O0 -std=c++17 -DDS_TEST → rc=139 Signal 11 (core dumped)，stdout 全空
```

裸 `clang++ -DDS_TEST`（无 -O 标志，默认 -O0）同样必崩，且在极早期（无任何
输出）。

## 排除项

- **不是头文件版本问题**：fede005 的 stb_ds.h 就是 v0.67，与已合入
  stb_ds/0.67 包（真机 "Ok!" 全过的先例）**逐字节一致**。
- **不是 C++ 标准版本问题**：c++17/gnu++14 在 -O2 均过。
- **包先例为何没踩到**：stb_ds/0.67 走 Conan 工具链 Release（-O2）构建。

## 定性

崩溃仅与优化级相关。两种可能未定论：clang-15 在 OHOS aarch64 的 -O0 代码
生成缺陷——与 catdoc 案件（clang-15 在 -O1+ 误编译需强制 -O0）**互为反向
镜像**，同一工具链两头的优化级各有一种病；或 stb_ds churn 依赖未定义行为
仅在无优化时显形。对 libstb 交付物无影响（配方与 test_package 不编译
test_ds；profile 为 Release）。

## 规避

编译运行 stb_ds 上游套件时显式 `-O2`（或经 Conan Release 工具链）。遇到
`-O0` SIGSEGV 先跑三格矩阵（O2×c++17 / O0×c++17 / O2×gnu++14）判定是否
优化级单因素，再决定修构建还是报工具链。
