# hiredis 1.3.0 适配笔记

## 编译环境

- 构建系统: CMake（上游 CMakeLists.txt，CMAKE_MINIMUM_REQUIRED 3.7.0）
- 编译日期: 2026-10-08
- 编译器: clang 15（OHOS SDK, aarch64-linux-ohos）
- 状态: published（conan create 全绿：包构建 + test_package 19 项消费者测试全 PASS）
- 任务: 平台任务 #14960（hiredis 1.3.0，taskBranch=feat/hiredis-1.3.0）

## 软件说明

hiredis 是 Redis 官方最小化 C 客户端库。本件为升级件：main 已有
archives/h/hiredis/1.2.0（同树旧版本），本次升级到 1.3.0 归档
archives/h/hiredis/1.3.0，1.2.0 保持不动。

零第三方运行时依赖（ssl/event 组件未启用；adapters/ 为纯头文件）。
下游 redis-plus-plus 依赖本件，1.3.0 出包后可解锁其 SSL/新版特性适配。

## 构建配置

- DISABLE_TESTS=ON（打包不构建 add_test——test.sh 需要真实 redis-server）
- ENABLE_SSL/SSL_TESTS/ASYNC_TESTS/EXAMPLES/NUGET 全 OFF
- 零源码补丁（1.3.0 的 CMake minimum 3.7.0 无 CMake 4.x 兼容问题，
  1.2.0 时代的 cmake_minimum_required(3.0.0) 正则补丁不再需要；OHOS 走
  POSIX 常规路径，sockcompat.h 无需平台补丁）

## R51 上游测试清点与结果申报（rule4 口径）

上游测试形态：单一自测二进制 test.c（118 个 test() 用例，22 个 test_
函数），CMake 注册 `add_test(NAME hiredis-test COMMAND test.sh)`；
test.sh 起真实 redis-server（TCP 56379 + unix socket + 可选 TLS 56443）
后跑全套。上游 CI（test.yml）用 redis:alpine docker。

实测（本机 aarch64 OHOS 环境，用 OHOS SDK clang 交叉编译 test.c 链接
conan 构建的 libhiredis.a 后直接运行）：

| 类别 | 数量 | 结果 |
|------|------|------|
| 无 server 纯函数用例 | 67 | **67/67 PASS** |
| 需真实 redis-server | 51 | 环境阻断（CI/本机均无 redis-server/docker） |

67 个构成明细（实测运行日志 #01-#67 连续编号）：
- test_allocator_injection：3（#01-#03）
- test_format_commands：25（#04-#28；15 个 test() 调用点 + printf-delegation
  宏 10 个整数/浮点变体展开计数——上游宏 INTEGER_WIDTH_TEST/FLOAT_WIDTH_TEST
  每类型 1 用例）
- test_reply_reader：34（#29-#62；含 RESP3 verbatim/push/double/nil/bool/
  map/attribute/set/bignum 全类型解析）
- test_blocking_connection_errors：3（#63-#65；第 4 个 NXDOMAIN 分支被本机
  DNS 劫持跳过——上游自身打印 "Skipping NXDOMAIN test. Found evil ISP!"）
- test_free_null：2（#66-#67）

51 个需 server 的用例（环境限制如实申报）：
- test_blocking_connection/timeouts/io_errors（TCP+unix 两轮）、
  test_invalid_timeout_errors、test_append_formatted_commands、
  test_tcp_options、test_unix_keepalive、test_throughput、test_pubsub_*、
  test_monitor、test_async_polling、test_resp3_push_*、test_privdata_hooks、
  test_command_timeout_during_pubsub 等——全部需要活的 redis-server 实例。
  test.sh 无法执行（第一步就是拉起 redis-server）。

## 消费者测试兜底（test_package，19 项全 PASS）

1. 同步 API 连接失败路径：redisConnect("127.0.0.1", 1) → err 置位、
   errstr="Connection refused"（errno 语义与上游 #63 用例同源）；
   redisConnectWithTimeout 同族断言。
2. redisFormatCommand：PING 14 字节、SET foo bar 31 字节，memcmp 字节级
   精确断言。
3. redisReaderFeed/GetReply：+PONG（STATUS）、:42（INTEGER）、
   *2 嵌套数组（ARRAY）、-ERR（ERROR）四型解析断言。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 1.2.0 时代 build() 里的 CMake 4.x 正则补丁在 1.3.0 不适用 | 上游 1.3.0 已声明 CMAKE_MINIMUM_REQUIRED(VERSION 3.7.0) | 升级件配方删除该运行时补丁逻辑，恢复标准 cmake.configure()/build() 流程 |
| 2 | 上游 test.c 单独编译需正确头文件搜索顺序 | test.c include 链经 sockcompat.h | 按上游 Makefile 方式 `clang test.c -I. -I<pkg>/include -L<pkg>/lib -lhiredis -lm` |

## 源码修改

无（零补丁）。
