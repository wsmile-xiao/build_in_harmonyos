# cidrmerge

## 软件描述

CIDR merging with network exclusion - CIDR 地址优化工具。

cidrmerge 是一个用于 CIDR（无类别域间路由）优化的程序和库。它可以：
- 合并 CIDR 地址块，减少地址列表数量
- 应用白名单排除特定网络地址
- 优化黑名单、ACL 和路由表

## 版本信息

当前版本: 1.5.3

## 构建系统

使用简单 Makefile 构建系统，无 configure 步骤。

## 功能特性

- 高性能 CIDR 合并算法（N*log(N) 复杂度）
- 支持白名单过滤
- 内存使用高效，支持百万级网络地址
- 提供 C 库供程序集成使用
- 包含网络掩码转换工具（Perl脚本）

## 参考资料

- [SourceForge 项目页面](https://sourceforge.net/projects/cidrmerge/)
- [Savannah GNU 页面](https://savannah.nongnu.org/projects/cidrmerge/)