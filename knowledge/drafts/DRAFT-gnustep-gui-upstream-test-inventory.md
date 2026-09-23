# DRAFT-gnustep-gui-upstream-test-inventory - gnustep-gui 的上游 Tests/ 库存必须单独记录

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-29
> **Source event**: gnustep-gui 0.32.0 HarmonyOS PC adaptation, PR #7095

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 现象

gnustep-gui 的发布 tarball 里确实有 `Tests/` 树，但它不是单一测试入口，而是混合了：

- 30 个 Objective-C 源测试文件；
- 19 个 `TestInfo` 描述文件；
- 2 个 `GNUmakefile` 入口或辅助文件。

如果只在 `test_package` 里跑一个 AppKit smoke test，然后把整个 upstream
Tests/ 统统视为“未统计”或“已通过”，报告就会失去可移植性边界。

## 根因

AppKit 类库的上游测试常常依赖目标运行时、GUI 环境或本机已安装的 GNUstep 生态。
在单包 HarmonyOS gate 中，消费者 smoke test 可以跑，但 upstream Tests/ 不一定能跑。
这不是“测试少了”，而是“执行面不同”。

## 推荐方法

把库存和执行分开记：

1. 在 `notes.md` 里记录 tarball 发现的测试结构；
2. 在 `test_package/MANIFEST.yml` 里记录 `upstream_test_inventory`；
3. 明确区分 discovered、executed 和 consumer tests；
4. consumer smoke test 保持独立，不混入 upstream tally。

## 与已有知识的差异

- 这不是单纯的 “0/0 tests” 问题。
- 也不是要把全部 upstream Tests/ 都强行塞进当前 gate。
- 重点是让读者知道：该库有真实的 upstream 库存，只是其中一部分在当前目标运行时上未执行。

## 禁止做法

- 不要把 consumer smoke test 计入 upstream inventory。
- 不要把 discovered inventory 直接写成 passed inventory。
- 不要只给出总数而不说明结构来源。

## 证据来源

- `archives/g/gnustep-gui/0.32.0.tar.gz`
- `archives/g/gnustep-gui/0.32.0/notes.md`
- `archives/g/gnustep-gui/0.32.0/test_package/MANIFEST.yml`
