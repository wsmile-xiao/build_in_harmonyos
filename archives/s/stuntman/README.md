# stuntman — STUN 协议服务端与客户端

## 简介

stuntman 是一个开源的 STUN（Session Traversal Utilities for NAT）协议实现，提供 STUN 服务端（stunserver）和客户端（stunclient）工具。它遵循 RFC 3489、5389、5789 和 5780 规范，用于检测和解决 NAT 网络环境下的连通性问题。

## 主要功能

- **stunserver**：STUN 协议服务端，支持多种 NAT 检测模式（直接映射、端点独立、地址依赖等）
- **stunclient**：STUN 协议客户端，用于查询 NAT 类型及公网 IP/端口映射
- **stuntestcode**：内置单元测试套件，验证 STUN 协议核心逻辑的正确性

## 版本信息

| 版本 | 编译状态 | 编译日期 |
|------|---------|---------|
| 1.2.16 | published | 2026-06-05 |

## 依赖

- openssl（提供 libcrypto，用于 STUN 消息完整性验证）

## 编译说明

### 构建系统

stuntman 使用自定义 Makefile（非标准 autotools/cmake），通过 `common.inc` 集中管理编译参数。

### OHOS 平台适配要点

1. **链接器替换**：OHOS SDK 的 lld 依赖 libxml2.so.16（平台不可用），需使用 GNU ld 替代：
   ```
   LDFLAGS="-fuse-ld=/data/service/hnp/bin/ld -L/storage/Users/currentUser/usr/local/lib"
   ```
2. **无 install 目标**：项目 Makefile 没有标准 `make install` 目标，需手动安装二进制和文档
3. **ELF 签名**：生成的二进制需通过 `ohc-run.py sign-elf` 签名后才能在 HMDFS 上执行

### 补丁

| 版本 | 补丁文件 | 说明 |
|------|---------|------|
| 1.2.16 | 0001-common.inc.patch | 添加 LDFLAGS 使用 GNU ld 和系统库搜索路径 |

## 预编译包

| 文件名 | 大小 | 说明 |
|--------|------|------|
| stuntman-1.2.16-ohos-aarch64.tar.gz | 3396KB | 预编译包（二进制 + man pages + 文档） |
| stuntman-1.2.16-ohos-aarch64-debug.tar.gz | 838KB | 调试符号包 |

## 验证结果

stuntestcode 全部 13 个单元测试 + 4 个 NAT 检测子测试 PASS：
- CTestDataStream、CTestReader、CTestBuilder、CTestIntegrity、CTestMessageHandler、CTestCmdLineParser、CTestClientLogic、CTestRecvFromEx(IPV4/IPV6)、CTestFastHash、CTestPolling、CTestAtomicHelpers、CTestRateLimiter

## 许可证

Apache License 2.0（详见源码包中的 LICENSE 文件）

## 参考链接

- 官方网站：https://www.stunprotocol.org/
- 源码下载：https://www.stunprotocol.org/stunserver-1.2.16.tgz