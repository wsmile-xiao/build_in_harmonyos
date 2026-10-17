# DRAFT-gnustep-gui-0.31.1-shebang-bash-fix - 修复 gnustep-make 脚本 shebang

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-31
> **Source event**: gnustep-gui 0.31.1 HarmonyOS PC adaptation, PR #7408

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 现象

gnustep-gui 0.31.1 构建过程中，gnustep-make 包内分发的辅助脚本以其原始 shebang
（如 `/bin/sh` 或 `/bin/bash`）执行时，在 OHOS worker 上报 `not found` 或
`Permission denied`，configure/build 中断。

## 根因

OHOS worker 上 `/bin/sh`、`/bin/bash` 不存在或处于 exec 受限状态（hmdfs 限制）。
gnustep-make 是共享的 relocatable Conan 工具包，其脚本 shebang 指向的这些解释器路径
在 OHOS 上不可用。

## 推荐方法

把需要的脚本复制到当前包目录，重写 shebang 为 OHOS 可用的解释器
`/data/service/hnp/bin/bash`，然后调用本地副本：

```sh
cp <gnustep-make>/bin/<script> .
sed -i '1s|.*|#!/data/service/hnp/bin/bash|' <script>
./<script>
```

## 与已有知识的差异

- 不是脚本内容问题，而是 shebang 解释器路径在 OHOS 上不可用。
- 不能硬编码 gnustep-make 的 package_folder（保持工具包可重定位）。

## 禁止做法

- 不要用原始 shebang 直接调用 gnustep-make 包内脚本。
- 不要把 package_folder 绝对路径写进 shebang 或脚本。

## 证据来源

- `archives/g/gnustep-gui/0.31.1/conanfile.py`
- `archives/g/gnustep-gui/0.31.1/manifest.yaml`（knowledge_gained 第 5 条）
