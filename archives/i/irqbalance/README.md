# irqbalance

irqbalance 是一个将硬件中断（IRQ）在多个处理器（CPU）之间均衡分配的守护进程，Linux 系
统生态常用。它通过读取 `/proc/interrupts`、`/sys/devices/system/cpu` 与 netlink 消息
持续监测中断分布与 CPU 状态，周期性把过剩的 IRQ 迁移到空闲核心，从而改善多核系统的
中断吞吐与整体性能。

## 本仓库适配

- 版本：1.9.4（上游 tag v1.9.4 官方 release 归档）
- 构建系统：autotools（GitHub tag tarball 不含 configure，配方内 autoreconf 自举）
- 依赖：glib-2.0（上游强制）、ncursesw（irqbalance-ui 组件）
- 产物：`irqbalance`（守护进程）、`irqbalance-ui`（ncurses 状态查看工具）

## HarmonyOS PC 适配要点

- config.guess/config.sub 注入 HarmonyOS 识别与 linux-ohos triplet（E007）
- configure umask 077→022 + mktemp 绝对路径（E136）
- cputree.c `rindex`→`strrchr`（OHOS libc 移除遗留符号）
- Makefile.am AM_CFLAGS 追加 `$(NCURSESW_CFLAGS)`（ui 编译头文件路径）

## 测试

- 上游 `make check`：tests/runoneshot.sh 1/1 通过
- test_package：执行安装后 `irqbalance --version` 校验版本输出
- 详细证据见版本目录 notes.md / reports/
