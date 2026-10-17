# DRAFT-14986-hiredis-1.3.0-tcp-server-prerequisite-test-partition：客户端库上游测试硬前置外部 TCP 服务时按 server 依赖二分——纯函数子集实跑 + 消费者兜底 + 阻断项定性

> Contributor: j669539 | Status: Draft | Updated: 2026-10-08
> Source: hiredis 1.3.0 适配（PR #14986，任务 #14960）；触发场景：上游 test.c 118 用例中 51 个需活的 redis-server
> 对应：`knowledge/drafts/DRAFT-14986-hiredis-1.3.0-tcp-server-prerequisite-test-partition.kv`

## 现象

客户端-服务器架构的客户端库，上游测试第一步就是 connect 服务端：

```text
#01 redisContext uses injected allocators: PASSED
...
#67 Don't fail when freeReplyObject is passed a NULL value: PASSED

Testing against TCP connection (127.0.0.1:6379):
Connection error: Connection refused
```

上游把测试包在包装脚本里（`add_test(NAME hiredis-test COMMAND test.sh)`），test.sh 先拉起 redis-server 再跑全套。OHOS CI worker 与本机均无 `redis-server`（`which redis-server` → not found）也无 redis docker 镜像。

**迷惑点（两种误判方向）**：

| 误判 | 表现 | 后果 |
|------|------|------|
| 整包套"环境限制" | "118 用例全需 server，全部跳过" | rule4 少报——67 个纯函数用例（connect 之前的无条件段）本可实跑，一个不报 |
| 只跑 test_package 冒烟 | "上游测试跑不了，消费者测试代替" | rule4 定性不完整——上游测试存在且大部分纯函数段可跑，未清点即放弃 |

## 与既有条目的不同构（查重三态）

| 既有条目 | 场景 | 与本条差异 |
|----------|------|------------|
| DRAFT-10251-libnfc-tools（configure 守卫静默排除） | 测试**根本没进构建**（TOTAL: 0） | 本条测试**存在且真实**，卡在环境硬前置 |
| E530（X11 客户端库无 X server） | 上游**无测试**，做 ABI 钉死 | 本条上游**有 118 用例**，二分后 67 个可跑 |
| E334/E357（daemon 网络探测/配置加载） | 运行期探测降级 | 本条是测试申报口径问题，非运行期行为 |

零命中：知识图谱 grep（hiredis/redis/server-prerequisite）无直接覆盖。

## 根因

上游测试形态：单一自测二进制 + 服务端前置包装脚本。`test.sh` 第一步 `redis-server redis.conf`（TCP 56379 + unix socket），CI 无该二进制则包装脚本整体失败。但 test.c 的 main() 里**连接建立之前的纯函数段是无条件执行的**——这就是可跑子集的边界。

## 方案（分层如实申报法）

1. **清点**（rule4 口径）：`grep -oE '\btest\(' test.c | wc -l`（剔除 `#define test(_s)` 宏定义行）→ 118 用例 / 22 函数。
2. **二分**：读 main() 无条件段 → allocator 注入 3 + 命令格式化 25 + 回复解析 34（含 RESP3 全类型）+ 连接错误 3 + free_null 2 = 67 个无 server 用例。
3. **纯函数子集实跑**：OHOS SDK clang 直编上游 test.c 链接 conan 产物（`clang test.c -I. -I<pkg>/include -L<pkg>/lib -lhiredis -lm`），本机 aarch64 直跑 → **#01–#67 全 PASSED（0 FAILED）**。注意 NXDOMAIN 子用例被本机 DNS 劫持跳过（上游自身打印 "Skipping NXDOMAIN test. Found evil ISP!"）——上游行为，如实记录。
4. **消费者测试兜底**（test_package）：连接失败 errno 语义 + RESP2 格式化/解析字节级 memcmp → 19 项全 PASS（conan create RC=0）。
5. **阻断项逐项定性**：51 个 server 依赖用例逐类列出 + 统一根因（无 redis-server/docker）+ 实测报错（`Connection error: Connection refused`）+ 环境限制关键词，写进 PR 统计表与 MANIFEST.yml。

## 禁止策略

- **禁止整包跳过**：67 个可跑用例一个不报 = 少报。
- **禁止 mock/stub 假 server 让 server 段"通过"**：破坏上游测试原始性，掩盖协议差异。
- **禁止虚报 100%**：server 段 51 用例未跑不计入通过。

## 验证

```bash
cd archives/h/hiredis/1.3.0 && conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# RC=0，test_package 19 项消费者测试全 PASS
# 纯函数子集：上游 test.c 实跑 #01–#67 全 PASSED 后停在第一个 connect（预期失败点）
```

本题实证：PR #14986（hiredis 1.3.0，任务 #14960），上游 67/67 纯函数 PASS + 消费者 19/19 PASS + 51 项环境限制如实申报；本地 L0-L5 门禁 100% 通过。

## 适用范围

所有客户端库（hiredis/libmemcached/rabbitmq-c/paho-mqtt/libpq 等）及任何 `add_test` 的 COMMAND 是"先起 daemon 再跑"包装脚本的测试套件。
