# DRAFT-gnustep-gui-0.31.1-hmdfs-copyfile-symlink - hmdfs 上 .so 别名与 mkdir 的规避

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-31
> **Source event**: gnustep-gui 0.31.1 HarmonyOS PC adaptation, PR #7408

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 现象

在 OHOS 上通过 Conan 打包 GNUstep GUI 时，两个 hmdfs 相关的限制同时出现：

1. `ln -s` 创建符号链接报 `Permission denied`——conan 子进程在 hmdfs 上无法创建
   符号链接，`libgnustep-gui.so.0.31.1` 的 `libgnustep-gui.so` 别名无法用链接生成。
2. GNUstep make 的 `mkinstalldirs` 脚本在 hmdfs 上被限制执行（exec denied），
   install/packaging 阶段目录创建失败。

## 根因

hmdfs 对符号链接与脚本执行施加了平台限制：Conan 子进程创建 symlink 被拒，
`mkinstalldirs` 这类 shell 脚本无法执行。GNUstep 打包逻辑默认依赖这两者。

## 推荐方法

在配方中：

- 用 `copyfile`（shutil.copy）把版本化 `.so` 复制为无版本别名，
  规避 `ln -s` 的 hmdfs 权限限制；
- 用 `MKDIRS='mkdir -p'` 覆写 GNUstep 的 `mkinstalldirs` 变量，
  让目录创建走 `mkdir -p` 而非受限脚本。

## 与已有知识的差异

- 不是单纯的权限问题，而是 hmdfs 对 symlink 与脚本 exec 的双重限制。
- 区别于普通 Linux 打包：Linux 上 `ln -s` 与 mkinstalldirs 均可用。

## 禁止做法

- 不要用 `ln -s` 生成 .so 别名（hmdfs 会拒绝）。
- 不要依赖 `mkinstalldirs` 脚本在 hmdfs 上执行。
- 不要把 hmdfs 特判扩散到 Linux 分支；Linux 上保持原生 symlink。

## 证据来源

- `archives/g/gnustep-gui/0.31.1/conanfile.py`（`_link_gui_library` 用 copyfile）
- `archives/g/gnustep-gui/0.31.1/manifest.yaml`（knowledge_gained 第 2、4 条）
