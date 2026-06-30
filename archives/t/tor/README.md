# tor

Tor anonymity network daemon，用于匿名通信和网络隐私保护。

## 基本信息

- **语言**: C
- **类型**: 网络守护进程
- **官方网站**: https://www.torproject.org/
- **源码**: https://gitlab.torproject.org/tp/core/tor

## 功能特性

- 匿名网络通信
- 隐藏服务（Hidden Services）
- 洋葱路由加密
- 桥接节点支持

## 版本信息

| 版本 | 状态 | 构建系统 | 补丁数 |
|------|------|----------|--------|
| 0.4.9.6 | published | autotools | 5 |

## 依赖

- OpenSSL
- libevent
- zlib

## 使用说明

```bash
tor --version
tor -f /etc/tor/torrc
```

## 编译说明

需要以下补丁：
- config.guess/config.sub 平台识别
- configure 脚本修改
- OpenSSL TLS 兼容性补丁