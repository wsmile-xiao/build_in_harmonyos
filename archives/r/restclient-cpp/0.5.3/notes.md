# restclient-cpp 0.5.3 适配笔记

## 编译环境
- 构建系统: cmake（上游同时提供 autotools 入口，本配方走 CMake）
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15（OHOS 工具链，`tools.build:compiler_executables`）
- 目标平台: OpenHarmony PC / aarch64 / os.version=6.0 / libc++ / cppstd=17 / Release
- Conan: 2.29.1，profile `ci/conan/profiles/ohos-aarch64`（`-pr:h` 与 `-pr:b` 同档，使 `can_run()` 为真、上游套件在设备本机真实执行）
- 资源防护: `build-slot.sh --mem 4000`（全机共享锁）+ `memcap-run.py --slow --mb 4000`（慢速档 + 硬预算），实测峰值 333MB
- 状态: built

## 编译步骤

1. `conan create archives/r/restclient-cpp/0.5.3 -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>`
2. `source()`：按官方 tag tarball 下载（sha256 见 manifest），依次应用 5 个 `strip: 1` 补丁，再把 `files/` 下的测试资产复制进 `test/`
3. `generate()`：`CMakeDeps` + `CMakeToolchain`，关键缓存变量
   - `BUILD_SHARED_LIBS=True`、`CMAKE_DEBUG_POSTFIX=""`
   - `CMAKE_GTEST_DISCOVER_TESTS_DISCOVERY_MODE=PRE_TEST`
   - `GTest_DIR` / `jsoncpp_DIR` 指向 Conan 依赖包内 `lib/cmake/<name>`
   - 额外写一个 build-scope 环境变量脚本，把构建树与依赖 lib 目录前插进 `LD_LIBRARY_PATH`（见问题 8）
4. `build()`：`cmake.configure()` → `cmake.build()` → 启动回环替身 `test/loopback_httpbin.py`（HTTP 8998 / TLS 8999 / CONNECT 代理 3128，ready-file 握手，30s 超时）→ `ctest -N` 复核注册数 == 51 → `ctest -E RestClientTest.TestRestClientGETHTTP2Code --timeout 60 --output-on-failure` → 关闭替身
5. `package()`：`cmake.install()` → 删除上游自带的 `lib/cmake` 包配置文件（见问题 11）→ `LICENSE` 复制到 `licenses/`
6. `test_package/`：以库使用者身份编译并运行 15 条断言（本机 `python3 -m http.server` 临时端口起服务，`www/index.json` 作被读文档）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 51 个 gtest 用例在 CI/真机上无法执行 | `test/Makefile.am` 依赖公网 `https://httpbin.org` 与本地 `squid`（`test/squid.conf`，666 端口）；容器与公网出口在 CI worker 上均不可用 ⇒ 要么全红要么被误判"无测试" | 新增纯标准库回环替身 `test/loopback_httpbin.py`（httpbin 端点子集 + TLS + CONNECT 代理），配方 `build()` 内自托管并跑完整套件；`test/tests.cpp` 的端点常量改为可用环境变量覆盖 |
| 2 | `ConnectionTestRemote` 6 例需要真实 TLS 握手，回环 HTTP 无法覆盖 | 该夹具测 CA 校验/ insecure / 代理 CONNECT，必须 HTTPS | 替身增加 TLS 8999（仅绑定 127.0.0.1 的自签名测试证书，公钥随包发布）与 CONNECT 代理 3128；`test_connection.cc` 改用 `RestClient::TestUrlTls` 并在 `SetUp()` 里 `SetCAInfoFilePath(RESTCLIENT_TEST_CA_FILE)`（编译期注入）；`TestFailForInvalidCA` 仍喂损坏 CA 以保持确定失败语义 |
| 3 | `find_package(GTest)`/`find_package(jsoncpp)` 命中 `vendor/jsoncpp-0.10.5` 或系统路径 | 上游 CMakeLists 直接 `add_subdirectory(vensor/...)` 并依赖默认搜索路径 | 补丁让 `test-program` 使用 Conan 导入目标 `GTest::gtest`、`jsoncpp`，并显式传 `GTest_DIR`/`jsoncpp_DIR` 锁到包内 config 目录；不再编译 vendor 目录 |
| 4 | 构建阶段就尝试执行 `test-program` | `gtest_discover_tests` 默认 `PRE_BUILD` 模式在 build 时运行被测程序，交叉构建下不可执行且污染日志 | `CMAKE_GTEST_DISCOVER_TESTS_DISCOVERY_MODE=PRE_TEST` |
| 5 | 新增测试文件（替身、证书、私钥）作为 `--- /dev/null` 补丁应用后落到了源码根目录，`test/` 下为空 | conan 的补丁管线（patch_ng）处理"新建文件"hunk 时以 `source_folder` 为根创建路径，不尊重头里的子目录 | 改走仓库既有约定：资产放配方目录 `files/`，`exports_sources = "patches/*", "files/*"`，在 `source()` 里 `copy()` 到 `test/`；补丁只保留对既有文件的修改 |
| 6 | 第二次 `refresh-patch --auto` 把新增文件判成"已修改"，生成的补丁头变成 `--- a/test/...` | 工具的 `_dry_run()` 校验会把新文件写进 `.orig` 基线，基线被污染 ⇒ 幂等性丢失 | 每次重新生成前先移走 `.orig` 里被误写的 0 字节新文件（本窗以 `~/tmp/uc2/TGFAT-1/orig-pollution-20260927/` 暂存），再 `refresh-patch --auto`；根治方案见 B草稿库 |
| 7 | 静态用例计数一度得 52 | `grep 'TEST_F('` 命中了上游注释掉的一行 `// TEST_F(ConnectionTestRemote, TestSSLCert)` | 逐文件区分活跃/注释：`test_restclient.cc` 26 + `test_connection.cc` 22（+1 注释） + `test_helpers.cc` 3 = **51**；配方以 `ctest -N` 的 `Total Tests` 作硬门禁复核 |
| 8 | `ctest -N` 报 `Error loading shared library librestclient-cpp.so` / `Result: 127` | `PRE_TEST` 发现模式会在 `ctest -N` 时**真的执行**被测程序；musl 的动态加载器忽略构建树里的 `DT_RUNPATH`，刚链接好的 `.so` 找不到 | 配方 `generate()` 写 build-scope 环境脚本，把 CMake 输出目录与 curl/jsoncpp/gtest 的包内 libdir 逐个 `prepend_path` 进 `LD_LIBRARY_PATH`（`Environment.prepend_path` 一次只能加一条路径），`ctest` 调用带 `env=["conanbuild", "conanrun"]` |
| 9 | 环境脚本已生成、内容正确，`ctest -N` 依旧取不到 `LD_LIBRARY_PATH` | `ConanFile.run(env=...)` 对字符串按**单个环境变量脚本名**处理（`env = [env] if isinstance(env, str)`），写 `"conanbuild,conanrun"` 等于引用一个不存在的脚本，静默不生效 | 必须传列表 `env=["conanbuild", "conanrun"]` |
| 10 | 补丁后 `test-program` 仍未生成，`ctest` 空跑 | 上游 CMakeLists 以 `GTEST_FOUND` 作门禁，而 config 模式的 `GTestConfig.cmake`（Conan 生成的那份）只设 `GTest_FOUND` ⇒ `if(GTEST_FOUND)` 恒假，测试目标被静默跳过 | 补丁改为 `if(GTEST_FOUND OR GTest_FOUND)`；配方另加 `ctest -N` 注册数 == 51 的硬门禁，防止"0 执行"再被静默吞掉 |
| 11 | `test_package` 消费者 `find_package(restclient-cpp)` 拿到的是上游安装的 `restclient-cpp-config.cmake`，其中不含 curl 接口 | `cmake.install()` 会把上游自带的 CMake 包文件一起装进 `lib/cmake`，与 Conan 生成的目标同名并遮蔽后者 | `package()` 里 `rmdir(self, <pkg>/lib/cmake)`，只保留 Conan 生成的 target 文件 |
| 12 | `test_package.cpp` 报 `fatal error: 'curl/curl.h' file not found` | 公开头 `restclient-cpp/connection.h` 直接 `#include <curl/curl.h>`，而 Conan 默认**不传播间接依赖的头文件与库**（`curl_INCLUDE_DIRS_RELEASE` 为空、`curl_COMPONENT_NAMES ""`） | 配方 `requirements()` 写成 `self.requires("curl/8.15.0", transitive_headers=True, transitive_libs=True)` |
| 13 | 上游错误文案断言失败：`TestRestClientGETFailureCode`、`TestInvalidProxy` | curl 8.x 改写了 `CURLE_COULDNT_RESOLVE_HOST`/`CURLE_COULDNT_CONNECT` 的字符串（`Couldn't resolve host name` → `Could not resolve hostname`；`Couldn't connect to server` → `Could not connect to server`），上游按旧文案字面比较 | 两处断言放宽为"接受 curl 7 与 curl 8 两种文案"（`EXPECT_TRUE(a == old \|\| a == new) << res.body`），不删用例、不改判通过；消费者测试同步放宽 |
| 14 | `TestSetHeaders` 失败 | 上游 httpbin 由 Go `net/http` 承载，会把回显的请求头名规范成大写首字母（`foo` → `Foo`）；回环替身原样保留大小写 ⇒ 断言取不到键 | 替身 `echo headers` 改为按 Go 的规范规则改写头名（`canonical_header_key`），与真实 httpbin 行为一致 |

## 源码修改

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| `CMakeLists.txt` | 修 `GTEST_FOUND` 门禁、测试目标改用 Conan 依赖（含 jsoncpp 导入目标名探测）、只把 `test-program` 抬到 C++17、注入回环 TLS CA 路径、不再编译 vendor/jsoncpp | 补丁 | ✅ 0001-CMakeLists.txt.patch |
| `test/test_connection.cc` | `ConnectionTestRemote` 端点改回环 TLS + 加载本地测试 CA；`TestInvalidProxy` 文案断言放宽 | 补丁 | ✅ 0002-test-test_connection.cc.patch |
| `test/test_restclient.cc` | `TestRestClientGETFailureCode` 的 `CURLE_COULDNT_RESOLVE_HOST` 文案断言放宽 | 补丁 | ✅ 0003-test-test_restclient.cc.patch |
| `test/tests.cpp` | 端点常量支持环境变量覆盖，新增 `TestUrlTls` | 补丁 | ✅ 0004-test-tests.cpp.patch |
| `test/tests.h` | 声明 `TestUrlTls` | 补丁 | ✅ 0005-test-tests.h.patch |
| `test/loopback_httpbin.py`、`test/localhost-test-only.crt`、`test/localhost-test-only.key` | 回环 httpbin/squid 替身与仅本机使用的测试证书 | 新增文件，经 `files/` + `exports_sources` 投递 | 非补丁（新增资产，见问题 5） |
| `test/test_helpers.cc` | 未改动 | — | 无需补丁 |

## 依赖版本

- curl/8.15.0（`requires`，制品仓已发布，OHOS profile 二进制实测可安装；配方以 `transitive_headers/transitive_libs` 向消费者传播）
- gtest/1.17.0、jsoncpp/1.9.8（`test_requires`，同上）
- clang 15（OHOS 工具链）

## 验证结果

```bash
$ sh ~/tmp/uc2/TGFAT-1/create-rcc1.sh        # build-slot + memcap 包裹的 conan create（attempt 20）
restclient-cpp/0.5.3: HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "executed": 50, "passed": 50,
  "failed": 0, "skipped_by_upstream": 1, "source_declared_total": 51, "registered": 51,
  "excluded_public_network": 1, "framework": "gtest+ctest"}
15/15 consumer assertions passed
MEMCAP[run] peak=333MB budget=4000MB rc=0 用时41.2s
END 2026-09-27 15:14:59 rc=0                       # 日志：~/tmp/uc2/TGFAT-1/rcc-build/create-rcc1.a20.log

$ sh ~/tmp/uc2/TGFAT-1/create-rcc1-clean.sh 2      # 从零复跑：conan remove -c 后重新导出/下载/打补丁
restclient-cpp/0.5.3: Removed recipe and all binaries
restclient-cpp: Source https://github.com/mrtazz/restclient-cpp/archive/refs/tags/0.5.3.tar.gz retrieved from local download cache
restclient-cpp/0.5.3: Apply patch (portability) x5
HMBS_UPSTREAM_TEST_RESULT=… 同上（executed 50 / passed 50 / failed 0 / registered 51 / declared 51）
15/15 consumer assertions passed
MEMCAP[run] peak=329MB budget=4000MB rc=0 用时41.6s
END 2026-09-27 15:18:53 rc=0                       # 日志：~/tmp/uc2/TGFAT-1/rcc-build/create-rcc1.clean2.log
```

ctest 汇总行：`100% tests passed, 0 tests failed out of 50`；`The following tests did not run: 21 - RestClientTest.TestRestClientOPTIONSCode (Skipped)`（上游自带 `GTEST_SKIP()`）；`ctest -N` 的 `Total Tests: 51`（配方内 == 51 硬门禁）。

框架门禁同源复跑（最终交付状态，2026-09-27 16:07，日志 `~/tmp/uc2/TGFAT-1/rcc-build/finish-rcc2.a1.log`）：

```bash
$ python3 scripts/ohc-run.py finish restclient-cpp 0.5.3 built     # 槽位闸 --mem 4000 包裹
Step 4/10 G1 PASS / G0 PASS / G2 PASS（conan create --build=missing，@ohpcd/stable）/ G3 PASS (R26)
Step 5/10 W3 本地 CI 模拟通过（reports/w3-local-ci.log:341）
  HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "executed": 50, "passed": 50, "failed": 0,
    "skipped_by_upstream": 1, "source_declared_total": 51, "registered": 51,
    "excluded_public_network": 1, "framework": "gtest+ctest"}
  conan-create.log:351 → 15/15 consumer assertions passed
Step 7/10 知识完整性检查通过（manifest.yaml: knowledge_count=13 unreferenced=0）
```

同一轮里 G2 与 W3 两条独立载体给出逐字一致的测试账本，故上表两组手工复跑数字与框架口径同源。

W4 提交前独立审计（`pre_pr_audit.py generate` 的审计输入正好覆盖本 PR 的 18 个交付路径，逐条对照 `.gitcode` 侧 code-style 25 条 + review-memory 30 条）：

```bash
$ python3 scripts/pre_pr_audit.py report --audit-result ~/tmp/uc2/TGFAT-1/w4/audit-report.json --repo-dir $PWD --package restclient-cpp --version 0.5.3
统计: P0=0 P1=0 P2=0 P3=6
✅ W5 审计通过 — 可以创建 PR
```

行尾归一（code-style 21）之后在最终交付形态上复跑一次从零构建，作为绑定证据：

```bash
$ sh ~/tmp/uc2/TGFAT-1/create-rcc1-clean.sh 3     # conan remove -c 后重下官方 tarball、重打 5 个补丁
restclient-cpp/0.5.3: HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "executed": 50, "passed": 50,
  "failed": 0, "skipped_by_upstream": 1, "source_declared_total": 51, "registered": 51,
  "excluded_public_network": 1, "framework": "gtest+ctest"}   # create-rcc1.clean3.log:224
15/15 consumer assertions passed                              # :340
MEMCAP[run] peak=332MB budget=4000MB rc=0 用时43.0s           # :342
END 2026-09-27 16:24:08 rc=0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `lib/librestclient-cpp.so` | 63,872 B | 动态库（`shared=True`），OHOS/aarch64/Release |
| `include/restclient-cpp/{restclient,connection,helpers,version}.h` | 4 个 | 公开头文件（`connection.h` 依赖 `<curl/curl.h>`，故配方传播 curl 头） |
| `licenses/LICENSE` | 1,062 B | 上游 MIT 许可 |
| `test-program`（构建产物，不打包） | — | 上游 51 例 gtest 可执行体，在 `build()` 内真实执行 |

## 注意事项

- 上游 `TestRestClientGETHTTP2Code` 需要与公网主机做 HTTP/2 协商，任何回环替身都无法提供，故本轮以 `ctest -E` 显式排除并在 PR 正文的未执行测试项中列明原因；未删除任何用例。
- 上游 `TestRestClientOPTIONSCode` 自带 `GTEST_SKIP()`（注释理由：httpbin 不支持 OPTIONS，且原目标是公网 reqbin），本轮沿用上游判断保持跳过，不改判为通过；故"ctest 执行 50 例"中真实断言的是 49 例。
- 回环替身实现的 httpbin 兼容面是**子集**：pretty JSON 以换行结尾、恒发 `Connection: keep-alive`、请求头名按 Go `net/http` 规范改写（首字母大写，见问题 14）、`url` 字段由原始 target + Host 重建——上游断言按字面比较，偏离任何一条都会假失败。
- `test_package` 的消费者断言里 `Content-Type` 用大小写无关查找：`HeaderFields` 是原样保留服务端拼写的 map，而 `python3 -m http.server` 发的是 `Content-type`（实测），直接 `count("Content-Type")` 会 0 命中。
- 测试证书 `localhost-test-only.*` 仅绑定 127.0.0.1/localhost、仅用于本机 TLS 握手，属测试公钥/临时私钥，**不是生产凭证**，也不参与打包产物。仓库对"测试密钥随包入库"已有先例（`archives/d/drogon/1.9.12/resources/server.key`、`archives/l/libmsquic/2.5.7/testcerts/localhost_key.pem`），故本配方按同一口径提交；不在 `source()` 里现生成证书，是因为那会把 `openssl` 变成构建期硬依赖（CI worker 上该工具可得性未证），固定测试材料反而可复核。
- `commands.json` 不随包发布：本配方是库（`package_type = "library"`），无可执行产物（R38）。
- 静态 51 例、注册 51 例、实际执行 50 例（含 1 例上游自跳过）、消费者 15 条断言四者同源；本笔记与 manifest、MANIFEST.yml、PR 正文在 W3 完成后一次性对齐。
- **E017 镜像注入再次污染活文件（本轮实测，提交前必须逐文件核对）**：Step 4 的 `conan-verify` 用自己的 `ghfast.top` 列表并打印"已恢复原始 conandata.yml"，但 Step 5 的 `build_and_test.sh` pre-download 又按 `gh-proxy.com` 列表改写一次且**未真正还原**——暂存前 `git show :...conandata.yml` 实测 `sources.url` 是两元素镜像列表。已用 `~/tmp/uc2/TGFAT-1/restore-conandata-official-url.py` 把 `sources.url` 钉回官方标量 + 真实 sha256（`ca450e15…`），污染副本留档 `~/tmp/uc2/TGFAT-1/conandata.yml.polluted-*` 作证据。共享下载缓存里该包的 sidecar 同时登记官方 URL 与镜像 URL（AGENTS §12.3），因此缓存条目未被判 dirty、本轮源码取自本地缓存而非镜像。
- **框架侧三条既有行为，本 PR 未改框架，如实登记**：① Step 3 的 G0「干净构建验证」对纯 CMake 项目必报 `configure 失败 (exit 127)`（它按 autotools 惯例找 `./configure`），非阻塞，真正的干净构建证据是 Step 4 的 G2 与 Step 5 的 W3；② Step 8 `gen_summary` 抛 `'str' object has no attribute 'append'`，SUMMARY.md 未生成（框架缺陷，按 AGENTS §9 不得手写 SUMMARY.md）；③ `junk_check.sh` 在 incremental 模式取 `git diff origin/main...HEAD`，而本 fork 的 `main` 落后 `upstream/main` 数百个提交，三路差集会把 605 个他人包（含他人仓库里自带的 `.staging-verified`）扫进本 PR 并触发 JC6 原子性失败——按 AGENTS §9 的既定规避在 worktree 根落一份只含本任务 18 个交付路径的 `pr.diff`，junk_check 即切到 `prdiff` 模式（与 buildbot 在 CI 上喂给它的同一份清单），实测输出 `检查模式: prdiff (18 个文件)` 后 JC 通过。另：`check_knowledge_gap.py` 判"是否已被引用"只看条目行内有无 `ref:` 字面量，故 `manifest.yaml` 的 13 条 `knowledge_gained` 已逐条补真实落点（`conanfile.py`/`patches/*`/`files/*`/`notes.md`/草稿路径）作为 `ref:`，`unreferenced` 由 13 归 0。
- **W4 审计文件的落盘位置与本 PR 的提交边界**：`.gitignore` 第 96 行整目录忽略 `reports/`、第 242 行忽略 `.ci-result.json`，因此 `reports/audit-result.json`（P0/P1/P2=0、P3=6，verdict=pass）与 W3 的 `.ci-result.json`（`exit_code: 0`、`log_sha256: 8732dee5…`）都只作为本地门禁证据留在工作区，不进 PR——仓库里虽有 340 份被强制加入的 `reports/audit-result.json` 历史样本，但那是当前忽略规则之前的形态，按框架现行口径提交报告目录反而与 R19/规则 24 冲突。另记一条框架现状（本 PR 不改框架）：`pre_pr_audit.py check` 只在**仓库根**找 `.ci-result.json`，而 `finish` 的 W3 把该文件写在**版本目录**下，所以 `check` 对已完成 W3 的任务恒报"未找到"；判定 W3 请以版本目录的 `.ci-result.json` + `reports/w3-local-ci.log` 为准。
---

**编译结束**: 2026-09-27 15:44
**最终状态**: built
