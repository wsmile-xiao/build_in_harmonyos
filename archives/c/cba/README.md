# cba — Continuous Beam Analysis

cba 是一个计算**连续梁**杆件内力与支座反力的结构工程命令行工具（上游 cbeam 项目的 CLI 部分，含独立求解器类 `cbeam_class`）。

## 版本
- 0.3.6

## 许可证
- GPL-3.0-or-later

## 软件简介
cba 采用矩阵位移法（刚度法）求解连续梁：输入各跨跨度、刚度参数、支座约束（含弹簧支座）与荷载，输出每跨最大/最小弯矩、剪力、挠度与各支座反力包络值，支持恒载/活载分项系数及卸荷组合。

**主要功能**:
- 单跨到多跨连续梁静力分析（每跨可独立设置惯性矩/弹性模量）
- 6 种荷载类型：均布、集中、局部均布、弯矩、梯形（含三角形）、局部三角形
- 支座约束：简支 / 固定转动 / 弹性（弹簧）支座、支座位移
- 荷载分项组合：特征值（1.0,1.0）与设计值（如 1.35,1.5），支持卸荷系数（4 参 FACTORS）
- 输出 `-o` 跨内结果文件与 `-p` 图形数据文件（101 点/跨 × 7 列，可直接 gnuplot）

## 用法
```
cba -i inputfile [-o outputfile -p plotfile]
```
输入文件为纯文本（大小写不敏感，`#` 注释行），示例：
```
SPANS 5.8 4.2
INERTIA 3.69e-5 3.69e-5
ELASTICITY 2.1e8
CONSTRAINTS -1 0 -1 0 -1 0
LOAD 1 1 10.0 5.0 0 0
LOAD 2 1 10.0 5.0 0 0
FACTORS 1.35 1.5
```

## OpenHarmony 编译状态
- 状态: built
- 编译日期: 2026-09-05
- 构建系统: makefile（上游纯 Makefile 工程，无 configure.ac）
- 编译器: clang/clang++
- 平台: HarmonyOS PC (aarch64)

## 依赖
无外部依赖（纯 C++ 标准库）。wxWidgets GUI（wxCBA）未构建（CLI-only 适配，见下）。

## CLI-only 适配说明
上游 cbeam 0.3.6 的源码目录在 Makefile 层分离：`src/` 为纯命令行求解器 `cba`
（`cbeam_class.cpp` + `cba_main.cpp`，无第三方依赖），`src/gui/` 为 wxWidgets
图形界面 `cba-gtk`（wxCBA）。**上游没有任何 configure 脚本/开关**，故 CLI-only
的实现 = 只构建 `src/` 目标、跳过 `src/gui/`（与 Debian 的分离构建一致）。
`src/Makefile` 硬编码 `CXX := c++`，配方在 make 命令行覆盖为 OHOS clang++。

## 测试
上游无任何测试（无 tests/ 目录、无 make check/TESTS 目标、无 configure.ac）。
本仓库 test_package 提供完整覆盖：**11 用例 / 55 断言** ——
6 结构解析解比对（简支梁均布/跨中集中/四分之一集中、两等跨连续梁、分项系数
组合、上游 README 算例回归，41 断言）+ 4 CLI 参数与错误路径（8 断言）
+ 1 输出文件/plot 一致性（6 断言）。全部程序化构造输入，零二进制数据。

## 已知问题
- cba 无 `--version`；无参数时打印 usage 并以 exit 1 结束（CI L2 smoke 记 warn 不阻塞）
- 结果行输出为固定精度（弯矩/剪力/反力 2 位小数、挠度 3 位小数）
