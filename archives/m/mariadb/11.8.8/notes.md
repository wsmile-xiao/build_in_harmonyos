# mariadb 11.8.8 - HarmonyOS(OHOS)适配笔记

> 分支：`feat/mariadb-11.8.8`；一库一 issue / 一分支 / 一 PR。

## 适配状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| W0 依赖检查 | 完成 | `ncurses/6.6` 来自仓库 Conan 依赖；wolfSSL、zlib、PCRE2、fmt、readline 使用 bundled 源 |
| 源码/构建系统分析 | 完成 | CMake `minbuild` 可产出 `mariadbd`、Connector/C 与 mysql-test 驱动 |
| Conan 配方与 test_package | 完成 | 默认构建服务端测试产物，安装包聚焦客户端开发产物 |
| 本机静态验证 | 完成 | Python 语法检查、补丁干净应用检查、diff 检查 |
| OHOS 真机 mysql-test | 完成 | 完整 `main` plus `binlog`/`client` 可运行边界；串行执行 |
| CI | 待重跑 | 推送后回复 `/rebuild` 并跟踪 |

## 关键适配点

- 官方源码包使用 `archive.mariadb.org` 地址与 SHA-256 校验；CI 下载走已校验同哈希的华为云镜像。
- 默认 `WITHOUT_SERVER=OFF` 构建 `minbuild` 服务端和 mysql-test；`without_server=True` 保留给仅需要客户端的消费者。
- `package()` 显式打包 Connector/C 公共头文件、`libmariadbclient.a` 以及直接依赖的 `libwolfssl.a`、`libzlib.a`，不把服务端测试树混入安装包。
- OHOS HMDFS 不能创建 MariaDB 默认的文件型 Unix socket；`MTR_TCP_ONLY=1` 时测试框架改用 `127.0.0.1` TCP，并显式传 `--protocol=tcp`。
- OHOS 上 `posix_fallocate()` 可能返回 `EACCES`（error 13）；InnoDB 对所有非 `EINTR` 拒绝静默回退到可移植写入路径，解决 `ib_logfile0` 未初始化问题。
- `symbolic-links=0` 避免测试数据目录触发 HMDFS 符号链接限制；这不是修改上游测试用例。
- `test_package` 链接真实客户端库并调用公共 API，不用它替代 mysql-test 统计。

## 上游测试口径

- 官方 `mysql-test/**/*.test` 基线：6650 个文件；2026-09-07 解包官方 tarball（SHA-256 与 conandata.yml 一致）复验，命令 `find mysql-test -name '*.test' | wc -l`，无需 git clone。
- 本次实际执行边界：完整 `main`、`binlog`、`client`，对应 1533 个 `.test` 文件，覆盖率 23.05%。
- MTR 独立用例：1517 个；combination 展开：1656 个。
- 最终合并结果：1124 pass、70 fail、317 skipped、6 disabled。
- 严格上游通过率：`1124/6650 = 16.90%`；已执行且非 skip/disabled 用例中通过率为 `1124/1194 = 94.14%`。
- skip/disabled 不计为通过；任何一个 combination 失败，该独立用例按失败计。
- 5117 个未执行文件按套件精确二分（2026-09-07）：**阻塞 2913**（rpl/multi_source 多服务器复制拓扑 737、galera*/wsrep 集群 685、perfschema*/sysschema 因 `PLUGIN_PERFSCHEMA=NO` 556、mariabackup 因 `WITH_MARIABACKUP=False` 100、s3 因 `PLUGIN_S3=NO` 22、encryption/binlog_encryption 动态插件不在 minbuild 产物 138、engines/storage_engine 外部引擎矩阵 548、plugins/federated/archive 动态插件 86、stress 长时压力 8、optimizer_unfixed_bugs 上游已知缺陷 22、mtr/mtr2 框架自检 8、include 3）+ **可运行未执行 2204**（sys_vars 755、innodb 族 592、parts 142、funcs_1/2 127、jp 111、compat 90、maria 66、vcol/roles/gcol/versioning/sql_sequence/atomic 252、小引擎套件 69）——可运行部分无平台/构建阻塞，超出 2026-09-05 单真机串行预算，不虚报为通过。
- 70 个失败逐类根因挂钩构建配置：wolfSSL 兼容层（TLS 30）、认证插件未构建（14）、HMDFS 符号链接/权限（6）、上游 mdev-33070 SIGSEGV 等（4）、SQL 结果差异（5）、binlog/client 断言（11）。
- 详细命令、6650 文件映射、失败域归因和真机日志路径见 `reports/mysql-test-ohos-full-run.md`。

## CI 固化子集

- 配方在每次默认完整服务端构建后串行执行 56 个真机已验证通过的 `main` 用例。
- 移除了旧列表中全量运行显示为 skipped 的 `count_distinct3` 与 `create_delayed`，改用已通过的 `insert` 与 `select`，避免把 skip 记作通过。
- 2026-09-05 使用新的空 vardir 复验：`Completed: All 56 tests were successful.`，MTR exit code 0。
- 2026-09-05：修正官方源码缩进匹配并重新编译 `os0file.cc`、`libinnobase.a` 与 `mariadbd` 后，CI #40518 的 5 个失败用例 5/5 通过，56 例 CI 子集再次 56/56 通过。
- 该子集是持续回归门禁，不替代 1124/6650 的上游统计口径。

## 验证记录

- 2026-09-05：完整 `main` 与 `binlog`/`client` 边界真机运行，全部 `--parallel=1`；完整日志在 `/storage/Users/currentUser/tmp/mariadb-mtr-tcp/`。
- 2026-09-05：56 例 CI 子集 fresh 复验 56/56 通过；运行前后可用内存分别约 13.7 GB 与 13.9 GB，无残留 MTR/mariadbd 进程。
- 2026-09-05：客户端静态库打包产物在真机单文件编译并运行 `test_mariadb.c`，API smoke 1/1 通过。
- CI #40518 曾因新源码未应用缩进匹配错误的 InnoDB 补丁而失败；修复后的新 CI 待触发和跟踪。

## 阻塞点

- 无本机阻塞点。剩余上游边界、70 个失败域和未执行 5117 个文件的分类均已记录，不虚报为通过。
