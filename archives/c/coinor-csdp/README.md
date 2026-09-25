# coinor-csdp（COIN-OR CSDP）

半定规划（Semidefinite Programming, SDP）求解器，COIN-OR 数学规划家族成员，C 语言实现，以命令行工具 + 静态库形式提供。

## 功能概述

- `csdp`：读取 SDPA 稀疏格式（`.dat-s`）的半定规划问题并求解，输出原始/对偶目标值、DIMACS 误差度量与解文件。
- `theta`：计算图的 Lovász theta 数（基于 SDP 的图不变量）。
- `complement` / `rand_graph` / `graphtoprob`：图输入输出辅助工具（求图补、随机图生成、图转 SDP 问题）。
- `libsdp.a` + `include/`：C API（`read_prob` / `initsoln` / `easy_sdp` / `write_prob` / `free_prob` 等），供程序内直接调用求解器。
- `example/`：`easy_sdp()` 接口的官方示例程序（随源码分发，不随包交付）。

## OHOS 适配要点

- 构建系统为纯 GNU make（无 configure）；编译标志与链接库一律在 make **命令行**显式钉死，不依赖环境 flags（详见版本级 `notes.md` 与 `conanfile.py`）。
- BLAS/LAPACK 取 Conan 包 `openblas`（静态归档直链），交付的可执行文件自包含（`NEEDED` 只依赖 `libc.so`），可脱离运行环境直接执行。
- 可执行文件运行前需 `binary-sign-tool` 自签（HarmonyOS 加载器要求，否则 EPERM）；包内产物已签。
- 5 个命令行工具支持 `--version` / `--help`（上游原版把该参数当输入文件打开）。
- 上游未启用 OpenMP 多线程路径（`-fopenmp`/`USEOPENMP`）：串行路径为上游自带正确代码，求解结果与参考输出一致；这是与 Linux 发行版构建（常见开 OpenMP）的主要差异。
- 与 Linux 无其他行为差异：无平台宏、无 ISA 专属代码路径，纯可移植 C。

## 已知问题（软件级）

- matlab/octave 接口未交付（上游顶层 `make all` 亦不构建，环境无 matlab/octave）。
- 只提供静态库（上游无 shared 构建形态）。

## 依赖关系

- 编译依赖：`openblas`（BLAS + LAPACK 实现；上游 INSTALL 亦推荐 OpenBLAS）。
- 运行依赖：交付的可执行文件自包含，无额外运行时依赖；作为库被消费时由 Conan 传递 `openblas` 链接闭包。
- 构建工具：GNU make + clang（HarmonyOS 工具链）。

## 参考资料

- 官网/项目主页：https://github.com/coin-or/Csdp
- 源码仓库：https://github.com/coin-or/Csdp（tag `releases/*`）
- COIN-OR 项目集合：https://www.coin-or.org/
- SDPA 格式说明与手册：上游 `doc/csdpuser.pdf`（源码树内）
