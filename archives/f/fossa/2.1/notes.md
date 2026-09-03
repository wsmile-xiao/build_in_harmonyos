# fossa 2.1 适配笔记

## 编译环境
- 构建系统: makefile（上游 `test/Makefile`）+ 单文件合并产物直接编译
- 编译日期: 2026-09-02
- 编译器: clang / llvm-ar（由 `tools.build:compiler_executables` 取得，R33）
- 状态: built

## 上游识别

Fossa 是 Cesanta 的 C/C++ 异步网络库（HTTP/WebSocket/MQTT/CoAP/DNS 共用一个
event manager），后来并入 Mongoose 6+。与 `archives/m/mongoose/7.21` 同族，
符号前缀为 `NS_*`。

注意与同名项目区分：FOSSA 许可证合规 CLI、Kevin Warren 的音频插件 SDK 均非本库。

## 编译步骤

```bash
# 1. 官方归档（R39）
curl -fsSL https://github.com/cesanta/fossa/archive/refs/tags/2.1.tar.gz -o fossa-2.1.tar.gz
shasum -a 256 fossa-2.1.tar.gz
# 59163a01d876324eaad81638b15c00e5bb48b737a264c4d46f892720ca0a7cb4

# 2. 静态库（与 mongoose 同法，直接编译合并产物）
clang -O2 -fPIC -DNS_ENABLE_COAP -DNS_ENABLE_IPV6 -DNS_ENABLE_THREADS \
      -DNS_ENABLE_MQTT_BROKER -DNS_ENABLE_DNS_SERVER -c fossa.c -o fossa.o
llvm-ar rcs libfossa.a fossa.o

# 3. 上游单元测试（test/Makefile，-j1；打补丁后默认配置不再需要 -lssl）
make -C test -j1 unit_test CC=clang CFLAGS_EXTRA=-DTEST_UNDER_VIRTUALBOX
MallocLogFile=/dev/null ./unit_test <TEST_FILTER>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接期 `ld.lld: unable to find library -lssl` | 上游 `test/Makefile` 无条件链接 `-lssl`，而默认测试构建不定义 `NS_ENABLE_SSL`、不含任何 TLS 代码；CI 环境无 OpenSSL 开发文件（设备上的 `~/.harmonybrew` 属用户级，不可复现） | 补丁 `0001-test-Makefile.patch`：仅当 `NS_ENABLE_SSL` 出现在 `CFLAGS` 中时才追加 `-lssl`。单一开关、不引入平台宏、可直接上游 |
| 2 | `test_http_errors` 期望 chmod 000 文件返回 HTTP 500，真机返回 200 | HMDFS 忽略 chmod：`chmod 000` 后仍是 `-rw-r-----`，`fopen` 仍成功（真机实测） | 用上游自带的 `TEST_UNDER_VIRTUALBOX`（专为文件系统权限语义不可靠的环境提供）经 `CFLAGS_EXTRA` 传入，零源码改动 |
| 3 | 全量跑一次只能得到第一个失败（`FAIL, run 247 in 10.692s`） | 上游 `RUN_TEST` 宏末尾 `if (msg) return msg;`，首个失败即中断整个进程 | `build()` 逐用例驱动，把用例名当作 `TEST_FILTER` |
| 4 | 逐用例跑后直接求和会虚高（789 vs 669） | `RUN_TEST` 用 `strstr(#test, filter)` 匹配，短名字过滤器会连带跑所有包含它的长名字用例 | 按名字长度**降序**遍历过滤器：一次 run 额外重跑的只会是该用例的长名字超串，而超串的断言数已先行测得，减去即得该用例真实值；配方对「重复归因／归因为负／判定被截断」三类不一致一律报错，不允许静默给出失真数字 |
| 5 | 分模块构建不可用 | tarball 缺 `common/` 与 `deps/frozen`，而 `src/modules.mk` 的 HEADERS/SOURCES 指向它们 | 只能使用上游已合并好的 `fossa.c`/`fossa.h`；`test/unit_test.c → src/internal.h → ../fossa.h` 链路完整，测试可独立构建 |
| 6 | 共享库交付 | OHOS 用户态 `.so` 需 ELF 签名（同族 mongoose 已确认同一限制） | 只交付静态库，`validate()` 显式拒绝 `shared=True` 并说明原因 |
| 7 | CI 里 `./unit_test test_dns_resolve` 直接 `Signal 11 (core dumped)`，没有汇总行，配方按设计报「汇总行缺失」并让构建失败 | 上游 `dns_resolve_cb`（`unit_test.c:2669`）没有 `msg == NULL` 守卫，而 `ns_dns_next_record()` 无条件解引用 `msg`（`fossa.c:6510`）。解析失败或应答 0 条时 `ns_resolve_async_eh()` 会以 `callback(NULL, ...)` 收尾（`fossa.c:7068`、`:7084`）。CI 拿不到可用应答（NXDOMAIN 时 `num_answers == 0`，无应答时重试耗尽，两条路径都走 `callback(NULL, ...)`）⇒ `msg == NULL` ⇒ 崩溃；真机上该名字被运营商泛解析合成为 198.18.6.164，`msg != NULL`，所以只表现为断言失配，掩盖了这个缺陷。同一文件里上游自己的 `dns_resolve_timeout_cb`（`:2711`）就带该守卫，且 `test_dns_resolve_timeout` 用 `udp://7.7.7.7:53` 专测这条 NULL 路径并在两边都通过 | 补丁 `0002-test-unit_test.c.patch`：补上游同款 NULL 守卫（按既有语义置 `data = 2` 表示 Error），并把只在「命中对应记录」时才写入的 `cname`/`got_addr` 两个局部变量初始化，消除同函数内的未初始化读取。不触碰任何断言与期望值、不含平台宏，可直接上游 |

## 源码修改

- `patches/0001-test-Makefile.patch`（`ohc-run.py refresh-patch --auto` 生成，
  `patch --dry-run -p1` 通过；原始 tarball + 补丁 == 修改后源码树，已逐字节比对）
  - `test/Makefile`：`-lssl` 改为条件链接
- `patches/0002-test-unit_test.c.patch`（复用 `scripts/ohc/refresh_patch.py` 的同一代码路径
  生成：`_diff_files` difflib、10 行上下文、per-file 命名；`_validate_patch_format` 与
  `_dry_run` 通过，`patch -p1` 实打后与预演文件逐字节一致。
  同时把 `test/unit_test.c` 登记进 work dir 的 `.edit-tracker.json`，
  使后续 `refresh-patch --auto` 能原地重生成同一组补丁 —— 已验证 0001 重生成结果与仓库现有内容逐字节相同）
  - `test/unit_test.c`：`dns_resolve_cb` 补 `msg == NULL` 守卫 + 初始化 `cname`/`got_addr`

补丁只落在 `test/` 下，库自身的 `fossa.c`/`fossa.h` 一个字节未改。两处改动均不含
`__OHOS__` 等平台宏（R8/PF5），均不修改任何断言表达式或期望值，可直接提交上游；
0002 修的是上游测试回调的 NULL 解引用，与鸿蒙无关，任何解析失败的网络都会命中。

## 依赖版本

无 Conan 依赖。合并产物只 `#include "fossa.h"`，尖括号包含仅
`<assert.h> <stdarg.h> <stdio.h> <stdlib.h> <string.h> <sys/epoll.h>`；
无 zlib/frozen/cares，OpenSSL 只在默认关闭的 `NS_ENABLE_SSL` 下需要。
运行期只需系统 pthread（`NS_ENABLE_THREADS`）。

## 关键打包决策：`NS_ENABLE_IPV6` 是 ABI 宏

`fossa.h:537`：

```c
#ifdef NS_ENABLE_IPV6
  struct sockaddr_in6 sin6;
#else
  struct sockaddr sin6;
#endif
};
```

`union socket_address` 的布局随该宏改变。消费者若不带此宏编译，就会以与库不一致
的结构体大小访问内存。因此配方把编进库的特性宏通过 `self.cpp_info.defines` 下发；
`test_package/test.c` 的 `test_socket_address_layout()` 直接写
`sa.sin6.sin6_family = AF_INET6`，宏不下发就编译不过，从而把这条契约钉住。

## 验证结果

### 上游测试（真机）

- 源码注册用例 60，其中 `test_ssl`、`test_modern_crypto` 位于
  `#ifdef NS_ENABLE_SSL` 内、本配置未编入二进制 → `skipped=2`
- 实跑 58：PASS 55 / FAIL 3，断言合计 669（逐用例矩阵与
  `HMBS_UPSTREAM_TEST_RESULT` 见 `conan create` 日志）
- 真机 `conan create`（提交 `ed43e904ab`，profile `ci/conan/profiles/ohos-aarch64`，
  `--build=missing --build="fossa/*"`）退出码 0；矩阵 58 条逐项求和 == 669 且无重复，
  已与日志逐字节比对一致；与 `5ecc979aea` 那次的矩阵 `diff` 无差异（结论可复现）
- 交付产物实测：`libfossa.a` 139968 字节、ELF Machine AArch64、
  102 个全局 `T ns_*` 导出符号（另有 19 个 `t` 型内部符号，归档内已定义符号共 189）
- `test_dns_uncompress`、`test_dns_decode_truncated` 在矩阵中记 **0 断言**：上游把这两
  个用例体写成 `#if 1 return NULL; #else ...`（`unit_test.c:2256`、`:2379`），
  属上游自带的空壳用例，不是本配方跳过，也不是被更早的失败截断
- 3 个失败均归因到「工具未装 / 环境限制」，与 fossa 代码及适配层无关：
  - `test_cgi`：设备 perl 5.44 无 CGI.pm（CGI 自 Perl 5.22 起移出核心），
    `test/data/cgi/index.cgi` 报 `Can't locate CGI.pm in @INC ... at index.cgi line 4`，
    上游注释亦标明 `Needs perl interpreter to run the test`
  - `test_connection_errors` / `test_dns_resolve`：运营商 resolver
    （114.114.114.114）对不存在域名做泛解析，合成 RFC 2544 基准测试段地址
    （`does.not.exist` → 198.18.6.163、`oncall.cesanta.com` → 198.18.6.164）
    并有透明代理接受任意端口；前者期望连接失败却成功（`ASSERT_EQ(data, 4)`
    拿到 1），后者固定比对 2015 年抓取的真实应答 52.16.170.74 /
    CNAME `dev.cesanta.com`，在任何非原始 DNS 环境下都不可能匹配
  - resolver 机制本身健康：`test_dns_resolve_hosts`、`test_dns_resolve_timeout`、
    `test_dns_server`、`test_dns_encode`、`test_dns_decode`、
    `test_dns_reply_encode` 全部通过
- 白名单之外的任何失败都会让 `build()` 直接报错，环境受限用例无法掩盖真实回归

### 消费端（test_package）

4 个用例 15 条断言：base64 编解码、`ns_get_http_var`、
`union socket_address` IPv6 布局，以及在 127.0.0.1 上完成一次真实 HTTP
请求/响应往返，证明交付的 `libfossa.a` 事件循环与 HTTP 协议处理器在真机可用。

## 交付物

| 文件 | 说明 |
|------|------|
| `include/fossa.h` | 合并后的单一头文件 |
| `lib/libfossa.a` | 静态库，含 COAP/IPV6/THREADS/MQTT_BROKER/DNS_SERVER 特性 |
| `licenses/LICENSE` | GPL-2.0-or-later（上游另有 Cesanta 商业双许可） |

## 注意事项

- 只交付静态库；`-o shared=True` 会被 `validate()` 拒绝并给出平台原因说明。
- 消费方不得自行增删特性宏，尤其 `NS_ENABLE_IPV6`，否则与已编译的 `libfossa.a`
  布局不一致；配方已通过 `cpp_info.defines` 下发正确取值。
- `NS_MALLOC/NS_CALLOC` 覆盖、`NS_MODULE_LINES`、`-include unit_test.h` 只属于
  上游测试构建，不进入库的编译参数。
- 本库上游已停止维护（2.1 为最后一个 release），需要 TLS 的场景应转向 mongoose；
  此处不提供 SSL 变体。

---

**编译结束**: 2026-09-02 18:06
**最终状态**: built（真机 aarch64 静态库编译、逐用例上游测试矩阵与 test_package HTTP 往返通过；3 个失败为环境/工具限制，见「验证结果」）

