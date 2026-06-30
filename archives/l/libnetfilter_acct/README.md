# libnetfilter_acct

## 简介
libnetfilter_acct 是一个用于访问网络连接统计信息的库，属于 Netfilter 项目的一部分。

## 功能特性
- 提供对网络连接统计信息的访问接口
- 支持 nfacct 命令行工具
- 与 libmnl 库协同工作

## 依赖关系
- libmnl（必需）

## 编译信息
- 最新版本: 1.0.3
- 编译状态: built
- 编译系统: autotools

## 使用方法
```bash
pkg-config --cflags --libs libnetfilter_acct
```

## 相关链接
- 官方网站: https://www.netfilter.org/projects/libnetfilter_acct/
