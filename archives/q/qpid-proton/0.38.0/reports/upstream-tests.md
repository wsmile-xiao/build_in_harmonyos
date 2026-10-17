# qpid-proton 0.38.0 上游测试实测报告（HarmonyOS PC 真机）

复跑命令（在 worktree 根目录）：

```
conan create archives/q/qpid-proton/0.38.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

配方 `build()` 内执行 `ctest -V --timeout 120`（工作目录 = 构建目录），完整输出留在
构建目录 `upstream-ctest.log`；日志尾部打印两条机器可读证据：

```
QPID_PROTON_UPSTREAM_TEST_RESULT={"status": "failed", "framework": "ctest", "command": "ctest -V --timeout 120",
 "return_code": 8, "registered": 11, "passed": 9, "failed": 2,
 "catch2_test_cases": 91, "catch2_test_cases_passed": 89,
 "catch2_assertions": 2672, "catch2_assertions_passed": 2660,
 "failed_tests": ["3/11 Test #3: c-proactor-test ...***Failed",
                  "5/11 Test #5: c-ssl-proactor-test ...***Failed"]}
QPID_PROTON_SSL_TEST_CERT={"c/tests/ssl-certs/tserver-certificate.pem": "Nov 24 18:10:39 2025 GMT",
                           "c/tests/ssl-certs/tclient-certificate.pem": "Nov 24 18:10:39 2025 GMT"}
```

## 逐条结果（ctest 注册 11 条目：9 通过 / 2 失败）

| # | ctest 条目 | 结果 | 口径与说明 |
|---|-----------|------|-----------|
| 1 | c-core-test | ✅ 1.5s | Catch2 72 用例 / 1299 断言 全通过 |
| 2 | c-extra-test | ✅ 1.4s | Catch2 1 用例 / 254 断言 全通过 |
| 3 | c-proactor-test | ❌ 1.8s | Catch2 15 用例（14 通过）/ 234 断言（226 通过）；唯一失败用例 `proactor_ssl`：8 断言因证书过期失败 |
| 4 | c-raw-connection-test | ✅ 1.4s | Catch2 2 用例 / 846 断言 全通过 |
| 5 | c-ssl-proactor-test | ❌ 2.0s | Catch2 1 用例（未通过）/ 39 断言（35 通过）：`pn_ssl_domain_set_credentials` 之后的双向验证因证书过期失败 |
| 6 | c-fdlimit-tests | ✅ 4.0s | Python `c/tests/fdlimit.py`：fd 上限下跑上游可执行文件 |
| 7 | c-example-tests | ✅ 5.7s | Python `tests/examples/testme`：起真实 `c-broker` + send/receive 回环，7 子用例全过 |
| 8-11 | fuzz-connection-driver / fuzz-message-decode / fuzz-url / fuzz-sniff-header | ✅ ×4 | libFuzzer `StandaloneFuzzTargetMain` 语料回归（上游默认 `ENABLE_FUZZ_TESTING=ON`） |

Catch2 口径合计：**91 用例（89 通过，97.8%）/ 2672 断言（2660 通过，99.6%）**。

## 两个失败条目的根因（与 OHOS 适配无关）

上游仓库自带的两张测试证书 `c/tests/ssl-certs/{tserver,tclient}-certificate.pem`
签发于 2015-11-27，**有效期至 2025-11-24**（`openssl x509 -noout -dates` /
`ssl._ssl._test_decode_cert` 实测 `notAfter=Nov 24 18:10:39 2025 GMT`）。本机日期为
2026-09-21，因此这些用例在**任何**平台上都会失败，报错原文：

```
FAILED: REQUIRE( pn_ssl_domain_set_credentials(...) == 0 )
CHECK_THAT( *server.last_condition, cond_empty() )  非空:
  pn_condition{"amqp:connection:framing-error",
               "SSL Failure: error:0A000415: SSL routines::ssl/tls alert certificate expired"}
  pn_condition{"amqp:connection:framing-error",
               "SSL Failure: error:0A000086: SSL routines::certificate verify failed"}
```

处置：**未修改任何上游测试数据**（证书属上游夹具）。若后续上游刷新证书，该 2 条目即会恢复
通过，其余 9 条目与断言数不受影响。

## TLS 开关的取舍（记录）

- `SSL_IMPL=none` 时：`c-proactor-test` 全过（SSL 用例走 skip），但 `c-ssl-proactor-test`
  与 `c-example-tests`（其 broker 需要装证书）**整体失败** → 9/11 且失败原因是"能力未启用"。
- `SSL_IMPL=openssl`（本次交付）：`c-example-tests` 变全绿，`c-proactor-test` 中 SSL 用例
  真跑，失败收敛为"上游证书过期"这一条与平台无关的原因 → 9/11，理由可核实。

## patches/0001 的回归证据

修复前：`c-proactor-test` 在 `proactor_interrupt_timeout` 用例内自旋不返回，ctest 1500s
超时（`***Timeout 1500.08 sec`），整套 ctest 耗时 1510s。修复后：该用例 8 断言全过，
`c-proactor-test` 1.9s 跑完，整套 ctest 25s。
