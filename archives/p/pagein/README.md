# pagein — 把进程页强制换入内存

`pagein` 遍历指定进程（或所有进程）的地址空间，逐页触碰每个内存映射，使这些页
被换入物理内存（paged in），并统计访问的映射数、页数、内存/交换占用变化与缺页
次数。用于在基准测试前把目标进程的页预热到内存。

## 主要功能

- `-p pid`：将指定进程的页换入。
- `-a`：将所有进程的页换入（需 root）。
- `-v`：详细输出。

## OHOS 适配要点

- **纯 Makefile 构建**：`make CC=<ohos clang>`；只覆盖 `CC`，保留上游
  `CFLAGS += -Wall -Wextra -DVERSION='"0.01.11"' -O2`。
- **零三方依赖、零补丁**：OHOS sysroot 提供 `sys/ptrace.h`、`sys/mman.h` 等所需头。
- 功能需要 CAP_SYS_PTRACE（root），消费者测试覆盖 `-h` 与参数校验错误路径。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/pagein` | 页换入工具 |
| `share/man/man1/pagein.1` | 手册 |
| `share/bash-completion/completions/pagein` | bash 补全脚本 |

## 参考资料

- 上游仓库：<https://github.com/ColinIanKing/pagein>
- 许可证：GPL-2.0-or-later
