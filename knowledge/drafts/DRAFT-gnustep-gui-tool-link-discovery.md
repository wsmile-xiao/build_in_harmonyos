# DRAFT-gnustep-gui-tool-link-discovery - GNUstep GUI tools 必须先解析到在树内共享库别名

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-29
> **Source event**: gnustep-gui 0.32.0 HarmonyOS PC adaptation, PR #7095

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 现象

GNUstep GUI 的 `Tools` 子项目在链接 `set_show_service`、`gpbs`、`gopen`、
`gcloseall` 时，可能只看到 `-lgnustep-gui`，然后被 `ld.lld` 判定为找不到库。
在 OHOS CI 里，这通常发生在 `Source` 只产出版本化共享对象、或者安装树里的别名
还没有完全稳定的时候。

## 根因

GNUstep Make 的工具链接规则并不保证每次都能看到同一种库名形式。`gnustep-gui`
在 build tree 里可能是版本化文件、symlink，或者无后缀别名，而 `Tools` 还必须在
`Source` 安装完成前完成链接。如果预案只接受单一命名或只接受 regular file，
最终就会回退到 `-lgnustep-gui`，让 lld 自己去猜。

## 推荐方法

在 recipe 里先把 `Source` 产物和安装树别名 stage 到 `GNUSTEP_SYSTEM_LIBRARIES`、
`Source/obj` 与 `Library/Libraries`，必要时直接在 recipe 里重写
`Tools/GNUmakefile.preamble`，再把最终选中的精确共享库路径作为
`GNUSTEP_GUI_TOOL_LIBS=<path>` 传给 `Tools`；路径选择要递归优先考虑已落地的
版本化/非版本化共享库别名，`Tools/GNUmakefile.preamble` 再在缺省情况下按
“已有文件优先”的顺序选择共享库名：

1. `libgnustep-gui.so.*`
2. `libgnustep-gui.*.so`
3. `libgnustep-gui.[0-9]*`
4. `libgnustep-gui.so`
5. `libgnustep-gui`
6. `-lgnustep-gui`

## 与已有知识的差异

- 这不是一般的 `LDFLAGS` 缺失问题。
- 也不是单纯的 `Source` 安装顺序问题。
- 重点是“工具链接时的库名发现”必须和 GNUstep Make 的输出形式对齐。
- 还要防住 `SYSTEM_LIBS` 里残留的裸 `-lgnustep-gui`。

## 禁止做法

- 不要只保留 `-lgnustep-gui` 这一种写法。
- 不要把 `find -type f` 当成唯一候选，它会漏掉 symlink 或别名文件。
- 不要假定 `Library/Libraries` 一定在 Tools 链接前已经完成最终布局。

## 证据来源

- `archives/g/gnustep-gui/0.32.0/conanfile.py`
- `archives/g/gnustep-gui/0.32.0/patches/0002-link-tools-with-in-tree-gui-library.patch`
- `archives/g/gnustep-gui/0.32.0/notes.md`
