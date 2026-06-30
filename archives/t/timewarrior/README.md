# Timewarrior

## 简介

Timewarrior 是一个命令行时间跟踪工具，用于记录和管理时间分配。它是 Taskwarrior 项目的姊妹项目，专注于时间追踪功能。

## 主要功能

- **时间追踪**：记录任务开始和结束时间
- **时间汇总**：生成时间使用报告和统计
- **时间修正**：支持修改、删除、移动时间记录
- **标签系统**：使用标签分类时间记录
- **数据导出**：支持多种格式的数据导出
- **扩展性**：支持自定义报告和钩子脚本

## OHOS 适配

### 构建系统
- 使用 CMake 构建
- 需要 C++17 支持
- 编译器：Clang 15.0.4

### 特殊处理
- GitHub tarball 不包含 Git 子模块 `libshared`
- 需手动下载 libshared 并放置到 `src/libshared/` 目录
- 测试套件完整，可直接运行 `make test`

### 已验证版本
- timewarrior 1.9.1 ✅

## 依赖关系

### 编译依赖
- CMake >= 3.10
- Clang (C++17 支持)
- libshared (内嵌，需手动下载)

### 运行依赖
- 无外部运行依赖

## 参考资料

- 官网：https://timewarrior.net
- 源码：https://github.com/GothenburgBitFactory/timewarrior
- 文档：https://timewarrior.net/docs