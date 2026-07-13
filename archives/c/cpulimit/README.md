# cpulimit

## 简介

cpulimit 是一个用于限制进程 CPU 使用率的命令行工具。它通过定期发送 SIGSTOP 和 SIGCONT 信号来控制目标进程的 CPU 占用百分比，适用于任何可执行程序。

## 上游主页

- **GitHub**: https://github.com/opsengine/cpulimit

## 许可证

- **GPL-2.0**

## 已编译版本

- **版本**: 0.2

## 编译方式

cpulimit 使用纯 Makefile 构建，无 `configure` 脚本（非 autotools 项目）。顶层 Makefile 委托 `src/` 和 `tests/` 子目录编译。

```bash
cd <source-dir>
make -j1
# 无 make install 目标，需手动复制二进制
cp src/cpulimit <prefix>/bin/
```

### OHOS 适配要点

- 在 `src/cpulimit.c` 中添加 `#define _GNU_SOURCE`（Makefile 的 `CFLAGS ?=` 会被环境变量覆盖）
- 在 `src/process_group.c` 中添加 `#include <libgen.h>`（OHOS sysroot 中 basename() 需要此头文件）
- 条件包含 `sys/sysctl.h`（仅 Apple/FreeBSD 需要，OHOS/Linux 不存在）
- 修复 `#ifdef` 语法为 `#if defined(...)` 形式

详见 `0.2/notes.md` 获取完整的适配笔记。
