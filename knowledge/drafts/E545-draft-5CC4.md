# E545 — 上游回调缺 `msg == NULL` 守卫：查询失败变成崩溃，测试汇总行随之消失

## 错误特征

同一条用例，在两台真实鸿蒙机器上呈现两种完全不同的失败形状。CI worker 上它直接崩
（下面逐字照抄 CI #36823 日志，`conan create` 于 2026-09-02）：

```
fossa/2.1: $ (cd .../b/test && MallocLogFile=/dev/null ./unit_test test_dns_resolve)
oSignal 11 (core dumped)
fossa/2.1: ERROR:
oPackage '4b977264131a1c74e82bd6bb51b63cc9aadc4cfa' build failed
oERROR: fossa/2.1: Error in build() method, line 228
o       self._run_upstream_tests(test_dir)
owhile calling '_run_upstream_tests', line 172
o       matrix = self._measure_upstream(test_dir)
owhile calling '_measure_upstream', line 135
o       ran, status, total = self._run_unit_test(test_dir, case)
owhile calling '_run_unit_test', line 112
o       raise ConanException(f"unit_test {case}: 框架汇总行缺失，无法取得真实用例数")
```

注意崩溃那一行的输出里**只有 `Signal 11`，没有 `[RUN]` 计时行、也没有
`PASS/FAIL, run N`**。这是判据所在：计时行由 `RUN_TEST` 在 `test()` **返回之后**
打印（`test/test_util.h:57`），汇总行由 `main()` 在 `run_tests()` 返回之后打印
（`test/unit_test.c:3250`）。崩溃发生在 `test()` 内部 ⇒ 两行都到不了，
任何按汇总行取数的逐用例度量都拿不到值。

开发用真机上同一条用例是**干净失败**（E544 已归因）：

```
$ ./unit_test test_dns_resolve
2.000000 != 1.000000
unit_test.c:2705:1 [data == 1] (in test_dns_resolve)
FAIL, run 1 in 0.014s
```

⇒ 判据：**「崩溃」与「失败」在同一段代码里由外部服务是否给出应答决定**。
只看到其中一种形状的机器会以为问题不存在，或者以为已经归因完了。

## 触发条件

- 构建系统: 任意（`make` / `conan create` / CI 均可复现，与构建无关）
- 阶段: testing（运行期缺陷，编译期零信号）
- 高发对象: 使用「带可空消息指针的回调」API 的上游自测代码 ——
  异步 DNS、异步连接、任何 `cb(struct xxx_message *msg, void *data)` 形状
- 触发环境: 外部 DNS / 外部服务**给不出可用应答**时（NXDOMAIN 且 `num_answers == 0`、
  超时、重试耗尽、被防火墙拦掉、CI 网络与开发机网络不同）

## 根因分析

完整因果链，逐行核对自官方归档 `2.1.tar.gz` 的未改动源码：

1. 库按约定在失败时以 `NULL` 调用注册回调 ——
   `fossa.c:7068`（`req->retries > req->max_retries` 重试耗尽）与
   `fossa.c:7084`（`NS_RECV` 里 `num_answers > 0` 不成立，包括真 NXDOMAIN 的空应答）
   两处都是 `req->callback(NULL, req->data);`。**这是库的公开契约，不是异常路径。**
2. 上游测试回调 `dns_resolve_cb`（`test/unit_test.c:2669`）没有 `msg` 判空，
   第一个动作就是 `ns_dns_next_record(msg, ...)`（`:2675`）。
3. `ns_dns_next_record` 无条件解引用：
   `for (rr = (prev == NULL ? msg->answers : prev + 1); rr - msg->answers < msg->num_answers; rr++)`
   （`fossa.c:6510`）⇒ 读地址 0 的偏移 ⇒ `SIGSEGV`。
4. 进程死亡早于汇总行打印 ⇒ 度量拿不到数，配方按设计抛
   `ConanException` 让构建立即失败（这一步是**唯一做对的事**：它把崩溃暴露成
   构建失败，而不是伪造一个数字）。

**关键判别：姊妹回调对照。** 同一文件里
`dns_resolve_timeout_cb`（`test/unit_test.c:2711`）签名完全相同，且自己就写了：

```c
static void dns_resolve_timeout_cb(struct ns_dns_message *msg, void *data) {
  if (msg == NULL) {
    *(int *) data = 1;
  }
}
```

⇒ `msg` 可空是上游作者已知的事实，只是漏在了 `dns_resolve_cb` 上。
这一步把问题从「鸿蒙上 DNS 崩了（平台锅）」精确改写成「上游漏了一个守卫（上游锅）」。

**现场 A/B（不依赖主机探针即可定责）**：CI #36823 的日志里，同一次构建、同一网络条件下
两条相邻命令给出了相反结果 ——

```
$ (cd .../b/test && MallocLogFile=/dev/null ./unit_test test_dns_resolve_timeout)
  [0.015] test_dns_resolve_timeout
PASS, run 1 in 0.015s
$ (cd .../b/test && MallocLogFile=/dev/null ./unit_test test_dns_resolve)
Signal 11 (core dumped)
```

带守卫的走 `msg == NULL` 分支 ⇒ 正常 `PASS, run 1`；无守卫的同一入口 ⇒ 崩溃。
注意 `test_dns_resolve_timeout` 用的是上游自带的死 resolver 惯用法
（`opts.nameserver_url = "udp://7.7.7.7:53"; opts.timeout = -1; opts.max_retries = 1;`，
`unit_test.c:2726-2728`），**必然**以 `msg == NULL` 收尾，与外网是否可达无关；
所以这里的差异不是网络条件的巧合，唯一变量就是那条守卫，归因在设备日志内部即已闭合，
第 3 步的主机 A/B 只是可移植的复现手段。

**同一函数里的第二条独立缺陷**（顺手一起修，别让它藏在第一条后面）：
`cname[256]` 与 `got_addr` 只在对应记录存在时才被写入，而判定式无条件读它们 ——
`strcmp(cname, "dev.cesanta.com")` 读未初始化栈内容、
`want_addr == got_addr.s_addr` 读未初始化结构体（`unit_test.c:2671-2689`）。
这是 `ns_dns_parse_record_data` 未命中时的未定义行为，**可能让断言偶然通过**。
因此补丁同时 `memset` 两个局部量。

**为什么开发机把这条完全掩盖了**：该网络接的运营商 resolver 对带点的不存在域名
做泛解析，合成一条 `198.18.0.0/15` 应答（见 E544）⇒ `num_answers > 0` ⇒
`msg != NULL` ⇒ 崩溃分支永远走不到。也就是说**环境越"坏"，这个上游缺陷越隐身**；
只有在给出真 NXDOMAIN 或无应答的环境（CI）上才暴露。这是「一处缺陷、两种症状」的
典型形态。

## 解决方案

### 推荐方案：姊妹回调对照 + 离线死地址 A/B 探针 + 最小平台中立守卫

1. **先对照，再动手**：在崩溃文件里 `grep -n "if (msg == NULL)"`，找同签名回调。
   找到 ⇒ 上游遗漏，可写守卫并可向上游提交（P005）；找不到 ⇒ 需要自己确认库的契约，
   去库里 `grep -n "callback(NULL"` 数出所有以 NULL 调用的位置。
2. **守卫置成"该函数已有的错误分支值"**，不要置成成功值，也不要新增状态码：
   `dns_resolve_cb` 的失败分支本来就是 `*(int *) data = 2; /* Error */`，
   所以 `msg == NULL` 也置 `2`。修改后该用例退化成一次**正常的断言失败**
   （`2 != 1`），与真机上观察到的形状一致 ⇒ 两台机器口径统一。
3. **用上游自己的死地址写法做离线复现**，不要依赖外网：
   `test_dns_resolve_timeout`（`unit_test.c:2719`）里
   `opts.nameserver_url = "udp://7.7.7.7:53"` + `timeout = -1` + `max_retries = 1`
   是上游自用的「必然无应答」写法（`:2726-2728`）。
   在探针里换成 `udp://127.0.0.1:9`（discard 端口，必然无应答）更稳，因为
   有的网络会劫持 53。把崩溃体与修复体编到同一个二进制里用参数切换，
   就能在同一台机器上给出 4/4 可重复的 A/B：

   ```
   variant=U ->    rc=139                 # 逐字复制的上游回调
   variant=G -> PROBE variant=G data=2 polls=3
      rc=0                                # 加上守卫
   ```

4. **守卫只在 `msg == NULL` 时生效**，因此在「总能拿到应答」的机器上语义严格不变，
   原矩阵数字可以直接沿用；`memset` 一条则收紧了「偶然通过」的可能，属于修正而非改写。

### 回退方案：runner 侧分离「崩溃」与「失败」并重算矩阵

不改上游源码时，按退出码把该用例单列 `crashed`，既不计 `passed` 也不计 `failed`、
更不塞进 `skipped`，矩阵按剩下的用例重算，并附探针步骤记为上游缺陷。
代价是永久丢掉这条覆盖，因此只作为无法提交守卫时的降级。

### 禁止做法

- ❌ 把「没有汇总行」读成 `run 0` 或 `except: pass` 后继续 —— 崩溃与 0 断言空壳
  用例（fossa 里 `test_dns_uncompress`、`test_dns_decode_truncated` 真是 0 断言）
  会被压成同一个数字，缺陷和覆盖损失一起消失。
- ❌ 把 `Signal 11` 归成「环境限制 / DNS 不稳定」然后跳过。它不是环境限制，
  是可达的 NULL 解引用；这样写的报告等于替上游把 bug 藏起来。
- ❌ 用 `#ifdef __OHOS__` 包守卫（违反 PF5/R8）。崩溃与平台无关，守卫也必须无关。
- ❌ 靠调大 `timeout` / 加重试 / 换 DNS 让它"别崩"。这只改变是否进入 NULL 分支。

## 验证

```sh
# 1) 契约确认：库确实以 NULL 调用回调，且被无条件解引用
grep -n "req->callback(NULL" fossa.c                    # 期望恰好 2 处: 7068, 7084
grep -n "prev == NULL ? msg->answers" fossa.c           # 期望 6510（循环初始化即解引用）

# 2) 姊妹回调对照（决定是上游锅还是平台锅）
grep -n "if (msg == NULL)" test/unit_test.c     # 期望命中 dns_resolve_timeout_cb

# 3) 离线 A/B，不需要外网
./probe U udp://127.0.0.1:9 ; echo rc=$?        # 期望 rc=139，且无 stdout
./probe G udp://127.0.0.1:9 ; echo rc=$?        # 期望 data=2，rc=0

# 4) 端到端：修复后汇总行必须回来，且退化点与真机一致
./unit_test test_dns_resolve      # 未打补丁构建: FAIL, run 1 at unit_test.c:2705
                                  # 打了 0002 的构建: 同一断言行位移到 unit_test.c:2721
```

本条正文引用的行号一律以**未改动的官方归档**为准；补丁 0002 在 `unit_test.c:2673`
之后插入 16 行，插入点之后的行整体 **+16**（`ns_dns_next_record` 调用 `:2675`→`:2691`、
成功判定 `:2689`→`:2705`、`ASSERT_EQ` `:2705`→`:2721`）。
所以看到 `2721` 不代表断言变了，只是行号位移；对照时不要拿打过补丁的构建去比首次归因记录。

第 4 步是主判据：**只要该用例不再打印 `PASS/FAIL, run N`，守卫就没生效**
（或者 `msg` 从另一条路径进来）。如果它变成 `PASS`，说明本机又拿到了可用应答，
不能据此判定修复无效 —— 必须回到第 3 步的离线 A/B 上确认。

## 关联条目

- 相关: E544（同一条用例的**另一种**失败形状：泛解析环境把它压成干净 FAIL，
  本条补的是「无应答 ⇒ 崩溃」一侧；两条合起来才是完整的跨环境归因）、
  E338（同类「外部 API 返回 NULL 被无条件解引用 ⇒ SIGSEGV」，处置同样是补判空，
  只是它按平台差异给了 `__OHOS__` 回退路径）、
  E040（man-db `get_man_owner()` 返回 NULL 被直接解引用 —— 同族且更早；差别在那条走
  `config-patch`，在 `config.h` 里取消 `MAN_OWNER` 从配置层让 NULL 不再出现，
  而本条的 NULL 是库公开契约内的正常失败输入，只能在调用点补守卫，且守卫必须平台中立），
  E462（OHOS 上 `ptrace` 被拦、ASan 可能静默时的崩溃定位手法 —— 本条不需要它，
  因为在 CI 日志里崩溃与用例行已经紧邻）、
  E429（逐用例断言度量的无重复计数，正是它要求「拿不到汇总行就失败」从而暴露了本条）
- 适用原则: P005（补丁必须可向上游提交 —— 守卫无平台宏、英文注释、复用上游自己的分支值）
- 适用铁律: R9（FAIL 禁止标 success；崩溃更不是 success）、R8（不在补丁里新增平台宏）

## 来源

- 软件/版本: fossa/2.1（`archives/f/fossa/2.1`，`patches/0002-test-unit_test.c.patch`）
- 上游: https://github.com/cesanta/fossa `fossa.c:6510`、`:7068`、`:7084`；
  `test/unit_test.c:2669`、`:2675`、`:2689`、`:2705`、`:2711`、`:2719`、`:2726-2728`、`:3250`；
  `test/test_util.h:50`（`RUN_TEST`）与 `:57`（计时行）
- 实测: CI #36823 失败（ohos-aarch64 worker，崩溃）/ CI #36830、#36835 通过（同 worker 群，补丁后）。
  通过轮的机器人评论只逐项报告 `Conan test_package` / `L0 门禁（结构完整性）` /
  `L1 门禁（测试执行验证）` 三项，不含 L2 项；且评论正文不写被构建的 SHA，
  「构建号 ↔ 提交」只能按 `/rebuild` 触发顺序推定（完整日志需外网权限，本地抓取被拦截）。
  开发真机 aarch64 干净 FAIL；离线 A/B 见 `probe_dns_null.c` 采集记录（主机控制实验）
- 记录人: Awstme <awstme@qq.com>，2026-09-02
