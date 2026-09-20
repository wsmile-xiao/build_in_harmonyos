# bus

bus 是一个无守护进程的本地消息广播系统（daemonless local message broadcasting），
基于 System V 信号量与共享内存实现，提供轻量级的两阶段进程间灵活屏障替代方案。

- 仓库: https://github.com/maandree/bus
- 许可证: MIT
- 交付内容: C 库 libbus（公开头文件 bus.h）+ 命令行工具 bus

## Versions

| Version | Status |
| --- | --- |
| 3.1.11 | built |

## 说明

- 构建系统: 纯 POSIX Makefile（config.mk），无 configure 脚本
- 运行时依赖: System V IPC（semget/shmget）+ librt；OHOS 应用沙箱会以 SIGSYS
  拦截 SysV IPC 系统调用（详见 3.1.11/reports/test-report.md 台账与取证）