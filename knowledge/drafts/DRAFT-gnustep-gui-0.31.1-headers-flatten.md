# DRAFT-gnustep-gui-0.31.1-headers-flatten - GNUstepGUI 头文件平铺

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-31
> **Source event**: gnustep-gui 0.31.1 HarmonyOS PC adaptation, PR #7408

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 现象

gnustep-gui 0.31.1 打包后，`AppKit.h` 通过 `<GNUstepGUI/GSVersion.h>` 引用子头文件。
若安装布局把 GNUstepGUI 头文件嵌套在更深路径（如
`Library/Headers/GNUstepGUI/AppKit/...`），消费者编译 `<AppKit/AppKit.h>` 时
`<GNUstepGUI/GSVersion.h>` 无法解析，报 header not found。

## 根因

GNUstep GUI 头文件之间存在固定引用关系（`AppKit.h` → `<GNUstepGUI/GSVersion.h>`）。
Conan 打包若保持嵌套目录布局而不平铺，include 路径无法匹配该引用。

## 推荐方法

打包时把 GNUstepGUI 头文件平铺到 `Library/Headers/GNUstepGUI/`，
保证 `GSVersion.h` 位于 `<GNUstepGUI/GSVersion.h>` 可解析的扁平路径。

## 与已有知识的差异

- 不是一般的 include-path 缺失，而是 GNUstep 头文件引用约定的布局要求。

## 禁止做法

- 不要省略 GNUstepGUI 头文件（消费者经 AppKit.h 引用）。
- 不要硬编码绝对头文件路径。

## 证据来源

- `archives/g/gnustep-gui/0.31.1/conanfile.py`
- `archives/g/gnustep-gui/0.31.1/manifest.yaml`（knowledge_gained 第 7 条）
