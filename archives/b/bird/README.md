# BIRD Internet Routing Daemon

BIRD 是一个动态 IP 路由守护进程，支持 BGP、OSPF、RIP、Babel 等路由协议。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 3.1.6 | built | 2026-07-06 |

## 描述

BIRD (BIRD Internet Routing Daemon) 是一个常用于 Linux/Unix 系统的开源动态 IP 路由守护进程。
它支持多种路由协议，包括 BGP (Border Gateway Protocol)、OSPF (Open Shortest Path First)、
RIP (Routing Information Protocol)、Babel 等。

## 核心可执行文件

- **bird** — 路由守护进程
- **birdcl** — 简易 CLI 客户端（命令行控制接口）
- **birdc** — ncurses CLI 客户端（OHOS 平台未构建，需 ncurses）

## 上游

- 主页: https://bird.nic.cz/
- 源码: https://gitlab.nic.cz/labs/bird
- 许可证: GPL-2.0-or-later
