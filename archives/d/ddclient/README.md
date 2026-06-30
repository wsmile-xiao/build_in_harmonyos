# ddclient

ddclient 是一个 Perl 编写的动态 DNS (DDNS) 更新客户端，用于自动将主机的 IP 地址变更同步到 DNS 服务商。

## 基本信息

| 项目 | 值 |
|------|---|
| 软件名 | ddclient |
| 当前版本 | 4.0.0 |
| 语言 | Perl |
| 构建系统 | autotools（实际为手动sed安装） |
| 许可证 | GPL-2.0 |
| 项目地址 | https://github.com/ddclient/ddclient |

## 功能描述

ddclient 支持通过39种动态DNS协议（包括 Cloudflare、DynDNS2、No-IP、Gandi、GoDaddy、HE.net、Hetzner、Namecheap、OVH、Porkbun 等）自动更新DNS记录。可通过Web、网络接口、防火墙/路由器、外部命令等方式获取IP地址，支持IPv4和IPv6。

## 运行依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| perl | ≥ 5.10.1 | 核心运行依赖 |
| curl | 系统自带 | 默认HTTP获取方式 |
| IO::Socket::SSL | - | HTTPS功能需要（当前平台缺失） |
| JSON::PP | Perl内置 | 部分协议需要 |
| Digest::SHA | Perl内置 | 部分协议需要 |

## 已编译版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 4.0.0 | published | 2026-06-03 |

## 平台适配说明

- ddclient 是纯 Perl 脚本软件，无需C编译器
- HMDFS平台上需要通过 `perl ddclient` 方式调用（shebang直接执行可能失败）
- configure/config.status 在 HMDFS 上可能因权限问题失败，可手动用 sed 从 .in 模板生成脚本