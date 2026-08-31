# DRAFT：Qt6 子模块上游测试子集（QT_BUILD_TESTS_BY_DEFAULT=OFF + 显式目标 + ctest -R）

> Source: qtscxml/6.11.1 HarmonyOS PC 适配（权威 CI PASS）
> Category: qt6-module-adapt | Status: Draft | E3XX 编号待知识系统分配

## 场景

Qt6 模块默认构建全部上游测试。qtscxml 的测试里，QML / ecmascript-datamodel 相关
测试依赖 qtdeclarative（不引入 qtdeclarative 的配置下无法构建）；且 OHOS 构建
产物未必能直接运行（can_run 守卫）。

## 问题

早期离线配置（不引入 qtdeclarative）下：盲目 `QT_BUILD_TESTS=OFF` 会丢掉可运行的
6 个核心测试；盲目全开会因 QML feature 缺失而构建失败。需要一个显式"测试子集"模式；
最终配方引入 qtdeclarative 后子集清单扩为上游 tests/auto 全量 17 个目标。

## 方案

- configure 缓存变量 `QT_BUILD_TESTS=ON`、`QT_BUILD_TESTS_BY_DEFAULT=OFF`；
- `build()` 内对选定目标显式 `cmake.build(target=t)`（本配方最终 = 全量 17 个；
  早期离线 = tst_qstatemachine / tst_qstate /
  tst_scxmlcoutput_{default,namespace,path,arguments}）；
- `can_run()` 守卫后以 `ctest -R '^(...)$'` 只跑这些目标，`QT_QPA_PLATFORM=offscreen`；
- `cmake_find_mode=none` 依赖不在 loader 路径 → `LD_LIBRARY_PATH` 追加 qtbase lib
  与本构建树 lib；
- host codegen 工具 qscxmlc 安装到 libexec、不产生 bin/ → L2（运行产物）门禁
  自动跳过。

## 验证

早期离线验证 6 个上游测试 6/6 PASS → 2026-08-30 权威 FULL CI 引入 qtdeclarative 后
17/17 全量 PASS（见 notes.md 验证结果）；早期离线阶段 QML 依赖测试不构建（预期）；
L2 正常跳过；test_package PASS。

## 可复用边界

- 适用于所有 Qt6 子模块 OHOS 适配的 L1 测试子集；
- 子集目标清单需与实际 feature 配置对齐，避免引用缺失 feature 的测试；
- 运行环境需 offscreen QPA + LD_LIBRARY_PATH 补齐 cmake_find_mode=none 依赖。

## 与现有知识的关系

- 与 E2149（curl 缺失镜像兜底）不同主题，无重叠。
