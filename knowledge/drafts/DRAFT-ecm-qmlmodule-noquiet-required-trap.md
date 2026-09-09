# DRAFT-ecm-qmlmodule-noquiet-required-trap: ECM 模块脚本无 QUIET find_package 把缺失可选组件升级为 REQUIRED 的陷阱

> **Contributor**: j669539 | **Status**: Draft（pending editor review）| **Updated**: 2026-09-06
> **Source**: knotifications 6.26.0 HarmonyOS PC 适配（build_in_harmonyos，archives/k/knotifications/6.26.0，分支 feat/knotifications-6.26.0，PR #8662）
> **拟提升编号：由知识库主编确认** —— 本草稿为未提升草稿，尚未分配正式 E 编号

## 问题

KF6 6.26.0 时代的包开始引入 `include(ECMQmlModule)`（knotifications 6.26.0 CMakeLists.txt:27 是链上首例）。
ecm/6.26.0 的 `ECMQmlModule6.cmake` 内部执行**不带 QUIET** 的：

```cmake
find_package(Qt6 COMPONENTS Core Qml CONFIG)
```

ohpcd 制品仓的 qtbase/6.11.1 只含 Core/Gui/Widgets/Network/Test 等基础组件，**没有 Qt6Qml**。
无 QUIET 的 find_package 把 Qt6 整体记为 REQUIRED-not-found，最终在 `ecm_feature_summary()`
处 FATAL 中止配置——报错信息只说 "The following required packages were not found: Qt6 (required version >= 6.x)"，
**不提 Qml，也不提 ECMQmlModule**，极具误导性（看起来像 qtbase 包坏了）。

## 根因

ECM 官方模块脚本（ECMQmlModule6.cmake）面向 Linux 发行版场景编写，假定 Qt6Qml 必然存在，
未对"组件可能缺失"做 QUIET 降级；而交叉编译制品仓的 qtbase 是裁剪包。错误面被
ecm_feature_summary 聚合后丢失了"缺失的是 Qml 组件"的信息。

## 修法（可迁移，已实测）

patch 0001 注释掉 `include(ECMQmlModule)`——**安全性依据**：上游 `src/CMakeLists.txt`
对 qml 子目录本就用 `if (TARGET Qt6::Qml)` 守卫，该 include 仅服务 QML 插件的构建注册，
注释后无 Qml 组件时整条 QML 构建线静默跳过（与上游裁剪语义一致）。

适用面：所有 6.26+ 引入 `include(ECMQmlModule)` 的 KF6 包（链上后续含 QML 的包必踩）；
同族变体：`ECMQmlModule` 之外的 ECM 模块脚本（ECMGenerateQDoc 等若引入对缺失组件的无 QUIET
find_package 同样适用）。

## 证据（PR #8662）

- 原始报错：`The following required packages were not found: Qt6 (required version >= 6.5.0)`（ecm_feature_summary FATAL，日志 ~/tmp/knotifications-create-r2.log）
- 修复：patches/0001-CMakeLists.txt.patch 中 `# include(ECMQmlModule)` 注释块（含安全依据注释）
- 验证：W3 conan create 五轮迭代，第四轮起配置全通过（CI #41315 校验通过，test_package 1/1）
