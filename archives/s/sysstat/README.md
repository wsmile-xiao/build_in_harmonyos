# sysstat

Linux 系统性能监控工具集，包含 sar、sadf、iostat、mpstat、pidstat 等命令。

## 描述

sysstat 是一组用于 Linux 系统性能监控的工具：
- **sar**: 收集和报告系统活动信息（CPU、内存、I/O、网络等）
- **sadf**: 以多种格式（CSV、JSON、SVG、XML）显示 sar 收集的数据
- **iostat**: 报告 CPU 和磁盘 I/O 统计信息
- **mpstat**: 报告每个 CPU 核心的统计信息
- **pidstat**: 报告进程/线程的 CPU、内存、I/O 统计信息
- **tapestat**: 报告磁带设备统计信息
- **cifsiostat**: 报告 CIFS 文件系统统计信息

## 鸿蒙适配说明

- 使用 `--disable-sensors` 禁用 sensors 支持（鸿蒙平台无 libsensors）
- 使用 `-V` 参数查看版本（非 `--version`），这是 sysstat 的设计特性
- `make install` 需要 root 权限创建 `/var/log/sa` 和 `/etc/sysconfig`，本地安装时可通过 `SA_DIR` 和 `SYSCONFIG_DIR` 参数覆盖到可写路径
- sadc 数据收集依赖 /proc 文件系统，核心监控命令（iostat/mpstat/pidstat）可实时从 /proc 读取统计数据
- G0 clean-verify 的 config.status Permission denied 是 HMDFS 平台已知限制（E046），非软件缺陷
- sysstat 不提供 `make check` 测试目标，需手动验证功能

## 已编译版本

- 12.7.9 (published, 2026-06-10)

## 下载与安装

预编译包可通过 cmd-pkgs 公共安装脚本安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- sysstat 12.7.9
```

安装后可用命令：
- `/storage/Users/currentUser/usr/local/bin/sar`
- `/storage/Users/currentUser/usr/local/bin/sadf`
- `/storage/Users/currentUser/usr/local/bin/iostat`
- `/storage/Users/currentUser/usr/local/bin/mpstat`
- `/storage/Users/currentUser/usr/local/bin/pidstat`
- `/storage/Users/currentUser/usr/local/bin/tapestat`
- `/storage/Users/currentUser/usr/local/bin/cifsiostat`

## 验证

```bash
sar -V       # 输出: sysstat version 12.7.9
iostat       # 输出: CPU和磁盘I/O统计
mpstat       # 输出: CPU使用率统计
pidstat      # 输出: 进程CPU使用率统计
```