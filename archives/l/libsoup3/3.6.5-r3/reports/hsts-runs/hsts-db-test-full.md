# libsoup3 3.6.5-r3 — hsts-db-test 实跑证据（R12 由 hsts-db-test-full.log 改写）

> 本文件为 R12 处置产物：原 `reports/hsts-runs/hsts-db-test-full.log` 因仓库禁止
> `*.log` 提交而改写为 .md，证据要点完整保留（命令、cwd、退出码、首错）。

## 命令与退出码

- **命令**（cwd = `<build_dir>/builddir/tests`，指 R11 轮 `-Dtests=true` 复验构建）：
  `./hsts-db-test`（LD_LIBRARY_PATH 含 glib/libpsl/libnghttp2 与 /usr/local/lib）
- **exit_code = 134**（SIGABRT：g_assert 断言失败，非 SIGTRAP 133）

## 补丁后行为（关键证据）

- 补丁前：`g_uri_get_port(https_uri)` 传 NULL → glib 2.84
  `GLib-FATAL-CRITICAL assertion 'uri != NULL' failed` → **SIGTRAP exit 133**
  （进程级崩溃，3 项全部无法运行）。
- 补丁后：不再 SIGTRAP；进程正常执行测试体，整体 exit 134 为断言失败。

## 输出要点（TAP）

- `TAP version 14`，计划 `1..3`（hsts-db-test 3 项全部注册）。
- 首错（https 依赖用例统一首错）：
  `ERROR:../tests/hsts-db-test.c:88:session_get_uri: assertion failed (error == NULL):
   Could not connect to localhost: Connection refused (g-io-error-quark, 39)`
- 随后的断言：`Unexpected status 0 (null) (expected 200 OK)`、
  `Unexpected status 301 Moved Permanently (expected 200 OK)`、
  `(enforced == expected_enforced)` 失败。
- 3 项用例 `/hsts-db/basic`、`/hsts-db/subdomains`、`/hsts-db/large-max-age`
  均命中同一 https 连接阻塞。

## 阻塞归属与恢复条件

- 归属：**平台 GIO TLS 后端缺失**（同 hsts-test——OHOS 无 glib-networking，
  GDummyTlsBackend supports_tls=0，https_uri 保持 NULL）。
- 恢复条件：具备 GIO TLS 后端的 CI/设备上，同一 `-Dtests=true` 构建即可连接
  本地测试服务器跑通。

> 完整 28 项逐项退出码台账见 `reports/hsts-runs/hsts-28-ledger.md`；
> 补丁后双口径统计见 `reports/test-report.md`。