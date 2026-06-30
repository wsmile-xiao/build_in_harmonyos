# bossa

**BOSSA** (Basic Open Source SAM-BA Application) — Atmel SAM 微控制器烧录工具。

## 简介

BOSSA 是用于 Atmel SAM（Smart ARM）微控制器的 Flash 编程工具，通过 USB 编程端口对 SAM 设备进行烧录。提供命令行工具 `bossac` 和交互式 Shell `bossash`。

在 HarmonyOS/OpenHarmony 平台上，仅编译 CLI 工具：
- **bossac**: 命令行烧录工具（支持 -e 擦除、-w 写入、-v 校验、-r 读取等操作）
- **bossash**: 交互式烧录 Shell（支持 bossa> 命令行交互）

GUI 工具 `bossa` 需要 wxWidgets，该平台不提供，因此不编译。

## 可用版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.9.1 | published | 仅 CLI 工具（bossac + bossash） |

## 依赖

- readline 8.2（bossash 交互式 Shell 所需）

## 编译要点

- 纯 Makefile 项目，无 configure 步骤
- Makefile 已内置 HarmonyOS 规则（`ifeq ($(OS),Harmony)`）
- VERSION 变量需手动覆盖（`git describe` 在非 git 源码目录失败）
- 需指定目标 `make bossac bossash`（generic `all` 目标覆盖了 HarmonyOS `all`）
- 需使用 `make -B install`（`install` 目标与 `install/` 目录同名冲突）
- 无源码补丁，仅需 make 参数覆盖
