# bgpq4

BGP filtering automation for Cisco, Juniper, BIRD and OpenBGPD routers.

## 描述

bgpq4 是一个用于自动生成 BGP 路由过滤规则的工具。它通过查询 IRRd（Internet Routing Registry daemon）数据库，为指定的 AS 号或 AS-SET 生成 prefix-list、access-list 或 route-filter，支持多种厂商格式输出：

- Cisco IOS Classic（默认）
- Cisco IOS XR
- Juniper Junos
- NIC.CZ BIRD
- OpenBSD OpenBGPD
- Huawei
- MikroTik RouterOS
- Nokia SR OS
- Arista EOS
- JSON

## 已编译版本

| 版本 | 状态 | 构建系统 | 许可证 | 日期 |
|------|------|----------|--------|------|
| 1.16 | built | autotools | BSD-2-Clause | 2026-06-10 |

## 许可证

BSD-2-Clause

## 项目主页

https://github.com/bgp/bgpq4