# pacparser

Library to parse proxy auto-config (PAC) files. Pacparser is a C library
(with Python bindings) that enables any program to evaluate PAC scripts
and determine proxy settings for given URLs.

## 简介

PAC（Proxy Auto-Config）文件是一种基于JavaScript的代理配置标准，
Web浏览器使用PAC文件来决定对于给定URL应该使用哪个代理服务器或直连。
pacparser使任何C或Python程序都能轻松具备PAC脚本解析能力。

## 实现方式

pacparser使用Mozilla的JavaScript解释器引擎来解析PAC脚本（JavaScript）。
v1.5.0版本内嵌QuickJS引擎（从SpiderMonkey迁移），并实现了所有PAC标准
辅助函数（如 `dnsDomainIs`、`isInNet`、`myIpAddress` 等）。

## 主要组件

| 组件 | 说明 |
|------|------|
| libpacparser.so | 共享库（C API，9个公共函数） |
| pactester | CLI工具（测试PAC文件） |
| pacparser.h | C头文件 |
| Python模块 | Python绑定（pip install pacparser） |

## 许可证

LGPL-3.0-or-later

## 链接

- 主页: http://pacparser.manugarg.com
- 源码: https://github.com/manugarg/pacparser
- 版本: 1.5.0