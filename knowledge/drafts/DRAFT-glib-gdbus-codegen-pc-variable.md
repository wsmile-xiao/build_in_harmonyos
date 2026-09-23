# DRAFT-glib-gdbus-codegen-pc-variable — 知识图谱草稿（随 glib 2.88.3.1 归档同 PR）

> 对应条目：`knowledge/drafts/DRAFT-glib-gdbus-codegen-pc-variable.kv`（同 stem 配对，字段相互对应）
> 来源：glib/2.88.3 依赖修复任务（libdex gdbus=enabled 前置缺陷修复；r01 候选，r03 配对补件）

## 主题（对应 .kv title）

OHOS/Conan 下 `gdbus_codegen` pc 变量缺失与 `gdbus-codegen` 工具不可用的可复用解法。

## 错误面（对应 .kv error_signature）

| 触发工具 | 阶段 | 错误签名 |
|---|---|---|
| meson / conan / pkg-config / python3 | configuration / installation / runtime | `Could not get pkg-config variable.*gdbus_codegen`、`gio-2.0.*no.*gdbus_codegen`、`gdbus-codegen.*No such file or directory`、`bad symlink.*gdbus-codegen` |

识别关键词（match_keywords）：`gdbus_codegen`、`gio-2.0.pc`、`gdbus-codegen`、`pkg_config_custom_content`、`PkgConfigDeps`、`get_variable`、`hnp/bin`、`broken symlink`、`python script`、`bin/gdbus-codegen`。

## 根因（对应 .kv root_cause）

GLib 的 `gio-2.0.pc` 上游经 meson `pkg.generate` 声明 `gdbus_codegen=${bindir}/gdbus-codegen` 变量，但 Conan `PkgConfigDeps` 基于 `package_info()` 重新生成 pc 文件时不继承该变量，导致 meson 消费方 `dependency('gio-2.0').get_variable('gdbus_codegen')` 失败（首错：`Could not get pkg-config variable and no default provided for gio-2.0`）。同时 OHOS `hnp/bin/gdbus-codegen` 若为坏符号链接或未随包安装 python 脚本，工具调用返回 `No such file or directory`。

## 方案（对应 .kv rec_approach）

1. 配方 `package_info()` 对 gio 组件调用 `set_property('pkg_config_custom_content', {'gdbus_codegen': '${bindir}/gdbus-codegen'})`，使 Conan 生成的 `gio-2.0.pc` 重新声明该变量；
2. 确保 `gdbus-codegen` 随包安装到 `bin/` 且为可执行 python 脚本（`#!/usr/bin/env python3`），坏符号链接需 `rm -f` 后以真实文件重建；
3. 消费方验证：`pkg-config --variable=gdbus_codegen gio-2.0` 与最小 XML 代码生成实测（`gdbus-codegen --generate-c-code demo test.xml`）。

## 验证（对应 .kv verification_cmd）

```bash
PKG_CONFIG_PATH=<pkg>/lib/pkgconfig pkg-config --variable=gdbus_codegen gio-2.0
LD_LIBRARY_PATH=<pkg>/lib python3 <pkg>/bin/gdbus-codegen --generate-c-code demo test.xml
```

- cwd：`/storage/Users/currentUser/.oh-runner/tmp/glib-2.88.3/gdbus-probe`
- 退出码：0（pkg-config 查询与代码生成均 rc=0）
- 日志：`/storage/Users/currentUser/.oh-runner/tmp/glib-2.88.3/logs/r02-gdbus-capability.log`（SHA-256 `16a65227604585e32a508c9533ee092bc46ba64aacd9856cd2a9c1448233524f`）

## 适用条件与反例（对应 .kv forbid_1_pattern / 边界）

- 适用：任何通过 Conan `PkgConfigDeps` 消费 `gio-2.0.pc` 变量并依赖 `gdbus-codegen` 工具做代码生成的 OHOS 构建（libdex gdbus=enabled 等）；`gdbus_codegen` 变量缺失或工具坏符号链接的 GLib 系消费栈。
- 反例/禁止：在 `conandata.yml` 中用 `file://` 本地缓存路径替代官方下载 URL（命中 PR 污染硬门禁 `local_file_url`，提交前必须恢复官方 HTTPS URL）；把 `gdbus_codegen` 变量指向不存在或不可执行的路径；伪造 `--version` 输出。

## 恢复条件

- pc 变量缺失：按上述方案注入 `pkg_config_custom_content` 后重新 `conan create`，消费方以新包重建。
- 工具不可用：确认包内 `bin/gdbus-codegen` 为可执行 python 脚本且目标环境 `python3` 可用；坏符号链接 `rm -f` 后以真实文件交付。

## 七轴查重结果（对应 .kv relations / novelty）

| 轴 | 结果 | 说明 |
|---|---|---|
| exact_duplicate | false | 无既有条目描述 gdbus_codegen pc 变量缺失或 pkg_config_custom_content 注入 |
| causal_duplicate | false | E046（chmod 不生效→测试期 skip）触发面相同但对象不同（recipe 打包期别名物化） |
| trigger_overlap | partial | E046 trigger_tool/phase 为 runtime testing；本条目为 conan pkg-config 生成期与 recipe package() 期 |
| solution_overlap | partial | E050 copy-replace-symlink 同族（regular 别名物化），但解决对象不同 |
| combination_novelty | true | 变量缺失 + 工具打包 + HMDFS chmod 降级组合无既有覆盖 |
| boundary_novelty | true | 适用边界（Conan PkgConfigDeps .pc + meson get_variable 消费方 / HMDFS package() 别名物化）未被描述 |
| test_migration_novelty | false | 无上游测试迁移成分 |

关系（relations）：`similar_to` = [E046（HMDFS chmod 不生效，本任务同轮在 recipe 别名物化阶段以降级校验处理）]；`caused_by` = []；`prerequisite_of` = [libdex 依赖修复后续轮次的 gdbus=enabled 实例化]；`conflicts_with` = []。

## 溯源

- 源事件：`archives/g/glib/2.88.3`（r01）→ `archives/g/glib/2.88.3.1`（r02 增量交付，随 PR #9454）
- 知识候选台账：`archives/g/glib/2.88.3.1/reports/`（knowledge candidate ledger，r01 登记）
- last_updated：2026-09-10
