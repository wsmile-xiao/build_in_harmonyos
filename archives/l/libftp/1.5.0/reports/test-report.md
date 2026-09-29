# Test Report — libftp 1.5.0（R05 全量闭合版）

> R05：client.cpp 集成套件（58 宏）真实执行，闭合最后未运行入口；上游 104 宏全部可运行且已运行。
> 本报告与 PR 统计表、`test_package/MANIFEST.yml` 三处同口径一致。

## 1. 上游测试全量清点（单一可复现口径）

发现命令（cwd = 官方 tarball 根目录，退出码 0）：

```bash
grep -rhoE '^\s*(TEST|TEST_F|TEST_P|TYPED_TEST|TYPED_TEST_P)\(' --include=*.cpp --include=*.hpp . | wc -l   # → 104
```

- **104 个 TEST 宏定义**（TEST=44 + TEST_F=45 + TEST_P=15，TYPED=0），跨全部测试面：
  - `test/`（71）：client.cpp 58 + utils.cpp 5 + 9 个单用例入口（ascii_istream/ascii_ostream/file_list_reply/file_modified_time_reply/file_size_reply/net_utils/replies/reply）；
  - `app/cmdline/test/`（33）：parser.cpp 30 + utils.cpp 3 —— R02/R03 遗漏，R04 补全；
  - 辅助不计入：test/test_utils.cpp 0 宏；example/ 无 TEST；test/server/pyftpdlib/ 为 vendored Python 包。
- 参数化展开的实际执行用例数以 gtest 运行输出 `[==========] N tests` 为准（不手工推算）。

## 2. 逐入口可运行性台账（全量）

完整台账见 `reports/upstream-test-ledger.md`。摘要：

| 入口 | TEST 宏 | 判定 | 结果 |
|---|---|---|---|
| app/cmdline/test/parser.cpp | 30 | 可运行 | **已运行** 33/33 PASSED（与 utils 同目标） |
| app/cmdline/test/utils.cpp | 3 | 可运行 | **已运行**（同上） |
| test/ 9 个单元入口（ascii_istream/ascii_ostream/file_list_reply/file_modified_time_reply/file_size_reply/net_utils/replies/reply/utils） | 13 | 可运行 | **已运行**，参数化展开实际执行 107/107 PASSED |
| test/client.cpp | 58 | 可运行 | **已运行**（R05 自建配置真实执行）：参数化展开 123 用例，122 PASSED / 1 SKIPPED / 0 FAILED |

## 3. 上游测试真实执行结果（R04 + R05 实际运行）

**cmdline 套件**（R04）：
```bash
cwd: /storage/Users/currentUser/tmp/libftp-cmdline-run
命令: ./build/cmdline_tests --gtest_color=no
退出码: 0
输出: [==========] 33 tests from 2 test suites ran. (0 ms total)  [ PASSED ] 33 tests.
日志: archives/l/libftp/1.5.0/reports/cmdline-suite-run.log
SHA-256: 02d3a73e3dcdf4cf560db6677c7bc07aeaca4985c9e16c59489f54a177dfa9cd
```

**test/ 单元入口**（R02 成果复跑）：
```bash
cwd: /storage/Users/currentUser/tmp/libftp-gtest-run
命令: ./build/ftp_units --gtest_color=no
退出码: 0
输出: [==========] 107 tests from 11 test suites ran. (3 ms total)  [ PASSED ] 107 tests.
日志: archives/l/libftp/1.5.0/reports/upstream-unit-tests-run.log
SHA-256: e28b2896d96aee9d3af1d0e952866ce91f7640bbe4a81a9ec6c5b19ff4d2069a
```

**client.cpp 集成套件**（R05 新增，闭合最后未运行入口）：
```bash
cwd: /storage/Users/currentUser/tmp/libftp-r5-client-build
命令: ./build/ftp_client --gtest_color=no        # 自建 CMake 目标（仅 client.cpp + test_utils.cpp + gtest main）
前置: LIBFTP_TEST_SERVER_PATH=test/server/server.py；python3 可用；vendored pyftpdlib 可导入（含 TLS_FTPHandler）；
      端口 2121(明文)/2142(FTPS) 空闲；certs/ 证书齐全；服务器真实启动（starting FTP server / FTP+SSL server）
退出码: 0
输出: [==========] 123 tests from 7 test suites ran. (9414 ms total)  [ PASSED ] 122 tests.  [ SKIPPED ] 1 test.
日志: archives/l/libftp/1.5.0/reports/client-suite-run.log
SHA-256: （见 reports/client-suite-run.log.sha256）
```

## 4. 适配后测试统计（三处一致口径）

| 测试类型 | 用例数 | 说明 |
|---|---|---|
| cmdline 套件（parser+utils，直接用例） | **33** | 真实运行，33/33 PASSED |
| 上游单元入口（test/ 9 入口含参数化展开） | **107** | R02 成果复跑，107/107 PASSED |
| 上游集成入口（client.cpp 58 宏参数化展开） | **123** | R05 真实运行，122 PASSED / 1 SKIPPED / 0 FAILED |
| 鸿蒙特有测试（test_package 消费者测试 test.cpp） | 1 | 1/1 PASSED（0.06s） |
| **适配后合计（实际执行）** | **264** | = 33 + 107 + 123 + 1 |

## 5. 验证结果

- 编译状态：通过（OHOS aarch64 交叉编译，clang 15，静态库 libftp.a；conan-verify G2-G4 复核 PASS）
- 上游测试用例通过率（全部已运行）：**262/263 PASSED + 1 SKIPPED（99.6%）**；唯一 SKIP = `ssl_client.login`（上游显式 GTEST_SKIP，pyftpdlib 不处理 REIN 命令，控制连接不切非 SSL 模式），**不计入通过**，单独列出
- 新增测试用例通过率：**1/1（100%）**
- 上游 TEST 宏定义总数：**104**，**全部可运行且已运行，未运行项 = 0**

## 6. 交付态与一致性

- 三处统计（本报告 / test_package/MANIFEST.yml / PR 正文）同口径：104 宏全部已运行、已执行 263 用例、未运行 0、适配后合计 264
- PR 正文「唯一不可运行入口的阻塞归属与恢复条件」段已删除（已无未运行项）
- 库内 .gitignore 取反例外保留（R03），根 .gitignore 与 main 逐字节一致（未再改动）
- 上游测试源码零修改；无删除/注释/#if 0/跳过/弱化；三套测试面（cmdline / test/ 单元 / client 集成）均真实执行
- client.cpp 运行前置（pyOpenSSL、自编 libboost_process/libboost_filesystem、自建 CMake 目标、FTP 服务器）均为本地临时构建依赖，未进入本库 PR 交付范围