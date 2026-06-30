# lmfit

C library for Levenberg-Marquardt minimization and least-squares curve fitting.

## 简介

lmfit 是一个用于 Levenberg-Marquardt 最小二乘法最小化和曲线拟合的 C/C++ 库。
它提供了以下核心功能：

- **lmmin**: 通用 Levenberg-Marquardt 最小化器
- **lmcurve**: 一维曲线拟合（简化接口）
- **lmcurve2**: 二维曲面拟合（简化接口）
- **lminvert**: 矩阵求逆

lmfit 是自包含的纯 C 库，无外部依赖，仅需 libc。

## 版本信息

| 版本 | 状态 | 编译日期 | 构建系统 |
|------|------|----------|----------|
| 10.0 | published | 2026-05-27 | cmake |

## 许可证

BSD-2-Clause (FreeBSD License)

## 链接

- 源码: https://jugit.fz-juelich.de/mlz/lmfit
- 主页: https://jugit.fz-juelich.de/mlz/lmfit

## HarmonyOS 编译要点

- 构建系统为 cmake（注意：URL不含"cmake"关键词，需手动指定 build_system）
- 推荐使用 out-of-source build 方式
- `LIB_MAN=OFF` 跳过 man 页面生成
- `PEDANTIC=OFF` 避免平台冗余警告
- 无需源码修改或补丁
- 仅编译为共享库 (liblmfit.so)，无 CLI 可执行文件