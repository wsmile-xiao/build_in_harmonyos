# ipmiutil

**描述**: IPMI 服务器管理工具集

**主页**: https://ipmiutil.sourceforge.net/

**许可证**: BSD-2-Clause AND BSD-3-Clause AND GPL-2.0-or-later

**语言**: C

**构建系统**: autotools

**分类**: 包管理类

## 功能概述

ipmiutil 是一组 IPMI（Intelligent Platform Management Interface）服务器管理工具，用于监控和管理 BMC（Baseboard Management Controller）。主要功能包括：

- **传感器监控**（sensor）：读取传感器数据和阈值
- **SEL 日志管理**（events/sel）：解码和显示 IPMI 事件日志
- **FRU 信息查询**（fru）：读取和写入 FRU（Field Replaceable Unit）库存数据
- **LAN 参数配置**（lan）：设置 IPMI LAN 参数和用户权限
- **电源控制**（power/reset）：远程电源控制和系统重置
- **看门狗定时器**（wdt）：配置和监控看门狗计时器
- **BMC 健康检查**（health）：检查 BMC 基本健康状况
- **固件更新**（hpm/fwum）：HPM 固件升级管理
- **SOL 远程控制台**（sol）：串口 over LAN 远程会话

## 编译版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 3.2.2 | published | 2026-06-12 | lanplus 功能因缺 OpenSSL 头文件而禁用 |

## HarmonyOS 适配要点

- config.guess/config.sub 需添加 `HarmonyOS` 平台识别
- configure 脚本需扩展 OS 检测以支持 `HarmonyOS`
- HMDFS 文件系统需处理 `/tmp` 只读问题（使用 `$TMPDIR` 替代）
- HMDFS 下 `mktemp` 创建的目录权限需 umask 022 修正
- `--enable-lanplus=no` 配置选项为必需（因缺少 OpenSSL 头文件）