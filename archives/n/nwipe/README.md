# nwipe

nwipe 是一个安全磁盘擦除工具，提供基于 curses 的文本界面 GUI，通过 libparted 枚举与擦除块设备。它是 Darik's Boot and Nuke (DBAN) 中 dwipe 命令的 fork。

## 功能概述

- 支持多种擦除方法：DOD Short / DOD 5220.22-M / PRNG Stream (XORoshiro-256) / HMG IS5 enhanced 等
- 多种伪随机数生成器：ISAAC / ISAAC-64 / MT19937 / ALFG / XORoshiro-256
- 多线程并行擦除（pthread）
- curses TUI 设备选择与进度显示
- PDF 擦除报告生成
- SCSI/ATA 硬盘温度监控

## OHOS 适配要点

- **构建系统**: autotools (autoreconf → configure → make → make install)
- **平台兼容 (R32)**: `settings.os in ("Linux", "OHOS")`
- **Linux 内核头文件**: `<linux/hdreg.h>` / `<linux/fd.h>` 用 `#if` 守卫，OHOS 用户态不提供时跳过包含（补丁 0002）
- **libconfig 检测**: 修复 `configure.ac` 中 libconfig 库名与链接器标志错误（补丁 0001）
- **POSIX 头文件**: `wait.h` → `sys/wait.h`

## 依赖关系

### 编译依赖

| 依赖 | 用途 |
|------|------|
| ncurses / panel | curses TUI |
| libparted | 块设备枚举与操作 |
| libconfig | 配置文件解析 (库名 `config`, 标志 `-lconfig`) |
| pthread | 多线程擦除 |
| uuid | libparted 静态链接需要 |
| intl | libparted 静态链接需要 |

### 运行依赖

- root 权限（访问 `/dev/sd*` 等块设备）
- hdparm / smartctl（可选，HDD 参数读取）

## 已知限制

1. 运行时需 root 权限访问块设备，test_package 仅验证 `--version` / `--help` 非特权路径
2. 深度耦合 Linux 块设备 ioctl（`HDIO_GET_IDENTITY`、`BLKGETSIZE64`），OHOS 上仅编译通过，实际擦除依赖 OHOS 块设备驱动接口
3. **上游无测试套件**: nwipe 0.39 源码经审计不含任何测试（详见 `test_package/MANIFEST.yml`）

## 参考资料

- 上游仓库: https://github.com/martijnvanbrummelen/nwipe
- 上游版本: 0.39 (git tag v0.39)
- License: GPL-2.0-only
