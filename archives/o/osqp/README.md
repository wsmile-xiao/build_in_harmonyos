# OSQP — Operator Splitting Quadratic Program Solver

## 简介
OSQP 是一个免费开源的凸二次规划（QP）求解器。基于算子分裂方法（ADMM），设计高效、稳定且易用。提供 C 语言 API，适用于嵌入式和桌面场景。

## 功能特性
- 求解凸二次规划问题: min 0.5*x'Px + q'x, s.t. l <= Ax <= u
- ADMM 算子分裂算法
- 内嵌 QDLDL 线性求解器（基于 LDL 分解）
- C 语言 API，支持静态库和共享库
- 支持代码生成（嵌入式应用）
- 支持导数计算
- 支持用户中断（Ctrl-C）
- 自适应 rho 参数

## 版本信息
- 软件版本: 1.0.0
- 编译日期: 2026-06-16
- 目标平台: HarmonyOS aarch64 (OpenHarmony)
- 编译器: clang 15.0.4

## 构建信息
- 构建系统: cmake
- 关键配置选项:
  - `-DCMAKE_BUILD_TYPE=Release`
  - `-DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local`
  - `-DOSQP_BUILD_DEMO_EXE=OFF`
  - `-DOSQP_BUILD_UNITTESTS=OFF`
  - `-DOSQP_CODEGEN=OFF`
- 内嵌依赖: QDLDL v0.1.8

## 安装产物
- `lib/libosqp.so` — 共享库
- `lib/libosqpstatic.a` — 静态库
- `include/osqp/` — 6 个头文件
- `include/qdldl/` — 3 个头文件
- `lib/cmake/osqp/` — cmake 配置文件

## 链接方式
```bash
# 静态库链接（需补充 interrupt_unix.o）
clang -o myapp myapp.c interrupt_unix.o \
  -I~/usr/local/include -L~/usr/local/lib -losqpstatic -lm -lrt -ldl

# 共享库链接
clang -o myapp myapp.c \
  -I~/usr/local/include -L~/usr/local/lib -losqp -lm
```

## 使用示例
```c
#include "osqp/osqp.h"

// 最简 QP: min 0.5*2*x^2 + 1*x, s.t. x >= 0
// P=[2], q=[1], A=[1], l=[0], u=[INF]
OSQPInt n = 1, m = 1;
OSQPCscMatrix *P = OSQPCscMatrix_new(n, n, 1, P_x, P_i, P_p);
OSQPCscMatrix *A = OSQPCscMatrix_new(m, n, 1, A_x, A_i, A_p);
OSQPSettings *settings = malloc(sizeof(OSQPSettings));
osqp_set_default_settings(settings);

OSQPSolver *solver = NULL;
osqp_setup(&solver, P, q_val, A, l_val, u_val, m, n, settings);
osqp_solve(solver);
// solver->solution->x[0] 为最优解
// solver->info->obj_val 为目标值
```

## 许可证
Apache-2.0

## 参考
- 官网: https://osqp.org
- 源码: https://github.com/osqp/osqp
- 论文: Stellato et al., "OSQP: An Operator Splitting Solver for Quadratic Programs", Mathematical Programming Computation, 2020
