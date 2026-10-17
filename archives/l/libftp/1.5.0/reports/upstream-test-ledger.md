# libftp 1.5.0 上游测试逐入口可运行性台账（R05 全量闭合修订）

清点口径（单一可复现、覆盖全部测试面）：

```bash
cd <tarball>/libftp-1.5.0
grep -rhoE '^\s*(TEST|TEST_F|TEST_P|TYPED_TEST|TYPED_TEST_P)\(' --include=*.cpp --include=*.hpp . | wc -l   # → 104
```

构成：TEST=44 + TEST_F=45 + TEST_P=15（TYPED_TEST/TYPED_TEST_P=0）。
- `test/`：**71** 宏（client.cpp 58 + utils.cpp 5 + 其余 9 个入口各 1）；
- `app/cmdline/test/`：**33** 宏（parser.cpp 30 + utils.cpp 3）——R02/R03 遗漏，R04 补全；
- 辅助不计入：`test/test_utils.cpp` 0 宏（仅被引用）；`example/` 无 TEST；`test/server/pyftpdlib/` 为 vendored Python 包。

| 源文件 | TEST 宏 | include 依赖 | 判定 | 依据/结果 |
|---|---|---|---|---|
| app/cmdline/test/parser.cpp | 30 (TEST) | gtest+gmock+command_parser.hpp/command.hpp/cmdline_exception.hpp | **可运行且已运行** | 33/33 PASSED（cmdline-suite-run.log） |
| app/cmdline/test/utils.cpp | 3 (TEST) | gtest+utils.hpp | **可运行且已运行** | 同上 |
| test/ascii_istream.cpp | 1 (TEST_P) | gtest+ftp headers | **可运行且已运行** | 107 套件内（upstream-unit-tests-run.log） |
| test/ascii_ostream.cpp | 1 (TEST_P) | 同上 | **可运行且已运行** | 同上 |
| test/file_list_reply.cpp | 1 (TEST) | 同上 | **可运行且已运行** | 同上 |
| test/file_modified_time_reply.cpp | 1 (TEST) | 同上 | **可运行且已运行** | 同上 |
| test/file_size_reply.cpp | 1 (TEST) | 同上 | **可运行且已运行** | 同上 |
| test/net_utils.cpp | 1 (TEST) | 同上 | **可运行且已运行** | 同上 |
| test/replies.cpp | 1 (TEST) | 同上 | **可运行且已运行** | 同上 |
| test/reply.cpp | 1 (TEST) | 同上 | **可运行且已运行** | 同上 |
| test/utils.cpp | 5 (TEST) | gtest+gmock+ftp headers | **可运行且已运行** | 同上 |
| test/client.cpp | 58 (TEST_F 45+TEST_P 13) | client.hpp/ssl.hpp + **test_server.hpp** | **可运行且已运行** | R05 真实执行（client-suite-run.log）：`[==========] 123 tests from 7 test suites ran`，**122 PASSED / 1 SKIPPED / 0 FAILED**。唯一 SKIP = `ssl_client.login`（client.cpp:1191 上游显式 `GTEST_SKIP`：pyftpdlib 不处理 REIN 命令，控制连接不切非 SSL 模式），属上游已知 pyftpdlib 限制，非服务器未启动 |
| test/test_utils.cpp | 0 | 辅助（被 file_list_reply/replies 引用） | 编译为辅助目标 | 无独立 TEST，不计入 |

## client.cpp 自建配置记录（R05 实际执行）

R04 曾判定 client.cpp 不可运行，依据为：制品仓全部 boost（1.76.0~1.91.0.1.3）`components["process"]` 引用=0，最小复现 `find_package(Boost 1.88.0 COMPONENTS filesystem process REQUIRED CONFIG)` → configure 失败 `Boost::filesystem/process target not found`。R05 依 `integration_suite_build_authorized: true` 改为**自建构建配置**真实绕过：

1. **自建 CMake 目标**（本地临时工程 `/tmp/libftp-r5-client-build`，不进入 PR）：仅编译 `test/client.cpp` + `test/test_utils.cpp` + 本地 gtest main；链接制品仓 `libftp.a` + `openssl` 静态库 + `GTest::gtest/gmock`；**不改动上游任何测试源码**。
2. **boost 已编译符号补齐**（本地临时静态库 `/tmp/libftp-r5-boostlibs`，不进入 PR）：制品仓 boost/1.90.0 包内 `include/boost/process.hpp` 头文件存在但无 `libboost_process`/`libboost_filesystem`；从缓存 boost 1.90.0 官方源码树编译 `libs/process/src`（`detail/environment_posix.cpp`、`posix/close_handles.cpp` 等）与 `libs/filesystem/src` 为静态库，仅作本地测试链接依赖。
3. **FTP 服务器前置**：`LIBFTP_TEST_SERVER_PATH` 指向 `test/server/server.py`；本机 `python3` 可用；vendored `pyftpdlib` 可导入（含 `TLS_FTPHandler`，pyOpenSSL 由 OHOS 原生 wheel 补齐）；端口 2121/2142 可用；证书可达。服务器真实启动（日志含 `starting FTP server` / `starting FTP+SSL server`）。
4. **运行修复**：鸿蒙内核不支持 `close_range` syscall（Signal 31 崩溃致 boost::process fork 子进程即死），以 `-DBOOST_PROCESS_V2_POSIX_FORCE_DISABLE_CLOSE_RANGE` 重编 close_handles.cpp（回退 `/dev/fd` dirent 遍历）后子进程正常 spawn，服务器真实启动。
5. **结论**：client.cpp 58 宏全部真实执行（参数化展开 123 用例）。阻塞归属无；R04 的"制品仓组件缺口"判定已被本任务授予的自建配置消除。服务器启动依赖的 pyOpenSSL/boost 编译符号均为**本地临时构建依赖，不进入 PR 交付范围**。

## 执行统计（全量口径，三处一致）

- 上游 TEST 宏定义总数：**104**（test/ 71 + cmdline 33），**全部可运行且已运行**。
- 实际执行用例数：**33（cmdline） + 107（test/ 9 个单元入口参数化展开） + 123（client.cpp 58 宏参数化展开）= 263 用例**；其中 client.cpp 套件 122 PASSED / 1 SKIPPED / 0 FAILED，其余 140/140 PASSED。
- 未运行：**0**（R05 已闭合最后未运行入口）。
- 适配后合计（实际执行）= 263 + 1（鸿蒙消费者 test_package）= **264**
- SKIP 明细：`ssl_client.login` 1 条 = 上游显式 `GTEST_SKIP`（pyftpdlib REIN 限制），**不计入通过**，单独列出并给出原因。
- 禁止项对照：未修改/删除/注释/#if 0 任何上游测试入口；SKIP 未计入通过；未把未运行入口计入合计；未写"整套不可运行"；census 覆盖全部测试面（非仅 test/）。