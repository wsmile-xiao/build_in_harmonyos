# das-watchdog

实时进程看门狗（Realtime-process watchdog）。

Das_Watchdog 是一个面向类 Linux 系统的通用看门狗，常驻后台运行，确保实时（SCHED_FIFO）进程不会挂死整机。当监控到实时进程占用 CPU 超时时，会将其临时降级为非实时优先级，并通过 xmessage 弹窗提示；进程恢复正常后自动恢复实时优先级。

- 上游: https://github.com/kmatheussen/das_watchdog
- 版本: 0.9.0（上游仓库 2015 年停更，无 tag/release，源码内 Makefile/README 声明为 V0.9.0）
- 许可证: GPL-2.0-or-later
- 依赖: libgtop/2.41.3（glibtop.h / libgtop-2.0.pc）