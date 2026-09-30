# OHOS/musl 下 core 插件 .so 的 dlopen 消费测试：桩层类型须逐字段对齐上游头文件

> Status: DRAFT（草稿期以文件名标识；promote 时由工具分配 E 编号）
> Source: kamailio-gcrypt 6.0.6（Alpine `kamailio` 子包 gcrypt 模块，core 插件）HarmonyOS PC 适配，2026-09-29
> Related: `kamailio-extras-6.0.6-ohos-platform-defs-injection`（构建期平台宏注入）；E074/E525（OHOS 禁 FIFO → `make -j1`）；P004、P013

## 背景

kamailio 的模块是**宿主导入型（core 插件）**共享库：模块 `gcrypt.so` 自身不实现
`sr_kemi_modules_add`、`fixup_spve2_pvar`、`get_debug_level` 等 23 个 core 符号
（实测数目），这些符号由 kamailio 主程序在 `loadmodule` 时提供（模块是 `dlopen` 进来的，
宿主已导出符号 → 解析成功）。

鸿蒙（OHOS）使用 musl 加载器，**对 `dlopen` 的共享库不做惰性绑定**（等价 `RTLD_NOW`）：
`dlopen` 那一刻，模块的全部未定义符号都必须解析成功，否则直接失败。因此「以消费者身份
加载模块并真实调用」这类测试（本仓 `test_package` 的 rule12 用例）必须随测试编译一个
**core 符号桩层**（`kamailio_core_stub.{c,h}`），并用 `-Wl,--export-dynamic` 把桩层符号
导出给 `dlopen` 解析。

本次 kamailio-gcrypt 适配中，这套做法第一次跑就踩到一个**极具误导性**的坑，值得固化为知识。

## 现象（错误面）

```text
$ clang -std=c11 test_gcrypt_e2e.c kamailio_core_stub.c -o build/test_gcrypt_e2e -I. \
        -Wl,--export-dynamic -ldl
compile rc=0                       ← 编译 100% 通过
$ LD_LIBRARY_PATH=<模块>:<依赖包 lib> ./build/test_gcrypt_e2e gcrypt.so
Signal 11 (core dumped)            ← 运行第一行就崩
e2e rc=139
```

误导点：表现完全不像"桩层问题"，而像"模块功能实现坏了"（例如 AES 加密函数崩）。
但 `gcrypt_aes128.c` 的实现逐行核对无问题（`gcry_cipher_open/setkey/setiv/encrypt` 都有
错误分支且返回 `NULL`/`-1`），因此排查方向一开始被带偏。

## 根因

桩层只保证了「符号名存在」，**类型口径与上游头文件错位**，共三处 + 一处空指针：

| 符号 | 上游声明（`src/core/dprint.h`） | 初版桩层写成 | 后果 |
|------|-------------------------------|-------------|------|
| `my_pid` | `int my_pid(void)`（**函数**，:161） | `int my_pid = 1;`（变量） | 模块误把它当函数调用/按变量取值 → 垃圾值 |
| `dprint_color` | `void dprint_color(int)`（**函数**，:217） | 变量 | 同上 |
| `log_level_info` | `struct log_level_info log_level_info[]`（**数组**，:181） | 标量指针 | 索引取值越界读 |
| `_km_log_func` | `void (*)(int, const char *, ...)`（:174） | `NULL` | **空指针调用 → SIGSEGV** |

触发链：模块的 `LM_ERR(...)` 经 `dprint.h` 的 `LOG_FX` 宏族展开，先判
`dprint_crit == 0`（桩层给了 0，成立）、再判 `get_debug_level(...) >= level`；
一旦成立即调用 `_km_log_func` —— 桩层是 `NULL` → 立即崩溃。
本次实际发生在 e2e 的 **NULL 上下文负例**上（模块按设计走 `LM_ERR("aes128_encrypt: context is NULL")`
并返回 -1，本该是一个干净的负例断言），结果变成进程崩死。

修好桩层类型、并把 `_km_log_func` 指向一个非空 sink 之后，同一用例 **50/50 断言全通过**，
且能在日志里看到那句本该出现的错误信息：

```text
[stub-log] aes128_encrypt: context is NULL
ALL OHOS E2E PASSED (50 assertions, ...)
e2e rc=0
```

## 处理策略（rec_approach）

桩层按「**上游头文件的声明形态**」逐字段对齐，而不是「能编过就行」：

1. **函数 vs 变量**：`my_pid`、`dprint_color` 写成函数定义；数组按真实元素类型/长度给足。
2. **日志函数指针必须指向非空 sink**（`void sink(int, const char*, ...)` 内 `vfprintf(stderr, ...)`）。
   即使当前 `get_debug_level()` 返回 0 使日志被抑制，也绝不留 `NULL` ——
   否则"需要看错误信息的时候"正是进程崩溃的时候。
3. 桩层文件头写明**类型口径来源**（上游文件 + 行号）与「哪些符号是真实语义实现、哪些仅需可解析」。
4. 被测试路径**真实调用**的符号（如 `sr_kemi_modules_add`）给出与宿主同语义的实现 + 计数/记录，
   使断言能观察宿主侧行为（本次即据此校验 `mod_register()` 传入的 KEMI 表）。
5. 需要 `-Wl,--export-dynamic` 才能把桩层符号导出给 `dlopen` 解析（缺了会在 `dlopen` 阶段
   报 `undefined symbol`）。

## 检测手段

```bash
# 1) 症状：编译过、运行立即 139
clang -std=c11 test_<m>_e2e.c kamailio_core_stub.c -o /tmp/e2e -I. -Wl,--export-dynamic -ldl
LD_LIBRARY_PATH=<模块目录>:<依赖包 lib> /tmp/e2e <m>.so; echo "rc=$?"     # 139 = SIGSEGV

# 2) 桩层类型与上游头文件逐条比对（本次三处错位点）
grep -nE "my_pid|dprint_color|log_level_info|_km_log_func|get_debug_level" src/core/dprint.h
grep -nE "my_pid|dprint_color|log_level_info|_km_log_func|get_debug_level" test_package/kamailio_core_stub.*

# 3) 修好后：断言全绿
LD_LIBRARY_PATH=... /tmp/e2e <m>.so        # 期望 ALL OHOS E2E PASSED (N/N)
```

## 适用面（affected_scope）

- 所有「宿主程序提供符号」的插件/扩展型 `.so` 在 OHOS 上的独立消费测试：
  kamailio 全家族模块、nginx 模块、gstreamer 插件、Apache 模块等；
- 以及任何在测试中**手工声明上游符号类型**（`extern` 变量 vs 函数）的桩层写法 ——
  同名符号编译期不报错，运行期才是未定义行为。

## 兜底方案（fallback）

不用桩层，改为让测试可执行文件链接**真宿主**导出的符号（分发宿主本体副本，或
`-Wl,--unresolved-symbols=ignore-all` + 运行期由真宿主提供）。代价是需要先能在 OHOS 上
构建/分发宿主本体（kamailio core 在 musl 下另有 `_res`/`union semun` 等适配成本），
验证成本远高于桩层；仅在宿主本体已在同一次构建中可得时采用。

## 禁止项

- **`_km_log_func` 置 NULL（或指向只返回值的 getter）**：等于给模块埋了「正常时看不见、
  出错时直接崩」的陷阱；`LOG_FX` 在判定通过时无条件调用该指针。
- **把上游的函数/数组声明成 `extern` 变量**：ABI 语义不同，编译不报错、运行即崩，
  崩溃点与真实缺陷位置不一致，严重误导排查。

## 原则引用

P004（平台隔离的标准写法）、P013（平台限制必须降级而非绕过）。
