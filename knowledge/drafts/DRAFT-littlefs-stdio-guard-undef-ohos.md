# DRAFT: 上游测试框架 `#undef _STDIO_H` 在 OHOS sysroot 触发 stdio.h 重入重定义

> 草稿（DRAFT-littlefs-stdio-guard-undef-ohos），来自 littlefs 2.11.2 适配。

## 问题描述

编译上游测试运行器（`make test-runner`）时报：

```
error: redefinition of enumerator 'FDSAN_ERROR_LEVEL_FATAL'
error: redefinition of '_G_fpos64_t'
note: 'stdio.h' included multiple times, additional include site here
```

## 根因

littlefs 官方测试框架 `runners/test_runner.h:28-29` 为了「给源码定义 feature 宏的
机会」，在首次 `#include <stdio.h>` 之后显式执行：

```c
#undef _FEATURES_H
#undef _STDIO_H
```

随后生成的测试文件（`*.t.c`）会再次包含 `<stdio.h>`。这一机制假设头文件是
**glibc 风格**：类型分布在各 `bits/types/*.h` 的按类型小守卫中，整个 `<stdio.h>`
可以安全地多次包含。而 OHOS sysroot（musl/OHOS 风格）的 `stdio.h` 将
`fpos_t`/`_G_fpos64_t` 与 `enum fdsan_error_level` 等直接内联在文件体内（无按类型
守卫），`#undef _STDIO_H` 后再次包含即产生重定义。

## 解决方案

唯一目标文件（测试运行器/生成测试）编译时**预定义 `_STDIO_H` 守卫**，使框架首个
`#include <stdio.h>` 被跳过，`#undef` 之后的包含成为唯一一次处理点：

```bash
CFLAGS="-fPIC -O2 -D_STDIO_H" make test-runner CC=<ohos-clang> AR=llvm-ar
```

注意：

- **只加在测试运行器编译**；库本体（`liblfs.a`）不涉及测试框架，不需要该参数。
- 该参数经**环境变量**传递（makefile 内 `CFLAGS +=` 会追加），不能经命令行
  `make CFLAGS+=...` 传递（会整体覆盖 makefile 的 CFLAGS，丢失 `-I.` 等）。

## 验证

```bash
./scripts/test.py ./runners/test_runner -b -k
# done: 11606/11606 passed, 0/11606 failed, 28741pls!, in 187.22s
```

littlefs 2.11.2 在 OHOS aarch64 + clang 15 上全量通过（194 用例 / 11606 perms）。

## 适用边界

- 适用于任何上游测试/构建框架显式 `#undef` 标准库头文件守卫并要求重包含的 C 库。
- 反例/不适用：头文件可安全重入的平台（glibc）、或框架不做 `#undef` 的情况。
- 备选方案：patch `test_runner.h` 用编译期宏跳过 `#undef _STDIO_H`（`_FEATURES_H`
  的 undef 可保留，features.h 重包含是安全的）。

## 关联条目

- E119（sockaddr_storage 重定义）：同为「头文件重定义」触发，根因不同。
- E020（musl FILE 不透明结构）：同为 musl libc 差异，场景不同。
- E493（program_invocation_name 缺失）：musl 符号差异，无关。