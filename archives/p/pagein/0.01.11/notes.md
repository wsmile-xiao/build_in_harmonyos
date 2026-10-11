# pagein 0.01.11 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 Makefile，`CFLAGS += ... -DVERSION='"0.01.11"'`）
- 编译日期: 2026-10-03
- 编译器: OHOS SDK clang（Conan profile 的 `tools.build:compiler_executables.c`）
- 状态: built

## 编译步骤

1. 从官方 `codeload.github.com` 取 tag `V0.01.11` 的源码包（`pagein-0.01.11.tar.gz`）。
2. `build()` 执行 `make CC=<ohos clang> -j1`（只覆盖 `CC`，让 Makefile 自带的
   `CFLAGS += -Wall -Wextra -DVERSION='"0.01.11"' -O2` 生效）。
3. `package()` 安装 `bin/pagein`、`share/man/man1/pagein.1`、
   `share/bash-completion/completions/pagein`、`licenses/{COPYING,README.md}`。
4. `test_package/test_pagein.sh` 运行 7 项检查。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 若命令行传 `CFLAGS=...` 会导致 Makefile 的 `CFLAGS +=` 失效、丢失 `-DVERSION` | make 中命令行变量会冻结文件内的 `+=` | 只传 `CC=<clang>`，不动 `CFLAGS` |
| 2 | 无法做功能级验证 | pagein 需以 root / CAP_SYS_PTRACE 附加目标进程 | 消费者测试覆盖 `-h` 与三条参数校验错误路径 |

## 源码修改

无。零补丁。

## 依赖版本

无三方依赖（仅 libc）。

## 验证结果

```bash
# 消费者（test_package/test_pagein.sh，7 项）
PAGEIN_CHECK_SUMMARY checks=7 fails=0
```

## 注意事项

- 上游无测试套件，按 §3.6 口径声明上游 N=0，另加鸿蒙特有（消费者）测试 7 项。
