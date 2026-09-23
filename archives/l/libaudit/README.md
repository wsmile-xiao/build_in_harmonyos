# libaudit

## 简介

libaudit 是 Linux 审计子系统的用户态客户端库，来自
[linux-audit/audit-userspace](https://github.com/linux-audit/audit-userspace)：
`audit_open()/audit_send()/audit_get_reply()` 经 NETLINK_AUDIT socket
与内核审计子系统通信；`audit_rule_fieldpair_data()` 等辅助函数构造审计
规则；并内置 syscall/machine/field/message 完整查找表。同源码树还产出
`libauparse`（审计日志解析库）与 auditctl/auditd/ausearch/aureport/
autrace/ausyscall 等管理工具。

本归档为**库导向打包**（包名 libaudit）；整体项目打包见 `audit/4.1.2`。

## 上游信息

- 官方仓库: https://github.com/linux-audit/audit-userspace
- License: LGPL-2.1-or-later（库）、GPL-2.0-or-later（工具）
- 构建系统: Autotools（tag 归档不含生成的 configure，需 autoreconf -f -i）

## OHOS 适配

- audit netlink 接口在 OHOS 内核形态（W0 实测）：常量在、socket 对
  app 域被拒（EACCES）——audit_open() 按文档语义返回负 fd，netlink
  控制面测试豁免申报，库的查找/解析面完整可用（详见各版本 notes.md）
- sockaddr_storage 头文件冲突守卫、strndupa 宏实现（clang lifetime
  陷阱）、posix_fallocate 返回码语义、lld -fno-common 头文件临时
  定义等 17 项移植补丁（详见 2.7.4/notes.md）
- 上游 make check 全绿（含 4.1.2 时代在 aarch64 失败的 lookup_test）

## 版本

- 2.7.4（2026-09-15）：首次适配，静态库（R26 系统同名库），测试全过
