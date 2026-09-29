# libftp 1.5.0 R05 知识查重判定（executor_local_required）

- task_id: libftp-1.5.0-r05-client-integration-suite-execution-pc1-19-20260927T125645Z
- 快照: /storage/Users/currentUser/.ohpc-knowledge-snap/libftp-1.5.0-r01-bootstrap-and-adapt-pc1-19-20260922T160045Z（main @ 48d9cee6，外置只读稀疏）
- 扫描范围: knowledge/graph/E*.kv(540) + knowledge/doc/E*.md(540) + knowledge/drafts/*.kv(成对) + 根 DRAFT-* 配对
- 快照审计: remote=https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git, ref=main, HEAD=48d9cee6844d0fca1f25e86c2df1293b904855d8, sparse=/knowledge/；与 R01–R04 同快照可核验复用

## R05 候选
1. **集成套件真实执行**：`test/client.cpp` 58 宏（参数化展开 123 用例）真实运行，
   `[==========] 123 tests from 7 test suites ran`，122 PASSED / 1 SKIPPED / 0 FAILED；
   SKIP = `ssl_client.login`（client.cpp:1191 上游显式 GTEST_SKIP：pyftpdlib REIN 限制）。
2. **运行前置修复**：鸿蒙内核不支持 `close_range` syscall（Signal 31 SIGSYS 终止子进程），
   需 `-DBOOST_PROCESS_V2_POSIX_FORCE_DISABLE_CLOSE_RANGE` 重编 close_handles.cpp（回退 `/dev/fd` dirent 遍历）。
3. **依赖补齐**：制品仓 boost 无 `libboost_process`/`libboost_filesystem` 已编译库 → 从缓存官方源码树
   自编本地静态库（仅本地测试链接）；pyOpenSSL 由 OHOS 原生 wheel（ohos_aarch64）补齐。

## 判定（逐候选）

- 候选 1：**等价命中 E292**（layered-ctest-migration：按 target inventory 区分可执行子集并真实运行，
  缺依赖记录为依赖闭环缺口而非整套阻塞）。R05 在 R02/R04 已运行 140 用例基础上，依
  `integration_suite_build_authorized` 用自建 CMake 目标闭合最后 58 宏入口，正是该方案的进一步应用；
  集成测试服务器启动/证书/端口前置属具体库运行准备，方法论已被 E292 覆盖 → 路径 A，不创建新草稿。
- 候选 2：**等价命中 DRAFT-ohos-syscall-capability-matrix-fork-probe**（error_signature 含
  `Signal 31|SIGSYS|exit 159|Bad system call`；root_cause=OHOS 内核未实现 syscall 以 SIGSYS 终止；
  rec_approach=fork-per-probe-capability-matrix）。close_range 正是"Linux 专有 syscall 在 OHOS 以
  SIGSYS 终止"的实例，本任务以编译宏禁用 close_range、回退 dirent 实现为修复，属该草稿方案的应用
  → 路径 A 等价命中，不创建新草稿。
- 候选 3：依赖补齐属具体库适配事实（boost 组件导出缺口已在 R04 记录恢复条件），方法论已被
  E292（依赖闭环缺口）+ E342（离线/制品仓替代 FetchContent 网络依赖）覆盖 → 路径 A。
- R05 无可沉淀的跨库新增通用知识：全部候选均为既有条目/草稿的实例应用 → knowledge_decision: reuse_existing（路径 A）。
- R01 路径 B 草稿对 DRAFT-libftp-1.5.0-openssl-flat-cmakedeps-target-rename.{kv,md} 继续有效并随本 PR。

## 草稿成对审计（R01 草稿对，本轮复核）
- kv SHA-256: 346ef5ad3d6baaeb0841799ce33abf9d48e7e770086cbe9742f2a0340032f7a
- md SHA-256: 325402f36879c450a5203f59e477ab0ec77417dc067fc08e577a8db8da9ec06e
- 同 stem 配对存在；kv 12 字段齐全；白名单 knowledge/drafts/DRAFT-libftp-1.5.0-*.md|.kv 匹配。
- R05 无新增草稿（knowledge_decision: reuse_existing，路径 A）。
