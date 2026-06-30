# Menlo-Legacy

Legacy internal and client support for Menlo.

## 描述

Menlo-Legacy 是 cpanminus (App::cpanminus) 的遗留兼容模块，包含 `Menlo::CLI::Compat`，后者是 cpanm 经典版本内部和客户端行为的兼容层。

该模块使得 Carton、Carmel、App::cpm 等下游客户端可以依赖 cpanm 的稳定特性和行为。

## 模块类型

**纯 Perl 模块** — 无 XS/C 编译组件。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 1.9022 | built | 2026-06-17 |

## 依赖

### 声明依赖
- Menlo >= 1.9018
- version >= 0.9905

### 运行时传递依赖
- Class::Tiny >= 1.008
- File::Which >= 1.27
- String::ShellQuote >= 1.04

## 鸿蒙平台说明

- 纯 Perl 模块，不受 SELinux HMDFS 限制
- 可直接从 `~/usr/local/lib/site_perl/` 加载
- 无需 HNP 安装或特殊签名处理
- 与 perl-dbd-pg 等 XS 模块不同，不存在运行时限制
