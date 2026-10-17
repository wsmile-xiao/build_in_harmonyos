# DRAFT-libdsme-0.67.0-libcheck-temp-env-on-ohos

## 现象

libdsme 上游 Check 测试在 OHOS 上（TMPDIR 已指向可写目录）仍失败：

```
/path/check_msg.c:317: Unable to create temporary file for communication;
may not have permissions to do so
```

CK_FORK=no 也无效。

## 根因

Check 0.15.2 `check_msg.c` 的 `open_tmp_file()` 探测顺序：

1. `TEMP` 环境变量
2. `P_tmpdir` 宏（musl 定义为 `"/tmp"`）
3. `TMPDIR` 环境变量
4. `"."`

musl 定义了 `P_tmpdir=/tmp`，OHOS `/tmp` 只读 → `mkstemp` 失败；`TMPDIR`
排在第 3 位，永远轮不到。glibc 不定义或允许覆盖 `P_tmpdir`，因此该问题在
OHOS/musl 上特有。

## 修复

同时设置三个拼写（最稳妥），指向可写目录：

```bash
TEMP=<build>/tmp TMP=<build>/tmp TMPDIR=<build>/tmp ./tests/ut_libdsme -o result.xml
```

实测同一二进制：
- 只设 TMPDIR → 失败；
- 设 TEMP/TMP/TMPDIR → `100%: Checks: 2, Failures: 0, Errors: 0`（fork 模式默认，无需 CK_FORK=no）。

## 适用范围

所有在 OHOS 上跑 libcheck 的 C 测试；构建脚本中"设置临时目录"时应把
`TEMP` 一并设置，不能只依赖 `TMPDIR`。
