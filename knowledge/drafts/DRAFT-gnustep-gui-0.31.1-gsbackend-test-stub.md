# DRAFT-gnustep-gui-0.31.1-gsbackend-test-stub - GSBackend 需要最小 stub

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-31
> **Source event**: gnustep-gui 0.31.1 HarmonyOS PC adaptation, PR #7408

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 现象

gnustep-gui 0.31.1 的 test_package（ObjC AppKit 消费者测试）需要实例化 AppKit 类。
在 OHOS 上，AppKit 的 backend（窗口/图形服务）由应用侧链接的后端库（如 gnustep-back）
提供，gnustep-gui 包本身不包含 backend 类。缺少 backend 时链接或运行会失败。

## 根因

GNUstep AppKit 架构中 backend 是独立组件，由应用侧负责链接。独立的 test_package
若要跑 AppKit 冒烟测试，必须自行提供最小 GSBackend stub 以满足 backend 查找与链接。

## 推荐方法

在 test_package 中添加最小 GSBackend stub（`gsbackend_stub.m`），并在构建中引用它，
使 AppKit 消费者测试可以编译、链接并运行，而无需真实 gnustep-back。

## 与已有知识的差异

- 不是补丁问题，而是 AppKit backend 组件模型的消费端要求。
- 与普通 C 库 test_package 不同：ObjC AppKit 需要 backend 链路。

## 禁止做法

- 不要假定 backend 类随 gnustep-gui 包一起提供。
- 不要因 backend 缺失就完全跳过 test_package（会违反 L0c 测试实质门禁）。

## 证据来源

- `archives/g/gnustep-gui/0.31.1/test_package/gsbackend_stub.m`
- `archives/g/gnustep-gui/0.31.1/manifest.yaml`（knowledge_gained 第 6 条）
