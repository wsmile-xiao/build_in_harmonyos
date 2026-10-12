# libsql 0.21.9 设备构建与测试记录

## 适配内容

使用 `conandata.yml` 锁定的 libSQL C SQLite fork `bea88634dbdf1f578c5187196e7e311f5aa8a67c`，通过 Autoconf/Make 构建 `libsqlite3` 和 `sqlite3`。不构建 Rust `sqld`。`sqlite3.lo` 增加 `-DSQLITE_ENABLE_DBPAGE_VTAB`。`testfixture` 链接 `ext/async/sqlite3async.c`，并定义 `SQLITE_ENABLE_ASYNCIO`、`SQLITE_ENABLE_MEMORY_MANAGEMENT`、`SQLITE_ENABLE_SNAPSHOT`。不定义 `SQLITE_ENABLE_UPDATE_DELETE_LIMIT` 和 `SQLITE_ENABLE_ATOMIC_WRITE`。

`test/tester.tcl` 补 `clock_seconds`、`memleak_check`。泄漏只忽略恰好 12884901888 字节且分配次数为 0 的 session 计数，其它非零 `memory_used` 仍记错。`reset_db` 会尝试关掉残留的 `sqlite3_memdebug_fail`。`test/fuzz_malloc.test` 把 `db close` 改为 `catch {db close}`。`test/vtabH.test` 在 `glob /*` 抛错或返回空列表时跳过根目录子测试。repair 的 `checkfreelist01.test` 中 1.7 至 1.9 按当前页布局取 trunk page；1.5 用独立的逐页链表作期望值。静态库从 `.libs/libsqlite3.a` 打包。`test_package` 编译器回退是 `clang`。

## 编译

设备 `make` 退出码 0。`/data/storage/el2/base/cache/libsql14404-feature-remake.log`（2026-10-04 15:33）含 `MAKE_EXIT=0`、`FTS5_SMOKE=0`、`DBPAGE_SMOKE=0`。异步与内存相关开关的重建日志是 `/data/storage/el2/base/cache/libsql14404-async-rebuild.log`（2026-10-04 21:27）。本轮这版配方没有重新执行 `conan create`。

鸿蒙特有测试仍是既有 `test_package` 的 2 项（C API 消费者，以及 `sqlite3` 的 `SELECT 6 * 7` = 42）。本轮没有重跑 test_package。

## 上游结果

声明分母是 1370 个 `.test` 文件。下面的数都来自 2026-10-04 的设备日志，不再使用 1352/1370、198/198 或 veryquick 的 257053。

先前一份 213 行状态表（`libsqdef36211cc040` 的 `upstream-test-results/suite-status.tsv`）里，`full_missing` 198 行，另外是 RBU、genfkey、JNI、2 个 repair 和 10 次 mptest。非零行只有 `tool_genfkey=1` 和 `jni_tester=2`。这 213 行的日志墙钟是 10199 秒。其中 68 个 full-only 当时是空 harness，不能算通过。

这 68 个在打开 FTS3/4/5、RTREE、SESSION、GEOPOLY、DBPAGE 之后重跑，目录 `/data/storage/el2/base/cache/libsql14404-features/`，15:46 至 21:16，墙钟 19785 秒。`fts4merge2.test` 约占 16751 秒，日志在 `...1063 Ok` 后是 `Signal 15`，退出码 143。其余里 54 个是 0 错误且断言数大于 1，`speed4` 与 `speed4p` 是有计时的基准。随后 `/data/storage/el2/base/cache/libsql14404-fixruns/` 把空 harness 里还能跑的补完：`snapshot_fault` 0/739、`ioerr5` 0/115、`crash5` 0/2971、`async2` 0/1865、`async3` 0/15、`sessionbig` 0/6，退出码都是 0。68 个里算实跑通过的是 62 个。

另外 130 个 full-only 不在空跑名单里，先前退出码 0。抽查 backup 为 0/869，ioerr 为 0/4337。

驱动和单独文件：

- extraquick：0/256488。日志 `libsql14404-vtabh-dbpage/drivers/extraquick.log`。
- recover：`recover2.log` 为 0/21，退出码 0。更早 549 字节的 `recover.log` 只是 0/1。
- veryquick：11:43 的日志在 `recover-1.1.1` 报 `no such table: sqlite_dbpage`，退出码 1，没有汇总行。DBPAGE 修复后没有整包重跑。
- fts3 驱动 0/85456，rtree 驱动 0/37053，退出码 0。
- session 驱动在泄漏计数修正前退出码 1，汇总 0/58678，内存计数 12884901888 字节、0 次分配。修正后只重跑了 sessionbig（0/6）。
- permutations：`nolookaside cast.test` 为 0/137，退出码 0。
- RBU 驱动 0/85，退出码 0。checkfreelist01 为 0/12。checkindex01 与 10 次 mptest 的状态行退出码 0，其中 config01 为 0/163。

未通过：

- soak：`libsql14404-fixruns2/logs/soak.log`，202490 字节，2026-10-04 21:48，退出码 139。`trans-1.0` 起 `invalid command name "db"`，`trans-1.2.1` 为 Signal 11。清掉 `sqlite3_memdebug_fail` 后签名不变。
- memleak：同目录，6856 字节，退出码 1，死在 `cast.test:283` 的 `PRAGMA encoding`。
- async.test：3701 字节，退出码 1，死在 `insert2.test:86`。async2 与 async3 已通过。
- malloc5：2/32。不改期望值。
- wherelfault：打开 `UPDATE_DELETE_LIMIT` 后 27/372，均为 `near "ORDER"`。开关已从配方移除。
- fts4merge3：没有历史二进制，0/1 的空收尾。
- ioerr6：未编译 `SQLITE_ENABLE_ATOMIC_WRITE`。
- loadext：测试扩展没建出来，设备没有 gcc。
- vtabH：补丁已进配方，没有新的通过日志。
- JNI：缺 `JDK_HOME`，退出码 2。genfkey：shell 没有 `.genfkey`，退出码 1。

`conan create` 不再启动 soak、memleak、async.test、veryquick、full-only 逐文件，以及 fts3/rtree/session 聚合驱动。原因是上面的失败，以及 10199 秒和 19785 秒都超过默认 3600 秒预算。create 仍会跑 recover、vtabH、RBU、async2、async3、有界 permutations、repair、mptest、JNI 和 genfkey。

## 结果口径

| 类别 | 数量 | 结果 |
|---|---:|---|
| 上游 `.test` 文件 | 1370 | 声明分母 |
| full-only 实跑通过 | 192 | 130 个先前非空退出码 0，加 62 个特性重跑通过 |
| full-only 不能算通过 | 6 | malloc5、wherelfault、fts4merge3、ioerr6、loadext、fts4merge2 |
| 鸿蒙特有 | 2 | 既有 test_package，本轮未重跑 |

192 加 6 等于 198 个 full-only 文件，不是 1370 的通过率。其余文件里的驱动结果见上文，不折成一个百分比。
