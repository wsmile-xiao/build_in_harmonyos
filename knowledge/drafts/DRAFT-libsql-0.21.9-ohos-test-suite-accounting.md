# HarmonyOS 上 SQLite/libSQL 测试文件需要按套件选择拆分统计

- **草稿 ID**：`DRAFT-libsql-0.21.9-ohos-test-suite-accounting`
- **来源**：libsql 0.21.9，C SQLite fork commit `bea88634dbdf1f578c5187196e7e311f5aa8a67c`，PR #13406
- **范围**：Conan 设备构建、SQLite Tcl 测试套件、HarmonyOS 应用沙箱
- **状态**：候选草稿。本 PR 走路径 A，标题是【依赖项】。main 尖端知识库 0 命中尚未重新取证，不作为路径 B 提交。

## 问题

libSQL 锁定的 C fork 用 Tcl `permutations.test` 选择文件集。只看 `veryquick.test` 的退出码会漏掉 full 集里的崩溃、模糊、故障注入、I/O 和大文件用例，也会把特性未编译时的空 harness 算进去。原始 `.test` 文件里还有套件驱动、RBU、repair、JNI、mptest 和工具用例。

HarmonyOS 上还有三类要分开记的阻塞：应用沙箱读不了 `/`、设备没有 JDK、锁定 fork 的 shell 没有 `.genfkey`。另外，`soak.test`、`memleak.test` 和 `async.test` 会在 `tester.tcl` 已经执行 `reset_db` 之后仍报 `invalid command name "db"`。把这些写成通过，或者写成一句「未执行」，都无法复核。

## 可复用做法

1. 用当前这次构建的 `testfixture` 和锁定源码的 `permutations.test` 生成 `full`、`veryquick`、`rbu` 列表。
2. `full` 减 `veryquick` 的每个文件单独保存日志和退出码。日志只有 harness 的 `0 errors out of 1`、且最大分配约 210 字节时，记为空跑，等对应的 `SQLITE_ENABLE_*` 打开后再跑。
3. 套件驱动单独记断言数和退出码，不把驱动断言数加进 `.test` 文件通过数。
4. `permutations.test` 要带套件名和文件名模式。`memleak.test` 的文件参数是路径本身。无参数的 permutations 会遍历 quick 集。
5. 不可执行项保留源文件、命令、报错和根因。`conan create` 默认 3600 秒放不下的长跑，用设备日志作为记录，并在配方里写明为什么 create 不再启动它。

## libsql 0.21.9 这次设备记录

声明分母 1370。设备状态表里 full-only 是 198 行。其中 68 个第一次是空 harness。打开 FTS/RTREE/SESSION/GEOPOLY/DBPAGE 并补上异步、内存和 snapshot 开关后，62 个有实跑且退出码 0，6 个不能算通过（malloc5 2/32，wherelfault 的 ORDER BY 语法，fts4merge3 无历史二进制，ioerr6 无 ATOMIC_WRITE，loadext 无测试扩展，fts4merge2 退出码 143）。另外 130 个不在空跑名单里，先前退出码 0；抽查 backup 为 0/869，ioerr 为 0/4337。

驱动：extraquick 为 0/256488；recover 在 DBPAGE 补上之后为 0/21；veryquick 旧日志在 `recover-1.1.1` 报 `no such table: sqlite_dbpage`，退出码 1，修复后没有整包重跑；fts3 驱动 0/85456，rtree 驱动 0/37053；session 驱动在泄漏计数修正前退出码 1（0/58678，12884901888 字节且 0 次分配），修正后只重跑了 sessionbig（0/6）；permutations 以 `nolookaside cast.test` 得到 0/137。

失败与阻塞：

- soak：有界运行退出码 139。`trans-1.0` 起 `invalid command name "db"`，`trans-1.2.1` 为 Signal 11。日志 `libsql14404-fixruns2/logs/soak.log`，202490 字节。`clock_seconds` 已存在。在 `reset_db` 里执行 `sqlite3_memdebug_fail -1` 没有改变这个签名。
- memleak：退出码 1，死在 `cast.test:283` 的 `PRAGMA encoding`。
- async.test：退出码 1，死在 `insert2.test:86`。async2 为 0/1865，async3 为 0/15。
- JNI：`make -f GNUmakefile tester-local` 在编译前要求 `JDK_HOME`，退出码 2，两个测试文件没有编译。
- genfkey：`genfkey-1.2` 报 shell 没有 `.genfkey`，退出码 1。
- vtabH：沙箱编辑已写入配方，这次没有新的通过日志。

特性仍关闭时那 213 行状态的墙钟是 10199 秒。68 个文件的特性重跑墙钟是 19785 秒，其中 fts4merge2 约 16751 秒。两者都超过 CI 默认 3600 秒，所以 create 不再重复这些长跑。

鸿蒙特有测试 2 项来自既有 test_package，这次没有重新 `conan create`。

## 边界

文件数和 Tcl 断言数是两个分母。veryquick 或 extraquick 的断言数不能代替 1370。空 harness 的退出码 0 不能记成通过。正式计数以该 PR 的 `notes.md`、`PR_BODY.md` 和 `test_package/MANIFEST.yml` 为准。
