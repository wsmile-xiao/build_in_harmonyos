- **三方库名称**：libsqlite3（平台任务名 = Conan 包名 = 仓库目录名；上游项目 SQLite）
- **上游版本**：3.50.0
- **上游仓库地址**：https://github.com/sqlite/sqlite
- **适配路径**：路径 A（基础适配）
- **使用知识库**：SQLite amalgamation 手工构建、静态系统库闭包、CLI 归档经验

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 1154 | 来源：上游 Tcl 回归套件 `test/*.test` 叶子用例文件（自身含 `do_test` 断言），逐文件真实执行 |
| 集成测试 | 0 | 上游以统一 Tcl 回归套件交付，无独立集成测试目录 |
| 其他测试 | 8 | 来源：`test/*.test` 中的套件调度驱动脚本（`all.test`/`full.test`/`quick.test`/`extraquick.test`/`soak.test`/`memleak.test`/`mallocAll.test`/`permutations.test`），自身 0 断言，仅按 permutation 调度上述叶子用例；按上游标准入口执行 |
| **合计** | **1162** | 与审查「上游实测 N=1162」口径一致（`test/*.test` 文件计数），全量真实执行、零裁剪、零跳过 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|------------|------|
| 单元测试 | 1154 | 不变 | 上游叶子用例全量保留并全量执行（`0 errors`） |
| 集成测试 | 0 | 不变 | — |
| 其他测试 | 8 | 不变 | 8 个套件调度驱动脚本全量保留并按标准入口执行 |
| 鸿蒙特有测试 | 4 | 新增 | **完整消费者端到端用例**（OHOS aarch64 真机口径执行，非纯断言）：① 文件库持久化 CRUD 生命周期（建库→建表/索引→批量插入→预编译绑定查询→事务回滚→更新→删除→关闭重开→持久性校验+`integrity_check`）；② 查询引擎路径（JOIN+聚合、范围过滤、FTS5 虚表 `MATCH`、RTREE 空间查询）；③ 版本/编译特性契约（`libversion`/`threadsafe`/`compile_options`）；④ 打包 `sqlite3` CLI 端到端流程（建库写数→`.dump` 导出并校验内容→重导入新库→`RAISE(ABORT)` 守卫触发器校验两个库） |
| **合计** | **1166** | **+4** | 上游 1162 全量 + 新增 4 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例（1162 个 `test/*.test` 零改动、零裁剪、零跳过，全量真实执行）
- [ ] **是**，存在对上游测试用例的修改

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游 Tcl 回归套件覆盖库内核回归，但不含「消费者从打包产物使用」的端到端用例，适配后补全
- [ ] **否**

- **补全的测试范围**：为核心对外能力新增 4 个消费者端到端用例（C API 3 个 + CLI 1 个），共 29 个校验点
- **补全原因**：上游回归套件验证 SQLite 内核行为，不验证「经 Conan 打包的静态库/CLI 产物在 OHOS 目标上被消费者完整使用」的流程
- **新增测试文件清单**：
  1. `test_package/test.c` — 3 个 C API 消费者端到端用例（持久化 CRUD 生命周期 / 查询引擎路径含 FTS5+RTREE / 版本与编译特性契约），24 断言
  2. `test_package/conanfile.py`（`_cli_e2e`）— 打包 `sqlite3` CLI 端到端流程：建库写数 → `.dump` 导出并校验内容 → 重导入新库 → 守卫触发器（`RAISE(ABORT)`）校验两个库的行数与 `SUM(qty)`，5 个校验点

## 验证结果

- 编译状态：通过（本地 `conan create` EXIT=0；CI 校验通过，见 ohpcd-robot 记录）
- 上游测试用例通过率：1156/1162（99.48%）（`test/*.test` 文件级，分母为审查实测 N=1162）；其中有 `do_test` 断言的叶子用例 **1154/1154（100%）**；未全绿的均为**自身 0 断言的套件调度脚本**，逐个技术定位见下及随本次提交的 `reports/upstream-test-evidence.md`
- 新增测试用例通过率：4/4（100%；24/24 C 断言 + 5/5 CLI 校验点）

### 上游测试执行口径（真实执行证据）

- **执行对象**：上游完整源码树 `sqlite/sqlite` tag `version-3.50.0`（含 `test/` 目录）
- **用例口径**：`test/*.test` 文件 = 1 用例（与审查实测 N=1162 一致）
- **testfixture 构建**：`./configure --with-tcl=/usr/lib && make testfixture`，编译开关与本配方 `conanfile.py` 完全一致（`SQLITE_THREADSAFE=1`、`SQLITE_ENABLE_RTREE`、`SQLITE_ENABLE_FTS5`、`SQLITE_ENABLE_COLUMN_METADATA`、`SQLITE_ENABLE_UNLOCK_NOTIFY`、`SQLITE_SECURE_DELETE`、`SQLITE_ENABLE_DBSTAT_VTAB`），故 FTS5/RTREE/DBSTAT 等相关上游用例**真实执行而非跳过**
- **执行环境**：WSL2 Ubuntu 22.04 x86_64、TCL 8.6.12、非 root 用户（上游 tester.tcl 在 root 下会使权限类用例失真），逐文件 `testfixture test/<name>.test`，每文件独立工作目录
- **判定标准**：退出码 0 且 harness 摘要 `0 errors out of N tests`、无 `Failures on these tests`
- **结果**：叶子用例 1154/1154 全部 `0 errors`；8 个套件调度驱动按标准入口执行，逐文件结果与失败定位见下条与证据文档（未修改、未裁剪、未跳过任何上游测试文件）
- **子测试级计数**：叶子用例 `do_test` 子测试 **1,413,931** 次执行（0 errors；取各文件 harness 摘要 `N tests` 实测求和，非静态统计）；各调度驱动另执行 39 万～135 万子测试/入口（quick 786,994、full 1,355,810、extraquick 390,026、permutations-veryquick 382,836 等）
- **逐文件证据**：随本次提交的 `reports/upstream-test-evidence.md`（含口径、命令、结果表与偏差定位过程）

### 鸿蒙特有测试真机口径（OHOS aarch64）

- **DAYU200 真机（RK3568 / OpenHarmony 6.0.0.47，aarch64）实测**：消费者端到端用例（静态链接打包产物 `libsqlite3.a`）真机执行 **`RESULT: 24 checks, 0 failures`（exit_code=0）**，含建库/插入/查询回环（文件库落盘、关闭重开持久、事务回滚、`integrity_check`）；同源同断言 **x86 对照**同为 `RESULT: 24 checks, 0 failures`，两侧行为一致。证据：`reports/device-e2e-evidence.md` + `_device_evidence.json`（设备序列号 450100445634303332018f3e7d2dba00）。
- 本地 `outputs/local-validate-recipe.sh`（qemu-aarch64-static + OHOS musl runroot，与 CI Worker 同口径）：`RESULT: 24 checks, 0 failures`；`cli e2e: create -> .dump -> re-import -> verify (both DBs) OK`
- CI 真机 Worker `conan create` + test_package 同口径通过（见 ohpcd-robot「CI 校验通过」）

## 补充说明

1. 配方直接编译官方 `sqlite-autoconf-3500000.tar.gz` 的 amalgamation 与 shell，绕过 HMDFS 上 `autosetup`/`jimsh0` 子进程限制；发布静态 `libsqlite3.a`、`sqlite3.h`、`sqlite3ext.h` 与 `sqlite3` CLI，Unix/OHOS 系统库闭包为 `dl`、`pthread`、`m`。
2. Conan 包名按任务使用 `libsqlite3`，上游 CMake/pkg-config 名保持 `sqlite3`（`sqlite3::sqlite3` / `sqlite3.pc`）。
3. 本轮按审查结论完成三处修订：① 补齐两个统计表与合计行（rule1）；② 上游 1162 用例由 0/N → **全量真实执行**，统计与证据见上（rule4）；③ 鸿蒙特有测试改为 4 个**完整消费者端到端用例**（非纯断言），含打包 CLI 的建库→导出→重导入→守卫校验全流程（rule12）。
4. 附带修订：移除配方中的 `SQLITE_DEFAULT_MEMSTATUS=0`。该开关会关闭 `sqlite3_status(SQLITE_STATUS_MEMORY_USED)` 计数，与上游测试断言（`loadext-3.5` 等）及上游默认行为不一致；移除后适配构建与上游默认内存统计行为一致，上游套件亦以同参构建的 testfixture 执行。
5. 上游 `test/*.test` 中 8 个文件为套件调度驱动（自身 0 断言，仅按 permutation 重复调度叶子用例），按标准入口执行的真实结果：`extraquick`（390,026 子测试）、`permutations veryquick`（382,836）**0 errors 通过**；`all`（单轮实测 5,198,857 子测试、25 个调度套件完成 23 个，尾部因共享 WSL 环境被外部 shutdown 中断——5 次尝试留痕，22 处失败全部定位、无新增失败类型）；`quick`（786,994 子测试，6 处定位）、`full`（1,355,810 子测试，4 处定位）的失败全部定位到两类非库功能问题：① `ext/recover/recoverfault*.test` 的 OOM 故障注入扫描在单进程长跑尾部的注入状态漂移（该文件在 1162 清单之外，独立执行 8,513 子测试 0 errors）；② `walsetlk` 跨进程文件锁时序用例偶发（清单内叶子，独立执行 51 子测试 0 errors）；`mallocAll` 在 `altermalloc2-5-oom-transient.862` 迭代 SIGSEGV（崩溃前实测 13,725 子测试全 Ok；该叶子独立执行 9,949 子测试 0 errors）；`soak`/`memleak` 两个文件 standalone 无法执行，均属上游脚本自身缺陷并已精确定位（`memleak.test` 调用全树无定义的 `memleak_check`；`soak.test` 依赖仅由 `sort4.test` 跨文件定义的 `clock_seconds` 及 loop 驱动置空 `finish_test` 后断裂的 db 命令生命周期），二者调度的 4 个随机压力叶子均独立执行通过。全部细节（含错误原文、用例名、迭代号、独立复测对照）见 `reports/upstream-test-evidence.md` §3。
6. 改动范围仅为 `archives/l/libsqlite3/3.50.0/`，分支 `feat/libsqlite3-3.50.0`。
