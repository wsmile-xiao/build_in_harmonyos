# lldb 17.0.0 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-09-09}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}
---

**编译结束**: 2026-09-09 13:54
**最终状态**: built

## 知识候选台账与查重（task lldb-17.0.0-r01-pc1-63）

### 候选清单（非噪声项）

| ID | 真实错误/现象 | 根因 | 修复 | 验证 | 适用范围 | 查重结论 |
|---|---|---|---|---|---|---|
| K1 | configure 无法识别 HarmonyOS 平台 | config.guess 缺 HarmonyOS 分支 | config.guess 加 aarch64*:HarmonyOS → aarch64-unknown-linux-ohos | 补丁后 configure 通过 | 所有 autotools 项目 | **exact_duplicate**: E007 已覆盖，复用已有知识 |
| K2 | LLDB_ENABLE_POSIX=OFF → TCP_NODELAY 未声明；NativeProcessLinux 未链入；lldb-server 未构建 | LLVM 17 monorepo 多 CMake 平台分支仅含 Linux/Android，HarmonyOS 全部落空 | 各 CMakeLists 平台分支扩展 Linux/Android/HarmonyOS；LLDBGenerateConfig POSIX 分支加 HarmonyOS | 全量构建通过、lldb-server 构建成功、bin/lldb 运行 | LLVM 系 CMake 项目 + LLDB | **boundary_novelty**: E092/E267/E532/DRAFT-libguarded 部分覆盖，LLDB 多文件 POSIX 分支+LLDB_ENABLE_POSIX 为新增差异 → **new_draft** E532 |
| K3 | LLDBConfig.cmake: Expected directory for clang-resource headers not found | LLDB 依赖 Clang 库与 resource headers，monorepo 需 LLVM_ENABLE_PROJECTS=clang;lldb | 配方 generate() 设 LLVM_ENABLE_PROJECTS=clang;lldb | conan create 全流程通过 | 所有 monorepo 内依赖 clang 的 LLVM 项目(lldb) | **combination_novelty**: 未命中既有条目 → **new_draft** E533 |
| K4 | 上游测试大量 ptrace/AF_UNIX/mkfifo/link EPERM 失败 | 宿主机沙箱禁止 ptrace/域套接字 bind/mkfifo/硬链接 | 探针实证 + 如实归因（非源码缺陷） | 独立 C 探针复现 | OHOS 沙箱调试类库 | **trigger_overlap**: E222 部分相关，测试运行层归因 |
| K5 | W3 本地 conan create 强制重建超时 | 脚本 --build=lldb/* 强制干净重建，3369 目标远超 bash 300s | 配方可构建性以 conan create --build=missing 缓存命中验证；build_timeouts 配 5400s | conan create 缓存命中 RC=0 | 大型 LLVM 系包 | **trigger_overlap**: E540 影子 CI 部分覆盖 |

### 七轴查重（路径 B 候选 K2/K3）

- K2: exact_duplicate=false, causal_duplicate=false, trigger_overlap=true(E092/E267/E532), solution_overlap=true(部分), combination_novelty=true(LLDB 多文件 POSIX+ENABLE_POSIX 组合), boundary_novelty=true(HarmonyOS 边界), test_migration_novelty=false
- K3: exact_duplicate=false, causal_duplicate=false, trigger_overlap=false, solution_overlap=false, combination_novelty=true(clang;lldb 组合), boundary_novelty=true(monorepo 构建边界), test_migration_novelty=false

### 路径决定

- K1 → reuse_existing（E007）
- K2 → new_draft（E532-draft，.md/.kv 配对已建）
- K3 → new_draft（E533-draft，.md/.kv 配对已建）
- 任务类型为【高难度挑战】（路径 C），知识草稿随同一 PR 进入，不另立知识库 PR

## W3 本地 CI 模拟执行通道限制（submit 前置门禁）

- 现象: finish W3 步骤调用 ci/conan/build_and_test.sh，其 conan create 用 --build=lldb/* 强制从源码干净重建 LLDB 3369 个编译目标，单次完整编译约 40-60 分钟。
- 首错: 每次运行均被执行端 bash 工具 300s 单次调用上限以 SIGTERM(信号15) 截断，conan create 返回 124（timeout）；日志完整保留于 .ci_logs/conan_build_lldb_17.0.0.log 与 reports/w3-local-ci.log（每次从 [1/3369] 重新开始，因脚本强制重建且每次新建 conan build 目录）。
- 退出码: 124（conan create 未在通道上限内完成）；命令: ci/conan/build_and_test.sh archives/l/lldb/17.0.0
- 配方可构建性等价验证（通过）: `conan create archives/l/lldb/17.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing`（不带强制重建参数）命中已注册缓存二进制，test_package 实际运行 `lldb --version` 与消费者 SB API 自检，RC=0；另手动在 conan build 目录完成全量 ninja（bin/lldb、bin/lldb-server、lib/liblldb.so 生成，RC=0）。
- 恢复条件: 远端 CI 环境（无 300s 通道上限）按 build_timeouts.txt（lldb/17.0.0 5400s，已配置）完成 conan create 强制重建即通过 W3；本地如需复验可将 OHC_W3_TIMEOUT 提高并由更长执行通道运行 build_and_test.sh。
