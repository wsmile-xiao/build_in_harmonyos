# DRAFT: aarch64 LP64 — "非 x86_64 ⇒ 32 位" typedef 假设导致静默状态破坏（oscpack 1.1.0 实证）

## 现象

oscpack 1.1.0 在 OHOS aarch64（clang 15）上编译零告警，但上游 OscUnitTests 在
`/a_bool` 用例后 SIGSEGV（exit 139）。单消息断言全过，崩溃发生在紧随其后的
bundle 构造/解析，且崩溃点随优化级别漂移（-O3 崩在 EndBundle 附近，部分场景
更早），看似随机。

## 根因

`osc/OscTypes.h`：

```c
#if defined(__x86_64__) || defined(_M_X64)
typedef signed int int32;      // x86_64: int = 4 字节 ✓
#else
typedef signed long int32;     // 隐含假设：非 x86_64 = 32 位平台
#endif
```

aarch64 是 LP64：`long == 8` 字节 → `sizeof(osc::int32) == 8`。
`OutboundPacketStream` 构造函数的 sanity assert（`assert(sizeof(osc::int32)==4)`）
在 Release（`-DNDEBUG`）下被编译掉；缓冲区偏移/尺寸算术随后全部类型错乱，
内部指针链被静默破坏，故障延迟到后续操作以 SIGSEGV 暴露。

## 定位过程（可复用手法）

1. 管道/重定向输出全缓冲时，SIGSEGV 会丢掉最后 ~4KB 输出 —— **看到的输出边界
   不是崩溃点**。设备无 stdbuf，用 `LD_PRELOAD` 注入 6 行构造函数库
   （`setvbuf(stdout, NULL, _IONBF, 0)`）拿到真实崩溃点。
2. ASan 重编上游源文件直接命中 `assert(sizeof(osc::int32) == 4)` —— 根因浮出。

## 修复（两个联动点）

1. `#else` 分支 typedef 改为 `signed int / unsigned int`（LP32/LP64 通用）；
2. 同库其余 `#if !(defined(__x86_64__)||defined(_M_X64))` 守卫（为 32 位补充的
   `operator<<(int)`、`ReceivedPacket(int)` 重载）追加
   `&& !defined(__LP64__) && !defined(_LP64)`，否则 int32 变 int 后编译报
   重定义。注意预处理指令里不能写 `sizeof(void*)==8`。

## 结果

修复后 OscUnitTests **91/91 通过**，UDP 回环收发正常，conan create 全链路
（含 test_package 端到端消费者测试 23/23）通过。

## 适用范围

任何带"非 x86_64 即 32 位"预处理分支的 C/C++ 库在 aarch64 首次适配时都应
优先 grep 检查 `__x86_64__` 守卫与 int32/long 类 typedef。
