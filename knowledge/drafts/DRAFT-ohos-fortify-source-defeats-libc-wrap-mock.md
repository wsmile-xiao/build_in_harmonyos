# `_FORTIFY_SOURCE` 把 libc 调用改写为 `__*_chk`，使 `-Wl,--wrap=read/write/…` 打桩失配

## 现象

用链接期 `--wrap` 给 libc 调用打桩的单元测试，桩函数**从不被调用**，测试框架报 mock 队列未被消费：

```
[==========] tests: Running 13 test(s).
[ RUN      ] write_all_simple_success_test
ERROR:tcti:.../src/util-io/io.c:123: write_all() failed to write to fd 99: Bad file descriptor
[  ERROR   ] --- 0 != 10
```

或 cmocka 直接报：

```
Has remaining non-returned values: __wrap_read
```

容易被误判为"测试本身写错了"，实则是**加固编译选项与打桩机制的交互**。

实测案例：tpm2-tss 4.2.0（`archives/t/tpm2-tss/4.2.0`）上游 `make check`，
6 项用 `--wrap` 的单测失败（`io`、`tcti-{mssim,swtpm,device,pcap}`、`tctildr-getinfo`）。

## 根因

`-D_FORTIFY_SOURCE=2` 会在**编译期**把部分 libc 调用点改写为带边界检查的变体：

| 源码调用 | fortify 开启后的目标符号 |
|---|---|
| `read()` | `__read_chk` |
| `write()` | `__write_chk` |
| `open()` | `__open_chk` |
| `memcpy()` | `__memcpy_chk` |

而 `-Wl,--wrap=<sym>` 的语义是：把**对 `<sym>` 的未定义引用**重定向到 `__wrap_<sym>`。
`__read_chk` 与 `read` **不是同一个符号**，因此：

```
-Wl,--wrap=read      ← 拦不到 __read_chk
-Wl,--wrap=write     ← 拦不到 __write_chk
```

→ 桩函数从不被调用 → mock 队列无人消费 → 报 `Has remaining non-returned values`，
或被测代码拿到未初始化值。

## 秒级诊断（关键：不必跑全量构建）

编译**真实调用点**、用 `nm -u` 看符号：

```sh
# 调用点常在库对象里（src/…），不在测试对象里（test/…）
$CC -O2 -D_FORTIFY_SOURCE=2 -c src/util-io/io.c -o /tmp/p.o
nm -u /tmp/p.o | grep _chk          # → __read_chk __write_chk  ⇒ 命中本条

$CC -O2 -D_FORTIFY_SOURCE=2 -U_FORTIFY_SOURCE -c src/util-io/io.c -o /tmp/q.o
nm -u /tmp/q.o | grep _chk          # → 空                    ⇒ 修法有效
```

实测结果正与上表一致。

## 修复方案

让**测试相关的编译**不带 `_FORTIFY_SOURCE`：在其 `-D` 之后追加 `-U_FORTIFY_SOURCE` 即可。

**⚠ 落点选择是这条的难点**（我踩过两次）：

| 落点 | 结果 |
|---|---|
| `make check AM_CFLAGS=-U_FORTIFY_SOURCE` | ✗ 整体覆盖 `AM_CFLAGS`，丢掉 `$(INCLUDE_DIRS)` → 头文件找不到 |
| 覆盖 `CPPFLAGS`（全局） | ✗ 波及 `src/tss2-esys` 等，openssl 头找不到 |
| **删对象 + 以剥掉 fortify 的 `CPPFLAGS` 重建** + 事后用原参数恢复 | ✓ 实测有效 |

关键点：**调用点在库对象（`src/util-io`、`src/tss2-tcti`）里，不在测试对象里**，
所以只改测试目标的 flags 够不到。且删除时**必须连 `.a` 一起删**——只删 `.o`/`.lo`
时陈旧归档仍携带 fortified 对象，重链接会把它带回来。

```sh
# 单点验证（复用已有构建树，秒级）
find src/util-io src/tss2-tcti test/unit -name '*.o' -o -name '*.lo' -o -name '*.a' | xargs rm -f
make check -j1 CPPFLAGS="-DNDEBUG -U_FORTIFY_SOURCE"
# 交付物不降低加固：测试通过后以原参数重建一次
make -j4
```

**回退方案**：给上游打补丁，在 `TESTS_CFLAGS` 加 `-U_FORTIFY_SOURCE`
（automake 用 `test_*_CFLAGS = $(AM_CFLAGS) $(TESTS_CFLAGS)` 传导到所有测试目标）。
注意：仅当**调用点也在测试对象内**时才够用。

## 与 E999 的差异

**E999-draft-8FBE**《OHOS libc 符号族 configure 误检的 ac_cv 禁用模式》讲的是
**configure 探测层**：`AC_CHECK_FUNCS` 因 `__fread_chk`/`__fgets_chk` 存在于 `libc.so`
而误判 `HAVE=1`，随后业务编译报 implicit declaration（声明受 `__FORTIFY_COMPILATION` 门控）。

本条是**测试打桩层**：fortify 不导致编译失败，而是把调用点静态改写为 `__*_chk`，
使 `--wrap` 匹配不到符号。同一个宏，但**作用阶段**（编译改写 vs 探测误判）与
**症状**（mock 队列未消费 vs implicit declaration）完全不同。

## 检测方法（预扫描）

测试 Makefile 中出现 `--wrap=<libc 函数>`（`read`/`write`/`open`/`memcpy`/`calloc`/…），
同时编译开启了 `-D_FORTIFY_SOURCE` → 预警本条。
