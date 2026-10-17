# libhiredis 1.3.0 适配笔记

## 编译环境

- 构建系统: CMake（上游 CMakeLists.txt，CMAKE_MINIMUM_REQUIRED 3.7.0）
- 编译日期: 2026-09-24
- 编译器: clang 15（OHOS SDK, aarch64-linux-ohos）
- 状态: published（conan create 全绿：包构建 + test_package 19 项消费者测试全 PASS）
- 任务: 平台任务 #13876（libhiredis 1.3.0，taskBranch=feat/libhiredis-1.3.0）

## 软件说明

hiredis 是 Redis 官方最小化 C 客户端库。任务名 libhiredis，与 main 已有
archives/h/hiredis/1.2.0（Question666，2026-08 done）为同一上游不同归档目录——
本配方按平台任务名归档 archives/l/libhiredis/1.3.0。

零第三方运行时依赖（ssl/event 组件未启用；adapters/ 为纯头文件）。

## 构建配置

- DISABLE_TESTS=ON（打包不构建 add_test——test.sh 需要真实 redis-server）
- ENABLE_SSL/SSL_TESTS/ASYNC_TESTS/EXAMPLES/NUGET 全 OFF
- 零源码补丁（1.3.0 的 CMake minimum 3.7.0 无 CMake 4.x 兼容问题，
  1.2.0 时代的 cmake_minimum_required 补丁不再需要；OHOS 走 POSIX 常规路径）

## R51 上游测试清点与结果申报（rule4 口径）

上游测试形态：单一自测二进制 test.c（118 个 test() 用例，22 个 test_ 函数），
CMake 注册 `add_test(NAME hiredis-test COMMAND test.sh)`；test.sh 起真实
redis-server（TCP 56379 + unix socket + 可选 TLS 56443）后跑全套。
上游 CI（test.yml）用 redis:alpine docker。

实测（本机 OHOS 交叉编译 test.c 链接 libhiredis.a 后直接运行）：

| 类别 | 数量 | 结果 |
|------|------|------|
| 无 server 纯函数用例 | 67 | **67/67 PASS** |
| 需真实 redis-server | 51 | 环境阻断（CI/本机均无 redis-server/docker） |

67 个构成明细：
- test_allocator_injection：3（#01-#03）
- test_format_commands：25（#04-#28；15 个 test() 调用点 + printf-delegation 宏
  10 个整数/浮点变体展开计数——上游宏 TEST_FORMAT_PRINTF_DELEGATION 每类型 1 用例）
- test_reply_reader：34（#29-#62；36 个 test() 调用点中 2 个属
  test_free_null 前置边界，实测运行 #29-#62 共 34 个）
- test_blocking_connection_errors：3（#63-#65；第 4 个 NXDOMAIN 分支被本机
  DNS 劫持跳过——上游自身打印 "Skipping NXDOMAIN test. Found evil ISP!"）
- test_free_null：2（#66-#67）

51 个需 server 的用例（环境限制如实申报）：
- test_blocking_connection/timeouts/io_errors（TCP+unix 两轮）、
  test_invalid_timeout_errors、test_append_formatted_commands、test_tcp_options、
  test_unix_keepalive、test_throughput、test_pubsub_*、test_monitor、
  test_async_polling、test_resp3_push_*、test_privdata_hooks、
  test_command_timeout_during_pubsub 等——全部需要活的 redis-server 实例。
  test.sh 无法执行（第一步就是拉起 redis-server）。

## 消费者测试兜底（test_package，19 项全 PASS）

1. 同步 API 连接失败路径：redisConnect("127.0.0.1", 1) → err=REDIS_ERR_IO、
   errstr="Connection refused"（errno 语义与上游 #63 用例同源）；
   redisConnectWithTimeout 同族断言。
2. redisFormatCommand：PING 14 字节、SET foo bar 31 字节，memcmp 字节级精确断言。
3. redisReaderFeed/GetReply：+PONG（STATUS）、:42（INTEGER）、
   *2 嵌套数组（ARRAY）、-ERR（ERROR）四型解析断言。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 test.c 单独编译报 pollfd 未定义 | test.c include 链经 sockcompat.h（POSIX 下引入 poll.h），直接 clang 编译需正确 -I 顺序 | 按上游 Makefile 方式 `clang test.c -I. -I<pkg>/include -L<pkg>/lib -lhiredis -lm` |
| 2 | 首轮 66 PASS/1 FAIL（RESP3 attribute） | 误链了 conan 缓存中旧 hiredis/1.2.0 的包（1.2.0 read.c 不支持 `\|` 类型字节）——通过 `conan cache path libhiredis/1.3.0:<pkgid>` 定位真包 | 用 1.3.0 真包重编后 67/67 全 PASS；教训：多版本同名包共存时必须用 cache path 精确定位 |

## 源码修改

无（零补丁）。
