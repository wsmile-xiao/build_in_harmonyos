# DRAFT-gnustep-gui-0.31.1-make-cli-flags - GNUstep make 不读环境变量，必须命令行传参

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-31
> **Source event**: gnustep-gui 0.31.1 HarmonyOS PC adaptation, PR #7408

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 现象

在 gnustep-gui 0.31.1 的 conan 构建中，通过环境变量 `export ADDITIONAL_CPPFLAGS=...`
传给 GNUstep make 的编译旗标被静默忽略。具体表现为 clang 命令里
`-DGNUSTEP_BASE_HAVE_LIBXML=` 为空值（期望 `=0`），导致依赖 libxml 的宏/头文件缺失，
编译报错。

## 根因

GNUstep make 的构建规则不会从进程环境读取 `ADDITIONAL_CPPFLAGS`（及其他构建旗标）。
只有把旗标作为 `make` 命令行参数传入，规则才会把它注入到每条编译命令中。
`export` 设置的环境变量对 GNUstep make 无效。

## 推荐方法

在配方 build 阶段把旗标直接拼到 make 命令上：

```sh
make ADDITIONAL_CPPFLAGS="-I<include> -DGNUSTEP_BASE_HAVE_LIBXML=0 ..."
```

确保所有编译单元都能拿到所需的 `-D`/`-I` 旗标。

## 与已有知识的差异

- 不是编译器或头文件缺失问题，而是 GNUstep make 的变量传递机制差异。
- 与 objc-runtime-gnu 草稿同属 GNUstep 构建环境类问题，但机制不同。

## 禁止做法

- 不要仅用 `export` 设置 `ADDITIONAL_CPPFLAGS` 就期望生效。
- 不要把绝对路径硬编码进旗标（会破坏可复现性）。

## 证据来源

- `archives/g/gnustep-gui/0.31.1/conanfile.py`
- `archives/g/gnustep-gui/0.31.1/manifest.yaml`（knowledge_gained 第 3 条）
- `archives/g/gnustep-gui/0.31.1/reports/conan-create.log`
