# memstat

解析 `/proc/<pid>/maps`，按进程与共享对象汇总虚拟地址空间用量的诊断工具。

memstat 列出所有占用虚拟内存的进程、可执行文件与共享库。要拿到完整列表
需以 root 运行（否则部分进程的 maps 不可读）。输出先按进程汇总（不含共享
内存），再按共享对象汇总（括号内为真正共享的部分），最后给出总计。
内存量均为**虚拟内存**而非物理内存。

## 用法

```
memstat [-n] [-v] [-w] [-p pid]
```

| 选项 | 说明 |
|------|------|
| `-n` | numeric 模式，跳过 inode→路径反查，因此**不需要** `/etc/memstat.conf` |
| `-v` | 打印版本与用法后退出 |
| `-w` | 不截断超过 79 列的行 |
| `-p pid` | 只统计指定 PID |

## HarmonyOS PC (aarch64) 适配说明

源码基于 glibc 编写，适配到 OHOS 的 musl libc 时需要一处补丁
（`patches/0001-memstat-c-musl-strtol-errno-and-path-max.patch`）：

- 显式 `#include <limits.h>` 以取得 `PATH_MAX`；
- `perm[4]` 改为 `perm[5]`，修掉 `%4s` 造成的 1 字节越界写；
- `read_proc()` 改用 `strtol` 的 endptr 判别非数字 `/proc` 条目——musl 的
  `strtol()` 会对无数字的字符串置 `errno=EINVAL`，原判定逻辑会导致
  memstat 在扫描第一个 `"."` 条目时 `exit(1)`，完全无法工作。

补丁不含任何平台宏，在 glibc 下同样编译通过且行为不变。
详见 `1.2/notes.md`。

## 已知限制

- 仅当某映射无路径、需按 inode 反查时才读取硬编码路径 `/etc/memstat.conf`；
  使用 `-n` 可完全跳过该依赖。
- 需要访问 `/proc`；在受限环境下报告可能不完整，属工具设计使然。
