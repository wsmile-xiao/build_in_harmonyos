# E544 — 运营商泛解析与透明代理使「期望解析/连接失败」类断言必然失败

## 错误特征

同一测试二进制里，只有依赖外部 DNS 语义的用例失败，且失败方向是**期望失败反而成功**
（鸿蒙真机实测，逐字照抄）：

```
$ ./unit_test test_connection_errors
1.000000 != 4.000000
unit_test.c:438:1 [data == 4] (in test_connection_errors)
FAIL, run 11 in 1.048s

$ ./unit_test test_dns_resolve
2.000000 != 1.000000
unit_test.c:2705:1 [data == 1] (in test_dns_resolve)
FAIL, run 1 in 0.014s

$ nslookup does.not.exist
Name:	does.not.exist
Address: 198.18.6.163

$ nslookup oncall.cesanta.com
Name:	oncall.cesanta.com
Address: 198.18.6.164
```

## 触发条件

- 构建系统: 任意（与构建无关，属运行期网络语义）
- 阶段: testing / runtime
- 高发对象: 期望 NXDOMAIN、期望 `ECONNREFUSED`/连接失败、期望解析超时，
  以及把某次真实外网应答硬编码成期望值的用例

## 根因分析

两条**互相独立**的机制，必须分开归因，不能笼统写成「DNS 不稳定」：

1. **泛解析 + 透明代理**（`test_connection_errors`）。设备所接运营商 resolver
   （114.114.114.114）对不存在域名不做 NXDOMAIN，而是合成 RFC 2544 基准测试段
   （`198.18.0.0/15`）地址；链路上的透明代理再 accept 任意端口的连接。
   用例期望 `ns_connect_opt("tcp://does.not.exist:8080")` 异步失败，
   其回调语义是「成功置位 1、失败置位 4」（`unit_test.c:389-399`），
   实测拿到 `1` ⇒ 连接**真的成功了**，于是 `ASSERT_EQ(data, 4)`（`:438`）失败。
2. **期望值绑死历史真实应答**（`test_dns_resolve`）。回调把成功条件写死为
   `want_addr == inet_addr("52.16.170.74")` **或** `cname == "dev.cesanta.com"`
   （`want_addr` 在 `:2673`，判定在 `:2689`）。泛解析合成的应答既不是那个 A、
   也不带那个 CNAME（实测只返回 `198.18.6.164`，无 CNAME），于是 `data = 2`
   ⇒ `ASSERT_EQ(data, 1)`（`:2705`）失败。这一类即使网络「正常」也会因 CDN/
   应答变化而失败，与解析成败无关。

共同点：两条都不是移植缺陷、不是库的 bug，而是断言所依赖的**外部环境语义前提**
在本机所接网络上不成立。换 resolver、换网络只能碰运气，任何此类环境下跑
「期望失败」的用例都会同样失败。

**判别细节**：泛解析只对**带点**的名字合成应答，单标签名字仍返回真正的 NXDOMAIN：

```
$ nslookup please_dont_name_a_host_like_ths
** server can't find please_dont_name_a_host_like_ths: NXDOMAIN
$ nslookup a-nope.invalid-5cc4.example
Address: 198.18.6.169
```

这正是同一二进制里 `test_resolve`（负向断言用的是单标签名）通过、
而 `test_connection_errors`（`does.not.exist` 带点）失败的分界。
⇒ 归因时不能只看「是不是一条负向 DNS 用例」，必须看它用的名字形状与断言前提。

## 解决方案

### 推荐方案：逐条归因 + 保留在失败矩阵 + 白名单外一律报错

1. **反证定位**：先跑同一二进制中**不依赖外部 resolver「应答失败」语义**的同类用例
   （纯编解码、本地内置 server、本地 hosts、超时路径、单标签名），确认解析功能本身没坏。
   实测这 7 条全部 PASS，且逐条断言数与矩阵中的 own 值一致：

   ```
   test_dns_resolve_hosts     PASS, run 3     test_dns_encode        PASS, run 24
   test_dns_resolve_timeout   PASS, run 1     test_dns_decode        PASS, run 17
   test_resolve               PASS, run 3     test_dns_reply_encode  PASS, run 15
   test_dns_server            PASS, run 21
   ```

   失败面因此精确落在「外部 DNS 应答语义」而非库代码。
2. **白名单只放行已归因用例，其余失败一律让构建立即失败**：

   ```python
   KNOWN_ENV_FAILURES = {
       "test_connection_errors": "环境限制：泛解析 + 透明代理，本应失败的连接反而成功",
       "test_dns_resolve":       "环境限制：期望值绑死 2015 年抓取的真实应答",
   }
   unexpected = [c for c in failed_cases if c not in KNOWN_ENV_FAILURES]
   if unexpected:
       raise ConanException(f"未归因的上游测试失败: {unexpected}")
   ```

3. **失败照常计入矩阵**：`failed` 里保留这两条、`status` 记 `partial`，
   不改成 passed、也不塞进 skipped。评审因此能看到
   「58 实跑 / 55 通过 / 3 环境失败 / 2 未编入」的完整事实而不是一个绿勾。

### 回退方案：把负向路径搬到可控环境

确需验证负向分支时，指向 127.0.0.1 上的测试 server 或本地 hosts，
而不是修改上游期望值；改过之后不得再称其为「上游测试」。

### 禁止做法

- ❌ 删用例、注释断言、整组 skip —— 真实回归与环境问题一起消失，评审无法区分（亦违反 R9）。
- ❌ 只写「已知问题／与本次适配无关」而不给机制与实测输出。
- ❌ 在配方里改 `resolv.conf`、注入公网 DNS 或指定外部 DNS 去凑通过：
  CI 环境不重现，且共享设备环境不该被单个包改写。
- ❌ 把两条机制合并成一句「DNS 不稳定」——归因粒度过粗等于没归因。

## 验证

```sh
nslookup does.not.exist         # 返回 198.18.0.0/15 段地址 ⇒ 泛解析命中
nslookup a-nope.5cc4.example    # 带点的假域名同样被合成 ⇒ 泛解析只认带点名字
nslookup please_dont_name_a_host_like_ths   # 单标签 ⇒ 真 NXDOMAIN
./unit_test test_dns_resolve_hosts   # 反证：不依赖外部应答语义 ⇒ PASS
./unit_test test_dns_resolve         # 归因成立时应稳定 FAIL 于 unit_test.c:2705
./unit_test test_connection_errors   # 归因成立时应稳定 FAIL 于 unit_test.c:438
```

两条 FAIL 的行号必须与上面一致：如果行号变了或失败面扩大到反证集合，
说明环境或上游代码变了，原有归因作废，需重新定位而不是继续放行。

**行号口径（重要，否则会误判成「归因失效」）**：本条引用的行号一律以
**未改动的官方归档** `2.1.tar.gz` 为准。本包另打了
`patches/0002-test-unit_test.c.patch`，它在 `unit_test.c:2673` 之后插入 16 行，
因此插入点之后的行整体 **+16**：

| 断言 | 未打补丁 | 打了 0002 |
| --- | --- | --- |
| `test_dns_resolve` 的 `ASSERT_EQ(data, 1)` | `:2705` | `:2721` |
| `dns_resolve_cb` 的 `if (want_addr …)` 判定 | `:2689` | `:2705` |
| `test_connection_errors` 的 `ASSERT_EQ(data, 4)` | `:438` | `:438`（不受影响） |

⇒ 校验时先看用的是哪个构建：报 `2721` 与报 `2705` 都可能是正确的，
差别只在有没有打 0002；`438` 则两边都必须一致。

## 关联条目

- 相关: E265（OHOS 上跑上游测试的环境差异处理：`/tmp` 只读、缺工具、shell/locale 不同，
  且明确「无 valgrind 不能伪造 valgrind 通过」—— 本条补的是它未覆盖的**网络应答语义**一侧）、
  E046 / E479（同一族「环境语义前提在本平台不成立」问题 —— HMDFS 的 `chmod`
  只加不减，处置同为降级 + 归因而非绕过）、E429（同批 fossa 草稿：断言数的无重复度量）
- **必读配对**: E545（同一条 `test_dns_resolve` 在「给不出可用应答」的环境里不是干净
  FAIL 而是 `Signal 11`，因为上游回调缺 `msg == NULL` 守卫。泛解析环境恰好总能给出
  应答，因此**把这条上游缺陷完全掩盖掉了**。只在泛解析机上做过归因就写下「环境限制」
  是不完整的：换到真 NXDOMAIN 的环境，同一用例的表现会换一种形状，
  且失败原因从「外部语义前提不成立」变成「上游代码 bug」）
- 适用原则: P013（平台限制必须降级而非绕过）
- 适用铁律: R9（质量门禁 FAIL 禁止标 success）

## 来源

- 软件/版本: fossa/2.1（`archives/f/fossa/2.1`，`KNOWN_ENV_FAILURES`）
- 上游: https://github.com/cesanta/fossa `test/unit_test.c:389`、`:438`、`:2673`、`:2689`、`:2705`
- 实测: 鸿蒙真机 aarch64（hmdfs、clang 15.0.4），2026-09-02
