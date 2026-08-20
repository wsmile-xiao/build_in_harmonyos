# 【知识库扩展】fix(appconfig): 修复归档目录与 Conan settings

## 问题现象

已合并但尚未发布的 AppConfig 1.71 配方在发布流水线被 L0m/L0p 拦截：归档包目录使用了大写 `AppConfig`，且主配方和 `test_package` 都只声明了 `os`、`arch` 两项 settings。首次同版本修复又在 Buildbot `checkout-pr` 阶段因纯大小写目录 rename 触发 `already exists in working directory`，尚未进入配方门禁，因此改用 Conan 修复号 `appconfig/1.71.1`。

## 根因

原提交前门禁没有机械检查 Conan slug，也没有解析两个配方的完整 OHOS profile settings，导致不合规内容在合并后才被发布流水线发现。Windows 大小写不敏感工作树还会把 `AppConfig` 与 `appconfig` 映射到同一物理目录；纯大小写 rename 的直接 patch 应用因此把目标判断为已存在。

## 修复范围

- 将路径和 Conan 修复版本改为 `archives/a/appconfig/1.71.1`。
- 贡献页任务、live Git 和 replacement PR 源分支全部精确使用 `fix/appconfig-1.71.1`，不追加额外后缀。
- 主配方与测试配方统一声明 `os`、`compiler`、`build_type`、`arch`。
- 修复号把目标改为 `appconfig/1.71.1`，同时改变目录大小写与版本段，从而避免旧路径别名；所有文件（含空 `.gitkeep`）完整迁移，并在当前 main 上精确重放候选 diff。
- 不修改 AppConfig 上游源码、补丁、依赖、打包语义或测试语义。

## 知识库查重与扩展

已检索 `knowledge/graph`、`knowledge/drafts`、`knowledge/doc`、`knowledge/operations`。E193 只覆盖 HMDFS 上的大小写敏感测试语义，不覆盖 Git 纯大小写 rename 在大小写不敏感 CI checkout 中的 patch 重放问题，因此新增配对草稿 `knowledge/drafts/E331-draft-2301.kv` 与 `.md`。

## 可复用说明

该经验适用于任何需要把既有归档目录改为小写 Conan slug、而 CI 通过 patch 重建 PR 的库。验证合同要求 direct apply 失败后零部分修改、three-way apply RC 0、重放 tree 与候选 tree 完全一致，并明确不把该结果替代 W3/W4/CI/Review 或发布证据。

## 发布边界

本 Issue 仅跟踪修复 PR。`/release` 只能在该修复 PR 合并后触发；release 成功后再以新鲜隔离 Conan home 回读 `appconfig/1.71.1` 的制品仓 recipe/binary 身份。
