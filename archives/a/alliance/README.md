# Alliance VLSI CAD Tools

Alliance VLSI CAD System（LIP6）是一套以 C 语言为主的 VLSI EDA 工具链，
提供 VHDL 编译/仿真、逻辑综合、自动布局布线等能力。本适配构建其**核心库**部分。

## 功能概述

- `Mut`（mbk）：基础数据容器库（chain_list、内存分配 mbkalloc/mbkfree 等）
- `Rds`：版图数据读取库
- `Abl`：抽象网表库
- `Bdd`：二元决策图库
- `Fsm`：有限状态机库
- `Fvh`：VHDL 前端库

## OHOS 适配

- 构建系统：分散式 Autotools（71 个 configure.in + 231 个 Makefile.am，autostuff 驱动）
- v5.1.1 tag archive 为裸源码，构建时以 autoreconf 自举
- configure.in 现代化（AC_INIT/AM_INIT_AUTOMAKE/AM_PROG_LIBTOOL）适配 autoconf 2.72 / automake 1.18
- HMDFS：config.status umask 077 → 000；CONFIG_SHELL=/bin/sh；make -j1
- 7 个 GUI 工具（X11/Motif）裁剪不构建
- 静态库构建（R26）

## 依赖关系

- 编译依赖：无（纯 C，内部库互依赖）
- host 工具：autoconf / automake / libtool（ohpcd tool_requires）、flex / bison（设备原生）
- 运行依赖：libm

## 参考资料

- 官网：https://coriolis.lip6.fr/
- 上游仓库：https://github.com/lip6/alliance
- 积分赛 PR 模板：见本次交付报告
