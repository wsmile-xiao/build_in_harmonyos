# SPOOLES

SPOOLES（SParse Object Oriented Linear Equations Solver）是 Boeing Phantom Works
发布的稀疏实数/复数线性方程组求解 C 语言库（公共领域），CalculiX 有限元求解器等的
构建依赖。采用面向对象风格设计的 45+ 功能模块（IV/DV/InpMtx/ETree/FrontMtx/…）。

## 功能特性

- 稀疏线性系统求解（实数/复数）
- 排序、符号分解、分解与回代全流程模块
- 纯 C 实现，无第三方依赖

## 版本信息

- 当前版本: 2.2（netlib，1999 年发布）
- 源码: https://www.netlib.org/linalg/spooles/spooles.2.2.tgz

## 依赖

- 无（仅需 C 编译器；MT/MPI 子目录默认不启用）

## 构建系统

- 纯 Makefile（无 configure）：`make -f makefile global -j1` 生成静态库

## 使用说明

SPOOLES 提供静态库 `libspooles.a`，头文件保留源码树相对布局，
消费方单 `-I<package>/include` 即可：

```bash
cc prog.c -I<spooles>/include <spooles>/lib/libspooles.a -lm -lpthread
```

```c
#include "SPOOLES.h"
#include "IV/IV.h"
#include "InpMtx/InpMtx.h"
```

CMake 消费：`find_package(spooles)` + `target_link_libraries(t spooles::spooles)`。

## 测试

上游 2.2 无可执行的官方测试套件（`drivers/` 示例需外部矩阵输入文件），
适配按 `no_tests` 如实申报；`test_package` 自带 IV/DV/InpMtx 真实 API
消费者测试（10 断言）。

## 许可证

公共领域（Public Domain，netlib 原文 "entirely within the public domain"）

## 相关资源

- 上游主页: https://www.netlib.org/linalg/spooles/spooles.2.2.html
- Spack 配方: https://github.com/spack/spack-packages（builtin/packages/spooles）
- 下游: CalculiX、preCICE adapter
