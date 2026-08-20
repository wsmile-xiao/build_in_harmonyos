【申请人账号】2301_80739235
【队伍名称】天天开心
【申请日期】2026/08/09
【库名称】libpng
【版本】1.6.58.2

## 申请原因

本任务是根 Issue #1093 `dosbox-staging/0.82.2-r1` 的真实前置依赖。正式 `libpng/1.6.58.1` 制品在删除 `libpng16-config` 与 `libpng16.la` 实体后留下两个悬空别名链接，使 DOSBox 的完整依赖闭包不可用。`1.6.58.2` 保持官方稳定源码 v1.6.58 不变，仅修复配方的包内容完整性并绑定已发布的 `zlib/1.3.2`。

## 知识库查重情况

已检索 `knowledge/graph`、`knowledge/graph/draft`、`knowledge/doc` 与 `knowledge/operations`。HMDFS 下 Autoconf 私有 `umask 077` 已由 E129 覆盖；未发现等价条目说明 Python `Path.is_file()` 对悬空符号链接返回 false、从而漏删包内残留别名的错误模式。

## 可复用说明

新增草稿 `E2152-draft-2301`：清理包内已弃用文件时，同时检查 `is_file()` 与 `is_symlink()`，再用负向测试重建悬空链接并要求 test_package 拒绝残留。该模式适用于 Conan/Python 配方中所有可能删除真实目标后继续清理别名链接的包内容规范化逻辑。

## 关联关系与验证

- 根任务：#1093 `dosbox-staging/0.82.2-r1`
- 依赖任务：contrib task 3319
- 上游稳定版本：v1.6.58（v1.7.0beta89 为预发布版，不作为稳定基线）
- 真机：上游 36/36、消费者 1/1、消费者断言 4/4、命令 smoke 2/2 全部通过
- 边界：无源码补丁；未引入任何名称含 `OHOS` 的源码/patches 条件编译宏
