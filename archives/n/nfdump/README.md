# nfdump — 网络流数据采集与分析工具

## 简介

nfdump 是一套开源的网络流数据采集和分析工具，支持 NetFlow v5/v7/v9/IPFIX 格式。它由以下核心组件组成：

- **nfcapd**: 网络流数据采集守护进程，接收并存储来自路由器/交换机的流数据
- **nfdump**: 流数据分析工具，类似 tcpdump 但针对流数据（NetFlow/IPFIX）
- **nfreplay**: 流数据回放工具，将存储的流数据重新发送到指定目标
- **nfanon**: 流数据匿名化工具，使用 CryptoPAn 算法对 IP 地址进行匿名化
- **nfexpire**: 流数据过期管理工具，自动清理过期的流数据文件

## 版本

- 当前版本: 1.7.7
- 作者: Peter Haag
- 许可证: BSD-license

## 平台支持

- 已在 OpenHarmony (aarch64) 上成功编译并测试
- 编译器: clang/clang++
- musl libc 兼容（已处理 `_res` 全局变量不可用的问题）

## 主要特性

- 支持压缩存储（LZO、LZ4 内嵌，可选 bzip2/zstd）
- 支持流数据过滤语法
- 支持多种输出格式（raw、CSV、JSON等）
- 支持 IPv4/IPv6
- 支持自动过期管理