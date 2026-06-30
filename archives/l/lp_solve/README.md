# lp_solve — Mixed Integer Linear Programming Solver

## 简介

lp_solve 是一个免费的混合整数线性规划（MILP）求解器，基于修正单纯形法和分支定界法。
它支持纯线性、混合整数/二进制、半连续和特殊有序集（SOS）模型。
lp_solve 使用 LGPL-2.1-or-later 许可证发布。

## 主要特性

- 线性规划（LP）求解
- 混合整数规划（MIP）求解
- 半连续变量支持
- SOS（特殊有序集）支持
- 内置 LUSOL 基分解引擎（默认）
- 支持 LP 和 MPS 文件格式
- 可通过共享库 API 嵌入其他程序

## 预编译包版本

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|---------|------|
| 5.5.2.14 | published | custom (Makefile) | 2026-06-09 |

## OpenHarmony 适配要点

1. ⭐ 必须使用 GNU ld (ld.bfd) 替代 lld
2. lp_solve 没有标准构建系统，使用自定义 `ccc` shell 脚本
3. 预生成的 flex/bison 代码使用 `lp_` 前缀，需编译器 `-D` 映射
4. 跨平台 API 用户应使用 `lp_lib.h` 而非 `lpsolve.h`

## 安装验证

```bash
lp_solve -h   # 显示版本 5.5.2.14
lp_solve model.lp   # 求解 LP 模型文件
```