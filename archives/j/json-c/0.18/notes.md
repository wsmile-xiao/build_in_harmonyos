# json-c 0.18 适配笔记

## 构建系统
- json-c 0.18 使用 CMake (非 autotools)
- CMake 最低版本要求: 3.9
- 项目是纯 C 库，无外部依赖

## 编译过程
1. `cmake .. -DCMAKE_INSTALL_PREFIX=$PREFIX -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DBUILD_SHARED_LIBS=ON`
2. `make -j2` — 全部目标编译成功
3. `make install DESTDIR=$TEST_PREFIX` — 安装成功

## 测试
- ctest 全部失败，原因是 HarmonyOS 动态链接器不支持相对 RPATH (`../libjson-c.so`)
- 直接设置 `LD_LIBRARY_PATH` 运行测试可正常通过
- 这是平台 RPATH 限制，非代码问题

## 产物
- libjson-c.so (共享库)
- libjson-c.a (静态库)
- 头文件: json-c/json.h, json_object.h, json_tokener.h 等
- pkg-config: json-c.pc
- CMake config: json-c-config.cmake

## Conan 配方
- 使用 CMake 构建 (conan.tools.cmake)
- 默认 shared=True (json-c 非系统同名库，可动态链接)
- 无外部依赖
---

## 知识候选台账与查重（2026-09-16 第一轮）

### 候选 1: HarmonyOS ctest 运行需 LD_LIBRARY_PATH（相对 RPATH 不支持）
- 真实错误: ctest 直接运行全部失败，动态链接器不支持相对 RPATH (`../libjson-c.so`)
- 根因: OHOS musl loader 不支持相对 RPATH，属平台限制非代码缺陷
- 修复/验证: `LD_LIBRARY_PATH=<build_dir> ctest` → 25/25 PASS（本轮实测日志 ctest-run.log）
- 适用范围: 所有 CMake 构建的共享库在上游 ctest 直跑失败时
- 四范围查重: 正式知识 E019/E120/E298 已覆盖（set-ld-library-path / env-library-path / virtual-run-env-explicit-run）；0.16/0.17 历史 notes.md 已记录同样结论
- 结论: 复用既有知识，无新增差异

### 候选 2: W3/finish junk_check full 模式命中 main 上其他库基线垃圾
- 真实错误: `检查模式: full`，JC1/JC5 拦截 `archives/c/cloog/0.21.1/.build-closed`、`.staging-verified`（隔离前 SHA-256 均为 e3b0c442...，已确认在 origin/main 历史提交中，不在本次 PR diff 内）
- 根因: junk_check 模式链 pr.diff > incremental > full；零提交/无 pr.diff 时回退 full 整仓扫描，命中其他库历史带入的跟踪杂项文件
- 修复/验证: `JUNK_PR_DIFF=<worktree>/pr.diff` 强制单包口径 → `检查模式: prdiff (4 个文件)`，JC_RESULT=pass，W3 通过（w3-local-ci.log 实测）
- 适用范围: 共享 build_in_harmonyos 仓库内所有新库分支的本地 finish/W3
- 四范围查重: DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental 已记录同根因（commit-first 方案）；本轮 JUNK_PR_DIFF=pr.diff 属同根因的 pr.diff 分支执行变体，无独立新增差异
- 结论: trigger_overlap=true / causal_duplicate=partial / solution_overlap=partial / 无 combination_novelty，复用既有草稿知识

### 候选 3: 直接 `conan create .` 缺 profile 报 settings.os.version 未定义
- 真实错误: 裸 `conan create . --build=missing` 报 `Invalid: 'settings.os.version' value not defined`
- 根因: 执行端未按 CI 口径传 `-pr:h=ohos-aarch64 -pr:b=ohos-aarch64`（default profile 无 os.version）
- 修复/验证: 带 ohos-aarch64 profile 重跑 → conan create 成功，test_package 2/2 PASS
- 结论: 执行端调用方式问题，非 json-c 适配知识，属噪声不入账

### 路径判断
- 七轴: exact_duplicate=true(候选1)/causal_duplicate=partial(候选2)/trigger_overlap=true(候选2)/solution_overlap=partial(候选2)/combination_novelty=false/boundary_novelty=false/test_migration_novelty=false
- similar_to: E019, E120, E298, DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental
- caused_by: []; prerequisite_of: []; conflicts_with: []
- **决定: reuse_existing / path_a_no_knowledge** — 无新增可跨库复用知识，不建 .md/.kv 草稿


**编译结束**: 2026-09-16 00:26
**最终状态**: built
