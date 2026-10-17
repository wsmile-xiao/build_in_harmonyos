# DRAFT-libfaketime-0.9.11-musl-symver-alias：ld.lld: error: symbol `timer_gettime@GLIBC_2.2` has undefined version

> Status: **Draft**（待审核 promote）| severity: `3`（🔴 blocking）| category: `libc, musl, portability, ohos, build-system` | Updated: 2026-09-25
> 对应: `knowledge/drafts/DRAFT-libfaketime-0.9.11-musl-symver-alias.kv`
> 实证来源: libfaketime 0.9.11 在 HarmonyOS PC（OHOS aarch64 / clang 15 / musl）`conan create`，PR head `feat/libfaketime-0.9.11`

---

**匹配关键词**：`.symver`, `undefined version`, `GLIBC_2.33`, `version-script`, `ld.lld`, `musl`, `interposer`, `alias`

**预扫描正则（prescan_pattern）**：`\.symver|version-script=|GLIBC_[0-9]+\.[0-9]+`，扫描范围 `*.c, *.h, Makefile*, *.mk, *.map`

## 1. 错误签名（error_signature）

```text
ld.lld: error: ... has undefined version GLIBC_[0-9.]+
symbol .* has undefined version
expected a '@' in the name          # 去掉 @ 后试图走"无版本别名"写法时的次生报错
```

libfaketime 0.9.11 上的真实输出（8 个符号一次性报出，节选）：

```text
ld.lld: error: symbol timer_gettime@GLIBC_2.2 has undefined version GLIBC_2.2
ld.lld: error: symbol timer_settime@GLIBC_2.33 has undefined version GLIBC_2.33
ld.lld: error: symbol pthread_cond_timedwait@GLIBC_2.2.5 has undefined version GLIBC_2.2.5
```

## 2. 根因（root_cause）

glibc 的**符号版本机制**（`.symver` 汇编指示 + `--version-script` 里的 `GLIBC_x.y { global: …; }` 节点）是 glibc 专有的。OHOS 用 musl：`libc.so` 里不存在任何 `GLIBC_x.y` 版本定义，ld.lld 在"符号带版本引用却找不到版本定义"处直接失败。

**次生坑（关键，别踩第二遍）**：把 `.symver` 的第二个参数去掉 `@`、想表达"未版本化别名"也不行——OHOS 的 clang 内联汇编前端（IntegratedAsm / AArch64）**强制要求 `.symver` 的名字带 `@`**：

```text
<inline asm>:1:21: error: expected a '@' in the name
```

因此 `.symver` 这条语法本身在 OHOS 上无路可走，必须换表达机制。

## 3. 推荐方案（rec_priority 1：`symver-alias-branch`）

三处配套改动，**glibc 路径零影响**：

1. **`#if defined __GLIBC__` 包住原 `.symver` 块**，`#else` 分支用符号别名把"当前 ABI 变体"以**未版本化公开名**导出：

```c
#if defined __GLIBC__
__asm__(".symver timer_settime_233, timer_settime@GLIBC_2.33");
#else
/* musl/OHOS: no symbol versioning — alias the current-ABI implementation
   to the public name so the interposer stays visible to the loader. */
__extension__ extern __typeof__ (timer_settime_233) timer_settime
    __attribute__ ((alias ("timer_settime_233")));
#endif
```

2. **把 `--version-script` 参数化**（`src/Makefile`：`-Wl,--version-script=libfaketime.map` → `-Wl,--version-script=$(VERSION_SCRIPT)`，默认值不变），OHOS 侧传一份**匿名（无版本节点名）的 local-only map**：

```
{ local: timer_settime_*; timer_gettime_*; pthread_cond_timedwait_*; pthread_cond_init_*; pthread_cond_destroy_*; };
```

——只把 `_22/_225/_232/_233` 实现名藏起来，其余全部公开导出。

3. 配方侧：`make VERSION_SCRIPT=libfaketime.map.ohos`。

4. **载体选择：这份 map 由配方 `build()` 用 `save()` 生成，不要用补丁新增文件**。本仓库的 `finish` 会跑 `refresh-patch --auto`，它按"**已存在的源文件**"逐个重生成补丁（`0001-src-Makefile.patch` … `0006-test-testframe.sh.patch`），并**静默丢弃 new-file hunk**——`src/libfaketime.map.ohos` 就是这样被吞掉的，之后 `export_conandata_patches` / `apply_conandata_patches` 直接 `ConanException: Patch file does not exist`。凡是"OHOS 独有、上游没有对应文件"的载荷（version script、machine file、wrapper 脚本），放进 `build()` 生成才幂等；否则每次 `finish` 都要人工重合并。

## 4. ★ 禁止策略（与推荐方案同等重要）★

**禁止"整块删掉 `.symver` 声明和 version script"**（仓库既有 `archives/l/libfaketime/0.9.10/patches/0002-disable-glibc-symver.patch` 即此做法）。

- **原因**：删掉之后 `timer_settime_233` / `timer_gettime_233` / `pthread_cond_timedwait_225` / `pthread_cond_timedwait_232` / `pthread_cond_init_232` 这些实现函数**没有任何公开名指向它们**——POSIX 定时器与条件变量超时等待的拦截能力在 OHOS 上被静默丢弃；同时 version script 也没了，这些内部名反而被导出污染 ABI。
- **后果**：库能链接、能加载、`time()`/`clock_gettime()` 照常工作，**既有计时类测试全部照绿**（libc 会顶替应答），缺陷只在"用了被拦截 API 的消费者"身上延迟暴露。这类回归对计时断言不可见，**必须靠符号归属断言才抓得住**。

## 5. 有效性判据（本机制自带的三级验收口径）

任何"把 glibc 版本节点绑定移植到 musl"的改动，三级都要过：

1. **静态**：`nm -D --defined-only` 里公开名必须是**未版本化**导出，`_22/_225/_232/_233` 实现名不得出现。
2. **运行时·时间语义**：`FAKETIME="-15d"` 下用**伪造钟**的 abstime 调 `pthread_cond_timedwait()`。未被拦截时 deadline 落后真实钟 15 天 → 立即返回 ETIMEDOUT；**实测必须真等 ≥800 ms** 才算 interposer 生效（libfaketime 0.9.11 实证：1001 ms）。
3. **运行时·符号归属**：`LD_PRELOAD` 后用 `dlsym(RTLD_DEFAULT, name)` + `dladdr()` 断言命中库本身（libc 顶替应答不算通过），并断言**本进程自身** `time` / `clock_gettime` / `gettimeofday` / `getpid` / `pthread_cond_timedwait` 的绑定地址落在该库。

> ⚠ **不要用 `dlopen()` 来做第 3 级检查**：`libfaketime.so.1` 在 OHOS 上 `dlopen()` 直接 **SIGSEGV**（未签名的构建目录副本同样崩，而 `libz.so` 能正常 dlopen），它是纯 LD_PRELOAD 载荷，只能预加载后检查。

## 6. 已尝试并失败的方案

| 方案 | 结果 |
|---|---|
| `.symver timer_gettime_233, timer_gettime`（去掉 `@`） | clang 报 `expected a '@' in the name`，语法层不通 |
| 删掉 `.symver` 块 + 删掉 version script（0.9.10 归档做法） | 链接通过，但 5 个拦截点消失、内部名泄漏（见 §4） |
| 给 musl 补一份假的 `GLIBC_2.x` version script 节点 | 链接期能过，运行时符号解析仍指向不存在的版本，属于自欺，未采纳 |

## 7. 适用范围与反例（safety_boundary）

- **适用**：任何以 `.symver` + `--version-script` 拦截/重定位 libc 符号的工程——LD_PRELOAD 型 interposer（时间、内存、线程、getaddrinfo 拦截器）、符号版本化 shim、`compat_*` 兼容层。
- **不适用**：只用到 `__asm__(".symver")` 做**自身**多版本导出（不引用 libc 版本节点）的场景——那类只需把引用侧版本节点去掉，不需要 alias；以及纯 C++ ABI 标签（`_ZTV…`）问题，与本机制无关。
- **配套条件**：`__attribute__((alias))` 要求目标与别名同 TU 且目标非 `static`；跨 TU 时改用薄封装函数而不是 alias。

## 8. 与知识库既有条目的关系

- 与 `musl-compat` 家族（OHOS 无 `_res` / `index` / `rindex` 等符号缺失类经验）**同族但不同签名**：那些是"符号在 musl 里不存在"，本条是"版本节点语法不存在"，解法也不同（补兼容实现 vs alias + 匿名 map）。
- 本条为 **create**（新增），不是 hit：知识库中没有任何条目覆盖 `.symver` / version-script 的移植。

---

*本文件与同名 `.kv` 成对提交于 libfaketime 0.9.11 的适配 PR；promote 后转入 `knowledge/doc/`。*
