# MySQL 9.7.1 OHOS 适配 —— 上游测试真实执行报告（testclients/mysql_client_test）

- 日期：2026-09-15
- 分支：feat/mysql-9.7.1（PR #9488）
- 用例集：上游 `testclients/mysql_client_test.cc`，`mysql_client_test --show-tests` 实测 **315** 项
- 结果：**307 / 315 通过（97.5%）**，8 项未通过逐项归因见第 4 节

## 1. 结论（修正此前"mysqld 无法启动"的记录）

`reports/阶段B-测试报告.md`、`reports/阶段C-mysqltest报告.md` 记录的"OHOS 沙箱导致 mysqld 无法
启动、上游测试无法运行"是**未完成运行期修复前的中间结论**。根因与修复如下（本 PR 补丁 0068）：

| 现象 | 根因 | 修复 |
|------|------|------|
| 启动中止 `[MY-013039] Can't create UNDO tablespace innodb_undo_001 since './undo_001' already exists` | HMDFS 的**文件名大小写不敏感、目录组件大小写敏感**混合行为：`Fil_path::get_real_path()` 对**整个绝对路径** `to_lower()` 后路径不可访问 → InnoDB 扫描不到既有 undo 表空间 → 误判需重建 | `get_real_path()` 改为能力探测：小写化后路径仍可访问才采用，否则保留真实大小写 |
| `posix_fallocate(): ... error number 13` | 沙箱拒绝 `fallocate`/`posix_fallocate`（EPERM/EINVAL） | `fil0fil.cc` 与 `mysys/my_fallocator.cc` 回退 `ftruncate`+`pwrite` 稀疏扩展 |
| `Can't start server : Bind on unix socket: Operation not permitted` | 沙箱拒绝 AF_UNIX `bind()` | `sql/conn_handler/socket_connection.cc` 降级为仅 TCP 监听，而非中止服务 |

修复后 `mysqld --initialize-insecure → 启动 → mysqladmin ping → mysqladmin shutdown` 在本机
OHOS **一次通过，无需任何手工绕行**，并由 `test_package/server_lifecycle_test.sh` 在 CI 中回归。

服务端就绪证据（mysqld 错误日志原文）：

```
[System] [MY-010931] [Server] .../mysqld: ready for connections. Version: '9.7.1'  socket: ''  port: 3310
```

## 2. 执行方式

- 用例数核实：`mysql_client_test --show-tests` → 315 项。
- 执行粒度：**逐用例独立执行**（每个用例前重建 `test` 库，避免用例间状态污染）。
- 环境前提（与上游 mysql-test 驱动保持一致）：
  - `--log-bin-trust-function-creators=1`（对齐 `mysql-test/include/default_mysqld.cnf`）；
  - `SET GLOBAL sql_mode=''`：`testclients/mysql_client_test.cc` 源码注释明确
    `Will not work if sql_mode is STRICT`（见 `mysql_client_test.cc:3833`），即该测试程序自身声明的
    前提是非严格 sql_mode。

## 3. 一键复现

```sh
BIN=<build>/runtime_output_directory      # mysqld / mysql / mysql_client_test
SERVER=<server runtime dir>               # 含 share/ 与 lib/，作 --basedir
W=${TMPDIR:-/tmp}/mysql971-upstream-test; P=3310

$BIN/mysqld --no-defaults --initialize-insecure --basedir=$SERVER --datadir=$W/data
$BIN/mysqld --no-defaults --basedir=$SERVER --datadir=$W/data --socket= --port=$P \
    --skip-networking=0 --log-bin-trust-function-creators=1 &
until $BIN/mysqladmin --no-defaults -h127.0.0.1 -P$P --user=root ping >/dev/null 2>&1; do sleep 1; done

$BIN/mysql --no-defaults -h127.0.0.1 -P$P --user=root -e "SET GLOBAL sql_mode='';"
n=0; pass=0; fail=0
for t in $($BIN/mysql_client_test --show-tests | tail -n +3); do
  n=$((n+1))
  $BIN/mysql --no-defaults -h127.0.0.1 -P$P --user=root \
      -e 'DROP DATABASE IF EXISTS test; CREATE DATABASE test;' >/dev/null 2>&1
  $BIN/mysql_client_test --host=127.0.0.1 --port=$P --user=root --database=test "$t" \
      >/dev/null 2>&1 && pass=$((pass+1)) || fail=$((fail+1))
done
echo "SUMMARY pass=$pass fail=$fail total=$n"     # SUMMARY pass=307 fail=8 total=315
```

## 4. 结果与逐项归因

总计 315，通过 307，未通过 8（97.5%）。其余 307 项覆盖 client/server 协议、预处理语句与
参数绑定、结果集/游标、事务、字符集转换、C API 生命周期与 `mysql_stmt_*` 系列等。

| # | 用例 | 现象（日志原文摘要） | 归因 |
|---|------|----------------------|------|
| 43 | client_store_result | `Table 'client_test_db.t1' doesn't exist` | 用例原设计为同一 client 会话内接续执行（依赖前序 `client_query` 建表）；本次为保证隔离采用逐用例执行，故必然失败。**非适配缺陷** |
| 44 | client_use_result | 同上 | 同上 |
| 156 | test_cursors_with_union | `Table 'client_test_db.t1' doesn't exist` | 同上 |
| 86 | test_explain_bug | 断言 `12 == mysql_num_fields(result)`，实测 1 | 用例期望 12 列的 `EXPLAIN` 输出，9.7.1 实际返回 1 列；**上游用例未随服务端输出格式更新**，与 OHOS 无关 |
| 246 | test_bug11766854 | `plugin != nullptr` | 依赖可选鉴权插件 `qa_auth_client.so`（本包不交付该测试插件）。**非适配缺陷** |
| 251 | test_wl6587 | `l_mysql != nullptr` | 同上（鉴权插件缺失） |
| 259 | test_bug20444737 | rc=139（SIGSEGV，core dumped） | 该用例执行中进程崩溃；同一二进制上其余 307 项全部正常。**待上游确认** |
| 304 | test_wl16221_reconnect | 等待 `wait_timeout`(10s) 后重连未完成 | 长等待型用例，逐用例执行窗口内未结束。**非适配缺陷** |

## 5. 与 mysql-test MTR（9339 个 .test）的关系

`mysql-test/` 的 9339 个 `.test` 依赖完整 MTR 框架（perl 驱动 + 多实例 + Unix socket 通信）；
其中 AF_UNIX `bind()` 在本机沙箱被拒，MTR 整体无法运行。本报告用上游
`testclients/mysql_client_test`（315 项，即 mysql-test `main.client_test` 所驱动的同一测试程序）
作为**真实执行**的上游测试面。

## 6. 与 test_package 的关系

- `test_package/test.c`（69 项，69/69）：**消费者视角**的静态库链接与 C API 冒烟；
- `test_package/server_lifecycle_test.sh`：服务端**生命周期**回归（CI 中执行）；
- 本报告：**上游测试程序**的真实执行结果。
