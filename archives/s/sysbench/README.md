# sysbench

Sysbench是一个模块化、跨平台、多线程的性能基准测试工具，用于评估系统各种子系统的性能。

## 基本信息

- **版本**: 1.0.20
- **构建系统**: autotools
- **编译日期**: 2026-05-27
- **状态**: built

## 简介

Sysbench支持CPU性能测试、内存性能测试、文件I/O性能测试、线程调度性能测试、互斥锁性能测试以及数据库OLTP性能测试。

## 已编译版本

| 版本 | 状态 | 预编译包 | 补丁数 |
|------|------|----------|--------|
| 1.0.20 | built | ❌ | 53 |

## OHOS 适配要点

### 内嵌依赖编译
- sysbench 1.0.20 内嵌了 LuaJIT 2.1.0-beta2 和 ConcurrencyKit
- 需手动编译内嵌的 LuaJIT（使用clang）
- 需修改 ConcurrencyKit configure 支持 HarmonyOS

### autotools 文件缺失
- 需添加 pkg.m4 文件解决 PKG_CHECK_MODULES 宏缺失
- 需复制 autotools 辅助文件（config.guess, config.sub等）

### pthread_cancel 问题
- sb_thread.c 中 pthread_cancel 在 OHOS/musl 上不可用
- 需添加 __OHOS__ 守卫使用替代方案

## 依赖

- 内嵌 LuaJIT
- 内嵌 ConcurrencyKit
- libaio（运行时）

## 功能验证

```bash
sysbench --version
# 输出: sysbench 1.0.20
```

## 参考

- 官网: https://github.com/akopytov/sysbench