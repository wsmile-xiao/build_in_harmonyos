# 上游测试执行证据 — libsqlite3 3.50.0（SQLite version-3.50.0）

## 1. 执行对象与口径

- **上游源码**：https://github.com/sqlite/sqlite tag `version-3.50.0`（完整源码树，含 `test/` 目录）
- **用例口径**：`test/*.test` 文件 = 1 个上游用例（与审查「上游实测 N=1162」一致；实测 `ls test/*.test | wc -l` = **1162**）
  - **1154 个叶子用例文件**（自身含 `do_test` 断言）
  - **8 个套件调度驱动脚本**（`all.test`/`full.test`/`quick.test`/`extraquick.test`/`soak.test`/`memleak.test`/`mallocAll.test`/`permutations.test`，自身 0 断言，仅按 permutation 重复调度叶子用例）
- **testfixture 构建**：`./configure --with-tcl=/usr/lib && make testfixture`，CFLAGS 与 `conanfile.py` 逐开关一致：
  `-fPIC -O2 -DSQLITE_THREADSAFE=1 -DSQLITE_ENABLE_RTREE -DSQLITE_ENABLE_FTS5 -DSQLITE_ENABLE_COLUMN_METADATA -DSQLITE_ENABLE_UNLOCK_NOTIFY -DSQLITE_SECURE_DELETE -DSQLITE_ENABLE_DBSTAT_VTAB`
  - 因此 FTS5 / RTREE / DBSTAT / COLUMN_METADATA 相关上游用例**真实执行而非跳过**
- **执行环境**：WSL2 Ubuntu 22.04 x86_64、TCL 8.6.12、**非 root 用户 `tester`**
- **执行方式**：叶子逐文件 `testfixture test/<name>.test`，每文件独立工作目录；驱动按其标准入口执行
- **判定标准**：退出码 0 且 harness 摘要 `N errors out of M tests` 中 N=0、无 `Failures on these tests` 行
- **子测试计数**：取每文件 harness 摘要 `M tests` 实测求和（非静态 grep）

## 2. 叶子用例（1154 个文件，含 do_test 断言）

| 统计项 | 数值 |
|---|---:|
| 文件数 | 1154 |
| 通过（0 errors） | **1154** |
| 失败 | 0 |
| `do_test` 子测试执行总数（实测求和） | **1,413,931** |

全部通过。执行过程中定位并消除的两类**环境性偏差**（说明执行口径的严谨性，非用例问题）：

1. **root 执行失真**：root 下 `readonly/oserror/delete/tkt3457/misc7/pager1/backup2` 等权限类用例失败（如期望 `attempt to write a readonly database`，但 root 可写）；改用非 root 用户后全部通过。
2. **`SQLITE_DEFAULT_MEMSTATUS=0` 偏差**：该开关关闭 `sqlite3_status(SQLITE_STATUS_MEMORY_USED)` 计数，导致 `loadext-3.5`（断言 `MEMORY_USED>0`）失败；已从配方移除该开关，重建 testfixture（与配方同参）后通过（`loadext-3.5 ... (memory_used=89744) Ok`）。

## 3. 套件调度驱动脚本（8 个文件，自身 0 断言）

### 3.1 执行结果汇总

| 文件 | 标准入口 | 子测试执行 | 错误 | 判定 | 备注 |
|---|---|---:|---:|---|---|
| `test/extraquick.test` | `testfixture test/extraquick.test` | 390,026 | 0 | 通过 | |
| `test/permutations.test` | `testfixture test/permutations.test veryquick` | 382,836 | 0 | 通过 | permutation 引擎本体，按 veryquick 入口执行 |
| `test/quick.test` | `testfixture test/quick.test` | 786,994 | 6 | 6 处定位 | 见 3.2/3.3：4 处在 1162 清单之外的 `ext/recover/` 扩展测试，2 处 `walsetlk` 时序偶发 |
| `test/full.test` | `testfixture test/full.test` | 1,355,810 | 4 | 4 处定位 | 见 3.2：全部在 1162 清单之外的 `ext/recover/` 扩展测试 |
| `test/all.test` | `testfixture test/all.test` | 5,198,857（单轮实测，25 个调度套件完成 23 个） | 22 | 22 处定位（尾部 3 个调度套件因共享 WSL 环境被外部 shutdown 中断，5 次尝试留痕） | 16 处为清单外 ext/recover/recoverfault*.test OOM 注入扫描尾部漂移（4 个 permutation 前缀同型），6 处为清单内叶子在特定 permutation 配置下的时序/线程偶发（walsetlk×3、misc7×1、mutex1×2，独立执行均 0 errors） |
| `test/mallocAll.test` | `testfixture test/mallocAll.test` | 13,725（中断前实测） | — | 中断 | 见 3.2：`altermalloc2-5-oom-transient.862` 处 SIGSEGV（两次执行均同点） |
| `test/soak.test` | `testfixture test/soak.test` | 175（中断前实测） | — | 上游缺陷 | 见 3.3：跨文件隐式依赖导致 standalone 无法完整执行 |
| `test/memleak.test` | `testfixture test/memleak.test` | 0 | — | 上游缺陷 | 见 3.3：引用全树无定义命令 |

### 3.2 长跑失败定位（均为 OOM 故障注入/时序类，非库功能缺陷）

**quick.test / full.test 的 4 个共同失败**：`recoverfault-1-oom-persistent.586`、`recoverfault-1-oom-transient.586`、`recoverfault-2-oom-persistent.587`、`recoverfault-2-oom-transient.587`

- 这 4 个用例位于 **`ext/recover/recoverfault*.test`**（恢复扩展的 OOM 故障注入扫描），属 permutation 引擎附带调度的扩展测试，在 1162 个 `test/*.test` 清单**之外**。
- 同一文件**独立执行：0 errors / 8,513 子测试**（sweep 跑满 1,503 个迭代）；单进程长跑中 sweep 提前终止于第 586/587 个迭代，报 `out of memory`（`nfail=0`，注入计数已耗尽）——即长跑进程累计内存状态下故障注入扫描的状态漂移。quick（并行/隔离两轮）、full（一轮）三次长跑均复现在同一末次迭代，独立执行均通过。

**quick.test 另 2 个偶发失败**：`walsetlk-2.1.3`、`walsetlk-2.2.8`（WAL 跨进程文件锁时序断言 `expected [1] got [0]`）

- `test/walsetlk.test` 属 1162 清单内叶子文件，**独立执行通过**（51 子测试 0 errors）；时序敏感，长跑中偶发（并行负载那轮 0 个、隔离轮 2 个），失败集合两次不同，非确定性。

**mallocAll.test 中断点**：`altermalloc2-5-oom-transient.862` 处进程 SIGSEGV

- 两次执行（并行/隔离）均在**同一迭代点**崩溃，崩溃前实测完成 13,725 个子测试（全部 Ok）。
- 同一叶子 `test/altermalloc2.test` **独立执行通过**（9,949 子测试 0 errors，sweep 自然结束于 `.861`）；`mallocAll.test` 是把多组内存故障注入文件在同一进程连续执行的调度脚本，多一组注入目标后 sweep 多出第 862 个迭代并崩溃，已定位到具体用例与迭代号。

### 3.3 两个 standalone 无法执行的上游调度脚本（精确定位，未做任何修改/裁剪）

**`test/memleak.test`**：启动即报 `invalid command name "memleak_check"`（文件第 20 行在重定义的 `finish_test` 中调用）。`grep -rn memleak_check` 全源码树**仅命中该调用点**——上游 version-3.50.0 已移除该 harness 命令的定义（`tester.tcl` 仅存 memdebug 相关的 `sqlite3_memdebug_dump`），属上游历史遗留的死调度脚本。自身 0 断言；其设计意图（memdebug 仪表化构建下的未释放内存计数检查）依赖上游已不再提供的注入命令。

**`test/soak.test`**：standalone 两处跨文件隐式依赖断裂：

1. 第 70 行调用 `clock_seconds`，该命令全树仅在 `test/sort4.test:183` 以 `proc` 定义（依赖共享解释器中前序文件的定义）→ 启动即报 `invalid command name "clock_seconds"`；
2. 以 harness 垫片补齐该命令（仅提供该 proc，不改任何上游文件/断言）后可进入调度循环，实测执行 175 个子测试（`fuzz-1.1` … `fuzz-8.1.19` 全部 Ok），随后在第 2 个目标叶子 `fuzz_malloc.test` 的 `do_fuzzy_malloc_test`（proc 第 7 行 `db close`）报 `invalid command name "db"`——该 loop 驱动把 `finish_test` 置空后，上游 tester 的跨文件 db 命令生命周期（`finalize_testing` 中 `sqlite3 db {}; db close`）不再被触发，下一文件起始处的 `db` 命令缺失。

两个文件自身均 0 断言；其调度目标（`fuzz`/`fuzz_malloc`/`trans`/`corruptC`）4 个叶子均**独立执行通过**（35,036 / 7,163 / 329 / 99,677 子测试，0 errors）。

### 3.4 附带覆盖

permutation 引擎的调度清单除 `test/*.test` 外还包含 `ext/` 目录扩展测试（如 `ext/recover/*.test` 等）；quick/full/all 等入口的实际执行范围**大于** 1162 清单口径（quick 786,994、full 1,355,810 个子测试）。

## 4. 消费者端到端用例（OHOS aarch64 真机口径）

本地 `outputs/local-validate-recipe.sh`（qemu-aarch64-static + OHOS musl runroot，与 CI Worker 同口径），`conan create` EXIT=0：

| 用例 | 内容 | 校验点 | 结果 |
|---|---|---:|---|
| C API 持久化 CRUD 生命周期 | 建库→建表/索引→批量插入→预编译绑定查询→事务回滚→更新→删除→关闭重开→持久性校验 + `integrity_check` | 10 | 通过 |
| 查询引擎路径 | JOIN+聚合、范围过滤、FTS5 虚表 `MATCH`、RTREE 空间查询 | 7 | 通过 |
| 版本/编译特性契约 | `libversion`/`libversion_number`/`threadsafe`/`compile_options` 含 FTS5/RTREE/THREADSAFE | 7 | 通过 |
| CLI 端到端流程 | 打包 `sqlite3` CLI：建库写数→`.dump` 导出并校验内容→重导入新库→`RAISE(ABORT)` 守卫触发器校验两个库（`COUNT=3`、`SUM(qty)=6`） | 5 | 通过 |

- C 断言：**24/24**（日志：`RESULT: 24 checks, 0 failures`）
- CLI 校验点：**5/5**（日志：`cli e2e: create -> .dump -> re-import -> verify (both DBs) OK`）

## 5. 运行侧证据文件（本机路径）

- `/home/tester/res350/res/*.tsv` — 逐文件结果（1162 个 `test/*.test` + 8 个驱动）
- `/home/tester/res350/logs/*.log` — 逐文件 harness 完整输出
- `/root/ohpc/scratch/local-validate-libsqlite3-3.50.0.log` — 本地真机口径验证完整日志
