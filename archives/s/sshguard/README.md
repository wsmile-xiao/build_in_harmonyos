# sshguard

> Protect hosts from brute force attacks against SSH and other services

## 基本信息

| 项目 | 值 |
|------|-----|
| 名称 | sshguard |
| 版本 | 2.5.1 |
| 许可证 | ISC |
| Homepage | https://www.sshguard.net/ |
| 分类 | 网络通信类 |
| 语言 | C |
| 构建系统 | autotools |

## 描述

sshguard monitors logging activity and blocks attacks by updating firewall rules. It supports multiple log sources (syslog, journald, file) and multiple firewall backends (iptables, pf, hosts.allow, etc.).

## 鸿蒙适配说明

- 防火墙后端 iptables/pf/nft 等在鸿蒙上不可用，推荐使用 `sshg-fw-null` 或 `sshg-fw-hosts`
- musl 不支持 pthread cancellation，已通过 `#ifdef __OHOS__` 宏守卫处理
- HMDFS umask 问题已通过 configure 补丁修复（E011）
- sshguard 需要配置文件 `sshguard.conf` 才能正常运行