# libftp 1.5.0 R02 知识查重判定（executor_local_required）

- task_id: libftp-1.5.0-r02-upstream-test-execution-and-evidence-closure-pc1-19-20260926T121523Z
- 快照: /storage/Users/currentUser/.ohpc-knowledge-snap/libftp-1.5.0-r01-bootstrap-and-adapt-pc1-19-20260922T160045Z（main @ 48d9cee6，外置只读稀疏）
- 扫描范围: knowledge/graph/E*.kv(540) + knowledge/doc/E*.md(540) + knowledge/drafts/*.kv + DRAFT-* 配对

## R02 候选
1. 上游测试必须逐入口判定可运行性，可运行子集必须真实执行，不得整套泛化"不可运行"；
2. 制品仓 googletest/1.17.0 替代上游 FetchContent googletest 构建可运行单元入口。

## 判定
- 候选 1：**等价命中 E292**（layered-ctest-migration：先按 CTest target inventory 区分
  可执行/需额外环境/不可执行子集，可执行子集真实运行，缺依赖记录为依赖闭环缺口而非整套阻塞）
  ——本任务 9 个可运行单元入口真实执行（107/107 PASSED）+ client.cpp 单列不可运行（boost/process 缺失）
  正是该方案的逐字段应用 → knowledge_decision: reuse_existing，路径 A，不创建新草稿。
- 候选 2：**E342**（Separate test-only bootstrap downloads from an offline package build /
  disable-networked-upstream-tests-and-run-consumer-test）+ DRAFT-cmake-test-framework-fetch-to-conan-find-package
  + DRAFT-cpu-features-0.11.0-configure-time-googletest-download 已覆盖
  "FetchContent 测试框架构建期网络在离线/制品仓环境的替代路径" → 等价/已覆盖，路径 A。
- R01 路径 B 草稿 DRAFT-libftp-1.5.0-openssl-flat-cmakedeps-target-rename.{kv,md} 保持有效
  （openssl flat 包 cmake_target_name 重映射），本轮无新增路径 B 草稿。

## 草稿成对审计（R01 草稿对，本轮复核）
- kv SHA-256: 346ef5ad3d6baaeb0841799ce33abf9d48e7e770086cbe9742f2a0340032f7a
- md SHA-256: 325402f36879c450a5203f59e477ab0ec77417dc067fc08e577a8db8da9ec06e
- 同 stem 配对存在；kv 12 字段齐全；白名单 knowledge/drafts/DRAFT-libftp-1.5.0-*.md|.kv 匹配。