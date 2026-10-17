# netatalk

## 简介

Netatalk 是开源 AFP（Apple Filing Protocol）文件服务器，可把 Unix 主机变成
Mac 客户端的高性能文件与打印服务器。本仓库适配 4.5.1 到 HarmonyOS PC。

## 功能特性

- afpd AFP 文件服务守护进程
- cnid_dbd / cnid_metad CNID 数据库守护进程（本适配仅 sqlite 后端）
- netatalk 服务控制器与 afppasswd 等工具
- 上游 afpd TAP 集成测试随构建运行

## 编译信息

- 版本：4.5.1
- 构建系统：meson
- 依赖：bstring、iniparser、libevent、libgcrypt、sqlite3
- 配置：CNID 仅 sqlite；ACL/CUPS/Kerberos/LDAP/PAM/quota/Zeroconf/
  Spotlight/TCP wrappers/dtrace/AppleTalk 关闭

## 使用方法

```bash
afpd -V
cnid_dbd -V
netatalk -V
```

## 更多信息

- 官网：https://netatalk.io
- 上游仓库：https://github.com/Netatalk/netatalk
- 发布页：https://github.com/Netatalk/netatalk/releases/tag/netatalk-4-5-1
