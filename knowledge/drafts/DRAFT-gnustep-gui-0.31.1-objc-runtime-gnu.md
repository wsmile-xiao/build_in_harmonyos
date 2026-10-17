# DRAFT-gnustep-gui-0.31.1-objc-runtime-gnu - GNUstep GUI 必须与 gnustep-base 使用一致的 GNU ObjC 运行时

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-31
> **Source event**: gnustep-gui 0.31.1 HarmonyOS PC adaptation, PR #7408

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 现象

GNUstep GUI（AppKit 层）在 HarmonyOS PC 上通过 gnustep-make 构建时，若未显式指定
Objective-C 运行时，make 默认选择 "ng"（next-generation）runtime。由于下游
gnustep-base/1.31.1 与 libobjc2/2.2.1 均按 GNU runtime（`OBJC_RUNTIME_LIB=gnu`）
构建，GUI 层若用 ng runtime 会产生运行时/ABI 不兼容，导致 AppKit 代码链接或运行失败。

## 根因

GNUstep 的运行时选择贯穿 configure、编译和链接：`OBJC_RUNTIME_LIB` 决定使用哪个
`-fobjc-runtime` 与 `-fconstant-string-class`。同一依赖链上的 base/gui/back 必须
保持同一运行时 ABI，否则方法派发、常量字符串类、类注册表不兼容。

## 推荐方法

在配方构建环境（configure 与 make 共用同一环境）中导出：

```sh
export OBJC_RUNTIME_LIB=gnu
```

并保持与 gnustep-base 一致的编译/链接旗标：
`-fobjc-runtime=gcc -fconstant-string-class=NSConstantString`。

## 与已有知识的差异

- 与 `DRAFT-gnustep-base-1.31.1-objc-runtime-consumer` 侧重不同：base 草稿面向
  "消费 base 的下游需要传播 runtime 旗标"；本草稿面向"GNUstep GUI 自身构建必须
  用 gnu runtime，避免默认 ng runtime"。

## 禁止做法

- 不要使用默认 ng runtime 构建 GNUstep 应用层库。
- 不要在 configure 与 make 之间切换不同 runtime。

## 证据来源

- `archives/g/gnustep-gui/0.31.1/conanfile.py`
- `archives/g/gnustep-gui/0.31.1/manifest.yaml`（knowledge_gained 第 1 条）
- `archives/g/gnustep-gui/0.31.1/notes.md`
