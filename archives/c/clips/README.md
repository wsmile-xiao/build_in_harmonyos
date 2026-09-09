# clips

CLIPS（"C" Language Integrated Production System）规则型专家系统：交互式
`clips` 解释器 + 可嵌入式 C 库（6.3 系列，上游 6.30 core source）。

## 简介

CLIPS 是 NASA Johnson 太空中心开发的公有领域前向链推理引擎，用可移植 C
编写，广泛用于规则/专家系统教学与嵌入式推理场景。本包适配 6.3 系列首发版
6.30（2014-08-16，SourceForge `clips_core_source_630.zip`；Debian 同源）。

## 主要特性

- 前向链推理（Rete 网络）：defrule / deftemplate / deffacts
- 面向对象 COOL：defclass / definstances / 消息传递
- 过程式编程：deffunction / defgeneric / defmodule
- 交互式 shell：`clips` 命令行（batch：`-f` / `-f2`，load：`-l`）
- 嵌入式 API：`CreateEnvironment` / `EnvBuild` / `EnvRun` /
  `EnvFunctionCall` 等整套 `Env*` 前缀多环境 API
  （`-DALLOW_ENVIRONMENT_GLOBALS=0`）
- 零外部依赖：纯 C，仅 libc + libm

## 构建

- `makefiles/makefile.lib` → `libclips.a`（163 个核心源文件）
- `main.c + libclips.a` → `bin/clips`（makefile 内注释的官方链接方式）
- 补丁 0001：makefile 工具链参数化（CC/AR/RANLIB/CFLAGS）

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 6.3（上游 6.30） | built（真机 conan create + test_package 10/10 + CLI 端到端全绿） | 2026-09-08 |
