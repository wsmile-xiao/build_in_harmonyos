# DRAFT：googletest 1.6 CapturedStream 硬编码 /tmp —— OHOS 死亡测试父进程 abort(134)

## 现象

老项目（本例 GNU CSSC 1.4.1，捆绑 googletest 1.6）在 OHOS 设备上 `make check`：

- 单元测试二进制（含 EXPECT_EXIT/ASSERT_DEATH 死亡用例）整体 `exit status 134`（SIGABRT）
- 日志仅有 `Death tests use fork(), which is unsafe particularly in a threaded context` 警告
  和 `Signal 6 (core dumped)`，**没有任何 [ OK ] / [ FAILED ] 用例级输出**
- automake 汇总 `FAIL: test_xxx (exit status: 134)`

## 误导性排查路径（实测排除）

1. ~~fork/pipe/abort 在 OHOS 上坏了~~ —— 纯 C 最小程序（pipe+fork+child abort+waitpid）
   在可写目录验证完全正常，父进程正确收割。
2. ~~threadsafe/fork 死亡测试模式差异~~ —— `--gtest_death_test_style=threadsafe` 同样挂。
3. ~~C++ 运行时（libc++/异常）影响 fork~~ —— 裸 clang++ 编译的最小 gtest 死亡测试同样挂。

## 真根因

`googletest/src/gtest-port.cc` 的 `CapturedStream` 构造：

```cpp
#  if GTEST_OS_LINUX_ANDROID
    char name_template[] = "/sdcard/captured_stream.XXXXXX";
#  else
    char name_template[] = "/tmp/captured_stream.XXXXXX";   // ← 硬编码
#  endif
    const int captured_fd = mkstemp(name_template);
```

- 仅 Android 特判 `/sdcard`，无 TMPDIR 逻辑（1.6 时代，2011）
- OHOS `/tmp` 只读 → `mkstemp` 返回 -1（errno EACCES）
- 紧随的 `GTEST_CHECK_` 在**父进程**里 `abort()`——`CaptureStderr()` 在 fork **之前**
  由父进程调用（用于捕获子进程 stderr），所以子进程根本没被 fork 出去，
  整个测试二进制就死了

连环坑：同包项目自有测试代码直接调 `tmpfile()`（musl `P_tmpdir="/tmp"`）同样失败
（cssc 的 test_linebuf.cc），需一并加 `mkstemp($TMPDIR)+fdopen+unlink` 回退。

## 修复（patch vendored gtest 副本，无条件 POSIX——R8 合规）

```diff
 #  else
-    char name_template[] = "/tmp/captured_stream.XXXXXX";
+    // Honour $TMPDIR when set: /tmp may be read-only on some
+    // platforms (e.g. HarmonyOS).
+    char name_template[4096];
+    {
+      const char *td = getenv("TMPDIR");
+      if (NULL == td || !*td)
+        td = "/tmp";
+      snprintf(name_template, sizeof(name_template),
+               "%s/captured_stream.XXXXXX", td);
+    }
```

不引入 `#ifdef __OHOS__` 平台宏（项目 R8 规则）：getenv("TMPDIR") 回退
"/tmp" 在所有平台与原行为等价——Linux 上 TMPDIR 未设时仍用 /tmp，
行为不变；OHOS 等只读 /tmp 环境设了 TMPDIR 才改道。

## 验证

- 修复前：`FAIL: test_sccsdate (exit status: 134)` 等 4 个二进制
- 修复后：unit-tests 11/11 PASS（含 SccsdateDeathTest.BuckRogers 等 4 个死亡用例）
- 上游 tests/ 91 shell 脚本 + gl/tests 不受影响

## 通用性

任何捆绑 googletest ≤1.7 且测试含死亡用例/CaptureStderr 的老项目在 OHOS
设备上跑测试都会踩（captured_stream 字符串是稳定指纹）；新版 gtest（≥1.8）
已有跨平台临时目录探测，不在此列。

关联家族：DRAFT-E547（libcheck 的 P_tmpdir/TMPDIR 优先级问题）——同为 /tmp
只读家族，但本条是**硬编码缺失 + 父进程 abort 的判读特征**，根因与修法都不同。
