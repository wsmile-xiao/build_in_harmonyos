# DRAFT-restclient-cpp-0.5.3-loopback-httpbin-standin：上游测试打公网端点（httpbin/squid），在配方 build() 内用纯标准库回环替身自托管同语义服务，使整套 gtest 在 CI/真机真实执行

- **软件/版本**：restclient-cpp 0.5.3（`archives/r/restclient-cpp/0.5.3/`）
- **实证环境**：HarmonyOS PC / OpenHarmony aarch64，clang 15 + musl，Conan 2.29.1，profile `ohos-aarch64`（`-pr:h` 与 `-pr:b` 同档）
- **一句话**：把"测试要连外部 HTTP 服务"这一类不可交付依赖，换成配方自带、零第三方依赖、只监听 127.0.0.1 的替身；明文/TLS/CONNECT 代理三层各覆盖一条独立代码路径。

## 1. 错误签名（error_signature）

```
RESTClientTest.TestRestClientGETCode  FAILED   (curl code 7 / CURLE_COULDNT_CONNECT)
curl: (6) Could not resolve host: httpbin.org
curl: (5) Couldn't resolve proxy name / Problem ssl steering
1 tests passed, 50 tests failed out of 51
ctest: No tests were found
```

上游侧触发点（源码取证，非推测）：

- `test/Makefile.am`：测试目标先起 `httpbin`（python 应用）与 `squid -c ./squid.conf`，`RESTCLIENT_TEST_SERVER` 之类变量由 Makefile 注入；
- `test/tests.cpp`：`TestServer = "localhost:8998"`、`TestUrl = "http://" + TestServer`，但 `RestClient::TestNonExistantUrl` 与多数断言按 httpbin 的响应字面写死；
- `test/test_connection.cc`：`ConnectionTestRemote() { testUrl = "https://httpbin.org"; }` —— 6 个用例需要**真实 TLS 握手**，另有代理用例需要 **CONNECT 代理**；
- `test/test_restclient.cc`：`TestRestClientGETHTTP2Code` 打 `https://httpbin.org/get --http2`，`TestRestClientOPTIONSCode` 打公网 `api.reqbin.com`（上游自己已 `GTEST_SKIP()`）。

## 2. 根因（root_cause）

这类库的测试**断言对象是外部服务**，不是被测代码。集成环境同时断三条路：CI worker 无公网出口、真机不装 docker/httpbin/squid、即使有网也会因上游限流随机翻红。

于是只有三种走法：① 硬跑 → 整批红；② 关掉测试入口 → 交付"0 执行"，在本仓是不可交付口径；③ **把外部服务的最小语义搬到本机** —— 本条知识走第 ③ 种。知识库既有条目只覆盖"构建期取不到测试框架"（FetchContent 拉 googletest 一类），没有覆盖"测试运行时的外部服务端"，因此这一类是空白区。

## 3. 推荐方案（rec_priority 1：`stdlib-loopback-standin-in-build`）

三层替身 + 端点常量可覆盖 + 构建期注册数门禁，缺一不可：

**(1) 端点收敛**（补丁 0003/0004/0001）：`tests.cpp` 里把 `TestServer/TestUrlTls/TestProxyUrl` 改成"环境变量优先、默认回环"，头文件补声明；`CMakeLists.txt` 给 `test-program` 注入 `RESTCLIENT_TEST_CA_FILE` 编译定义并改用 Conan 的 `GTest::gtest` / `jsoncpp` 导入目标（不再编译 `vendor/jsoncpp-0.10.5`）。

**(2) 替身本体**（`test/loopback_httpbin.py`，仅标准库）：

| 监听 | 覆盖的代码路径 | 关键语义 |
|---|---|---|
| HTTP `127.0.0.1:8998` | 传输与响应解析 | `/get /post /put /patch /delete /options /anything /headers /basic-auth/<u>/<p> /redirect/<n> /delay/<s> /status/<code>` |
| TLS `localhost:8999` | 证书校验 / `SetCAInfoFilePath` / `SetInsecure` | 仅绑定回环的自签名证书（公钥随包发布，非生产凭证） |
| CONNECT 代理 `127.0.0.1:3128` | 代理路径与 `SetProxy` 参数族 | 只做 CONNECT 字节转发，不解析 HTTP，语义等同 squid 对本用例的作用 |

**保真约束**（上游断言按字面比较，偏离即假失败）：响应体是 pretty JSON 且以换行结尾；恒发 `Connection: keep-alive`；保留请求头原始大小写；`url` 字段由原始 request-target + `Host` 头重建，而不是由本地 socket 名推导。

**(3) 配方内编排**（`build()`）：`cmake.configure/build` → 起替身（`--ready-file` 握手，30s 超时，**进程早退立刻抛出其日志路径**，否则失败会伪装成一片超时）→ `ctest -N` 断言注册数 == 静态活跃数 → `ctest -E RestClientTest.TestRestClientGETHTTP2Code --timeout 60 --output-on-failure` → 关替身。交叉构建下 `gtest_discover_tests` 必须置 `CMAKE_GTEST_DISCOVER_TESTS_DISCOVERY_MODE=PRE_TEST`（默认 `PRE_BUILD` 会在 build 阶段执行测试程序）。

**(4) 排除口径**：只对"任何回环替身都无法提供的能力"单例排除（HTTP/2 版本协商），用 `ctest -E` 而非删用例，并在 PR 正文"未执行测试"逐项写原因；上游自带 `GTEST_SKIP()` 的 1 例沿用其判断，不改判为通过。

## 4. ★ 禁止策略（与推荐方案同等重要）★

- **禁止**用"公网可达"当作跳过整批测试的理由，也禁止 `BUILD_TESTING=OFF` / 删测试入口 / 注释 `add_test`：这类做法在本仓会被静态审查直接判测试口径不通过，且把"零覆盖"洗成"高通过率"。
- **禁止**为了让替身"看起来像 httpbin"而放宽断言或改写预期值：改的是被测环境，不是判据；一旦改判据，回归就再也抓不住。
- **禁止**把替身实现成"只回固定 200"的桩：`TestFailForInvalidCA`（要真失败）、`/redirect/N`（要真跳）、`/status/NNN`（要真回码）、`/basic-auth`（要真校验）会立刻失去意义，通过率是假的。
- **禁止**用补丁（`--- /dev/null` hunk）投递替身与证书：见 §6 第 1 条，会落到源码根目录。

## 5. 有效性判据（本机制自带的三级验收口径）

1. **注册数**：`ctest -N` 的 `Total Tests` == 按源码逐个 `TEST_F` 数出的静态活跃数。本例 26（`test_restclient.cc`）+ 22（`test_connection.cc`）+ 3（`test_helpers.cc`）= **51**；注意 `grep 'TEST_F('` 命中 52 处，其中 `ConnectionTestRemote.TestSSLCert` 在上游源码里就是注释行，不计入。配方把这条做成硬门禁（不等即 `raise`），专防"静默 0 测试"。
2. **执行/通过数**：取自同一份 ctest 汇总行，失败数必须为 0；被排除与被 skip 的用例逐项给技术原因。本轮真机读数：待 W3 完成后回填（见 `notes.md` 与 `test_package/MANIFEST.yml` 同源三处）。
3. **端点归零**：跑完后测试日志中不得再出现任何公网域名解析；TLS 用例目标是 `localhost:8999`、代理用例是 `127.0.0.1:3128`，两者都由 ready-file 与证书注入在配方内坐实。

## 6. 已尝试并失败的方案

1. **新增文件走补丁投递** —— conan 的补丁管线（patch_ng）处理"新建文件"hunk 时以 `source_folder` 为根创建路径，**不尊重头里的子目录**：`--- /dev/null +++ b/test/loopback_httpbin.py` 实际在源码根建出同名文件，`test/` 下为空，`build()` 报 `loopback stand-in exited with 2`。四种头写法（plain / `diff --git`+`new file mode` / tab 时间戳）逐一实测同结果；仓库既有配方（ada 等）的子路径新文件补丁同样不落地。**正解**：资产放配方目录 `files/`，`exports_sources = "patches/*", "files/*"`，在 `source()` 里 `copy()` 进 `test/`；补丁只保留对既有文件的修改。
2. **`refresh-patch --auto` 幂等性丢失** —— 工具的 `_dry_run()` 校验会把新建文件写进 `.orig` 基线，于是第二次 `--auto` 把它们判成"已修改"，生成 `--- a/test/...` 的错误补丁。**规避**：每次重生成前把 `.orig` 里被误写的 0 字节新文件移走（本窗暂存于 `~/tmp/uc2/TGFAT-1/orig-pollution-20260927/`），再跑 `--auto`；已复核修正后的 4 个补丁头均为 `--- a/…` 且 `strip: 1`。
3. **保留 `vendor/jsoncpp-0.10.5` 一起编译** —— 与制品仓 `jsoncpp/1.9.8` 的 CMake config 目标名冲突，`find_package(jsoncpp)` 命中 vendor 目录，测试目标链接到旧版；改为显式 `-Djsoncpp_DIR=<Conan 包>/lib/cmake/jsoncpp` 后消失。
4. **`-pr:b` 用 build 机 native profile** —— `can_run()` 为假，`build()` 只编译不执行上游套件，等于回到"0 执行"；交叉档位下把 `-pr:h` 与 `-pr:b` 同指 `ohos-aarch64`，让 ctest 在设备本机执行才是可交付口径。

## 7. 适用范围与反例（safety_boundary）

**适用**：测试源码里出现字面量公网域名、或测试目标启动即依赖某个远端服务/代理的 C/C++ 库（libcurl/c-ares 系 HTTP 客户端、REST/OAuth SDK、任何带 `squid`/`privoxy`/`httpbin`/`requestbin` 的套件）。判据：`grep -rnE 'https?://[a-z0-9.-]+\.(org|com|io)' test/` 有命中且断言直接读响应体。

**反例 / 不适用**：

- 需要**真·公网语义**的用例（HTTP/2 协商、真实 CA 链、DNS 解析失败路径 `CURLE_COULDNT_RESOLVE_HOST=6`）不能靠回环替身复刻 —— 只能像本例一样单例排除并写原因，或改断言目标（本例保留 `TestNonExistantUrl` 走真实解析失败，因为回环环境不干扰它）；
- 被测库自带 httpbin 依赖且测试**只校验语义子集之外**的字段时，替身保真成本会超过收益，此时应改测例而不是加高墙；
- 需要 mTLS/真实证书链/SNI 行为的用例，本方案只覆盖"有握手 + 可指定 CA"这一层，不覆盖链校验。

**解除条件**：若集成环境提供稳定的内网 httpbin/squid 镜像，可退回上游原生 Makefile 编排，本草稿只保留"端点常量可环境变量覆盖"这一层改造。

## 8. 与知识库既有条目的关系

- **不重复**：仓库既有条目覆盖"构建期取不到测试框架"（FetchContent 拉 googletest 一类），未覆盖"测试运行时的外部服务端"；本条是新的解题路径，且对所有 HTTP 客户端库通用（成套配送货源：同机制可派给任何打公网端点的测试套件）。
- **配合**：与"上游测试必须在 `build()` 中真实执行"这一硬规则互补 —— 那条规定口径，本条给出"看起来没环境"时的可行实现路径与其边界。
- 交叉引用（供 promote 时人工确认）：`similar_to` 暂留空，待知识图谱侧给出同族条目号。
