# E-DRAFT: LLVM 内置 googletest 的 CapturedStream 硬编码 `/tmp` —— 只读 `/tmp` 上整轮单测中止（0 结果）

- **触发实例**：clang-format 22.1.8.src 适配，`FormatTests` 在 HarmonyOS PC aarch64 上运行（2026-09-18）
- **错误签名**：`[ FATAL ] .../gtest-port.cc:1126:: Failed to open tmp file /tmp/gtest_captured_stream.XXXXXX for capturing stream.` + `Signal 6 (core dumped)`
- **类别**：test-harness-platform
- **严重度**：2（确定性中止；但因中止发生在汇总行之前，朴素解析会看到“0 结果”，易被误当无事发生）

## 症状

运行单测二进制（如 `FormatTests`）到第一个使用 `CaptureStdout/CaptureStderr` 的用例时：

```text
[WARNING] .../gtest-port.cc:1102:: Failed to create tmp file /tmp/gtest_captured_stream.XXXXXX
          for test; does the test have access to the /tmp directory?
[ FATAL ] .../gtest-port.cc:1126:: Failed to open tmp file /tmp/gtest_captured_stream.XXXXXX for capturing stream.
Signal 6 (core dumped)
```

进程被 SIGABRT 杀死，**汇总行 `[  PASSED  ] N tests.` 根本没打印**。夹具实测：
1244 个用例跑到 ~800 个时中止；朴素正则读到 `unit_total=0`。

## 根因

`third-party/unittest/googletest/src/gtest-port.cc` 的 `CapturedStream` 在
非 Windows / 非 Android / 非 iOS 分支里：

```c
name_template = "/tmp/";
name_template.append("gtest_captured_stream.XXXXXX");
const int captured_fd = ::mkstemp(const_cast<char*>(name_template.data()));
```

路径是**编译期字面量**，该 gtest 副本对 POSIX 分支**不读** `TMPDIR` 也不读 `TEST_TMPDIR`
（设了也没用）。鸿蒙根 `/tmp` 只读（SKILL E002）→ `mkstemp` 失败 → gtest FATAL + SIGABRT。

## 修复（不改上游源码/测试）

编译一个 20 行 LD_PRELOAD 垫片拦截 `mkstemp`，把 `/tmp/` 前缀改写掉，使文件落到**可写的
当前工作目录**；然后从可写目录运行单测：

```c
#define _GNU_SOURCE
#include <dlfcn.h>
#include <string.h>
int mkstemp(char *tmpl) {
    static int (*real)(char *) = 0;
    if (!real) real = (int (*)(char *))dlsym(RTLD_NEXT, "mkstemp");
    if (tmpl && strncmp(tmpl, "/tmp/", 5) == 0)
        memmove(tmpl, tmpl + 5, strlen(tmpl + 5) + 1);   /* 只变短：仍在 std::string 容量内 */
    return real(tmpl);
}
```

```bash
cc -shared -fPIC -o shim.so shim.c
cd <可写目录> && LD_PRELOAD=shim.so <unit-binary>
```

垫片下 `FormatTests` **1244/1244 真实全通过**（含此前中止的 `ConfigParseTest.GetStyleOutput`）。

## 备选（次选，需显式申报）

`--gtest_filter=-ConfigParseTest.GetStyleOutput` 排除使用 Capture* 的用例。保留其余用例真实
运行，但**丢断言**，必须按 R51 显式写明技术原因，不得静默跳过。优先用垫片跑全量。

## 禁止

- `chmod`/`umount`/`remount rw` 去改平台挂载（越权、破坏设备稳定性）。
- 给 `gtest-port.cc` 打补丁改字面量（改上游测试基础设施，偏离上游）。
- 把“解析出 0 个用例”当成通过（把硬中止静默转成假绿，违反 R30/R51）。

## 关联

- 实例配方：`archives/c/clang-format/22.1.8.src/conanfile.py`
- 相关：`DRAFT-22018-llvm22-lit-use-clang-env`（同批 LLVM 22 测试基础设施差异）
