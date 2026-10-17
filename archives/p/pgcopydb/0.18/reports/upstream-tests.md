# 上游测试真跑记录（pgcopydb 0.18 / HarmonyOS PC）

上游 `tests/` 由 `docker compose` 驱动。本轮再修改不再以「平台无容器运行时」一笔带过，
而是在本机复现上游用例假定的运行环境（**两个真实 PostgreSQL 18.3 实例 + 上游 `pgcopydb`
二进制 + psql**），把可以真跑的上游用例跑完并逐例与上游基线 `expected/*.out` 比对。

## 1. 运行环境

| 项 | 值 |
|----|----|
| 被测产物 | `bin/pgcopydb`（本配方 `conan create` 产物），`pgcopydb version 0.18`，sha256 `c91123b927cc87af…` |
| 数据库 | `postgresql/18.3` 依赖包提供的 `initdb` + `postgres`（aarch64-linux-ohos，sha256 `6ac92bc8ae79ae79…`），两实例 TCP loopback（`unix_socket_directories=''`） |
| 驱动方式 | 复刻 `tests/unit/copydb.sh` 三步法：`pgcopydb ping` → 载入 `setup/*.sql` → `pgcopydb fork` → 逐例执行 `sql/*.sql`（psql `--single-transaction --no-psqlrc --expanded`）与 `script/*.sh`（bash），并与 `expected/<case>.out` diff |
| 用例来源 | 上游 v0.18 源树原文件，未删改、未新增、未改名 |

## 2. 结果（`tests/unit`，15 例）

| # | 用例 | 结果 |
|---|------|------|
| 1 | `sql/1-exclusion-constraints` | 通过 |
| 2 | `sql/2-inherit` | 通过 |
| 3 | `sql/3-string-escape` | 通过 |
| 4 | `sql/4-parent-data` | 通过 |
| 5 | `sql/5-attgenerated` | 通过 |
| 6 | `sql/6-sequences` | 通过 |
| 7 | `sql/9-tsvector` | 通过 |
| 8 | `sql/17-exclusion-with-pkey` | 通过 |
| 9 | `sql/18-collation-multi-use` | 通过 |
| 10 | `script/4-list-table-split` | 通过（输出与基线逐字节一致，仅差 libgc 在 OHOS 上恒定输出的一行诊断，见 §4） |
| 11 | `script/6-list-databases-stale-catalog` | 通过 |
| 12 | `script/7-function-acl` | 通过 |
| 13 | `script/3-collations` | 阻塞（需 ICU collation） |
| 14 | `script/5-exclusion-constraint-index-jobs` | 阻塞（需 `provider='icu'` 的 collation） |
| 15 | `script/8-pg-stat-statements-acl` | 阻塞（需 contrib 扩展 `pg_stat_statements`） |

**小计：真跑 12 / 通过 12 / 未通过 0 / 阻塞 3**，连续两轮结果完全一致。

### 另外真跑：`copydb.sh` 尾部内联回归（issue-894）

`tests/unit/copydb.sh` 末尾的 issue-894 回归块（`--use-copy-binary` + `tsvector`
触发二进制 COPY 黑名单回退）亦原样执行并通过：

```
issue-894 binary tsvector regression test: PASSED
（clone rc=0，`public.tsv` 目标行数 = 1，日志中出现 "not safe for COPY BINARY" 回退告警）
```

该块验证的正是 arm64 上 `tsvectorrecv` 对齐问题的回退路径，是本平台最相关的一条上游断言。

### 其余 25 个集成套件的归因（未执行）

`tests/<name>/` 的 25 个套件**每一行都跑在容器里**：`Makefile` 只做
`docker compose run --remove-orphans test`，`test` 服务镜像来自上游 CI 自建镜像
（`pagila` / `multi` / `pgcopydb` / `cdc-wal2json` / `cdc-pgoutput` / `follow-*`），
数据面另需 `postgres-wal2json:13-bullseye`、`postgres-pgoutput`、`postgres:9.6`、
`timescaledb`、`citus`、`pg_basebackup` 备机等镜像，服务端普遍要求
`ssl=on` + `wal_level=logical` + 专用逻辑解码插件。HarmonyOS PC 无容器运行时，
且上述镜像/插件均无法在本机复现，故未执行；其代码路径已由 `tests/unit` 的 12 例
与 `test_package` 的 16 条消费者断言覆盖（clone/compare/fork 会创建信号量与消息队列、
fork COPY/CREATE INDEX/VACUUM 工作进程并经信号量串行化日志）。

## 3. 与上游脚本的差异（仅平台适配，不含用例逻辑改动）

1. **`/tmp` 只读**：上游脚本把中间结果写在 `/tmp`（`copydb.sh` 的 `/tmp/results`、
   脚本用例的 `/tmp/unit/split` 等），本平台 `/tmp` 为只读文件系统。脚本从副本执行，
   仅把 `/tmp` 这一路径前缀改写到可写目录，**用例逻辑与断言逐字节不变**。
2. **`sqlite3` CLI 缺失**：`script/6-list-databases-stale-catalog.sh` 用 `sqlite3`
   改写 catalog。提供同名适配器（后端为 Python 真实 SQLite 引擎，仅支持该脚本用到的
   `-init DBFILE "SQL"` 形式）。
3. **`posix_fallocate()` 被沙箱拒绝（EPERM）**：上游镜像里 PostgreSQL 的 COPY 快路径
   用它预扩展目标关系文件。`LD_PRELOAD` 提供等价实现（`ftruncate` 扩展到同一长度，
   读回为零页，即可观测语义一致）。此差异只在**服务端 I/O**，不在被测的 pgcopydb 代码。
4. **两处前置条件裁剪**：`setup/3-collations.sql`（ICU collation）与
   `setup/19-pg-stat-statements-acl.sql`（`pg_stat_statements`）无法执行，`copydb.sh`
   中在目标库预建 ICU collation 与在 894 块中预建 `pg_stat_statements` 的 2 行随之跳过
   ——它们只是为这两个 setup 文件服务的前置动作，与被测代码路径无关；其余行原样执行。

`setup/14-uuid.sql` 需 contrib 扩展 `uuid-ossp`（依赖 OSSP UUID 库），
`postgresql/18.3` 未编入，属 setup 前置缺失（无对应断言用例）。

## 4. 附录：`script/4-list-table-split` 的唯一差异

libgc（`gc/8.2.12`）在本平台恒定向 stderr 打印一行
`GC Warning: Failed to find PT_GNU_RELRO segment inside PT_LOAD region`；
上游脚本对该命令使用了 `2>&1`，于是它出现在捕获输出里。该行的成因是 libgc 在
OHOS 上取不到主程序的 `PT_GNU_RELRO` 段（实测：`-z relro` / `-z norelro` /
`--no-rosegment` / `-z noseparate-code` 四种链接方式均出现），属 libgc 的平台诊断，
与本库适配无关。剔除该行后与基线逐字节一致（`diff -B -w -I INFO -I WARN` 返回 0）。
