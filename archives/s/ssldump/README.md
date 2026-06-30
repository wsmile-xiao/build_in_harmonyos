# ssldump

ssldump 是一个 SSL/TLS 流量分析工具，用于网络安全监控和 SSL/TLS 协议分析。

## 功能概述

- 实时分析 SSL/TLS 流量
- 解密 SSL/TLS 通信（需要密钥）
- 显示 SSL/TLS 协议握手过程
- 支持多种 SSL/TLS 协议版本
- 网络安全监控和取证分析
- 支持 JSON 输出格式

## OHOS 适配要点

### 依赖库配置

ssldump 需要多个依赖库，CMake 配置时需要指定路径：

```bash
cmake -DOPENSSL_ROOT_DIR=/usr/local \
      -DPCAP_LIBRARY=/usr/local/lib/libpcap.so \
      -DPCAP_INCLUDE_DIR=/usr/local/include \
      -DLIBNET_LIBRARY=/usr/local/lib/libnet.so \
      -DLIBNET_INCLUDE_DIR=/usr/local/include
```

### 依赖关系

ssldump 的主要依赖：

- OpenSSL：SSL/TLS 协议支持
- libpcap：网络包捕获
- libnet：网络包构造
- json-c：JSON 输出格式

### 使用场景

ssldump 主要用于：

- SSL/TLS 协议分析
- 网络安全监控
- 通信取证分析
- SSL/TLS 配置验证

## 依赖关系

### 编译依赖
- OpenSSL 1.1.1 或更高版本
- libpcap（网络包捕获库）
- libnet 1.2（网络包构造库）
- json-c（JSON 库）

### 运行依赖
- OpenSSL
- libpcap
- libnet
- json-c

## 使用示例

```bash
# 监控指定接口的 SSL 流量
ssldump -i eth0

# 解密 SSL 流量（需要密钥）
ssldump -i eth0 -k server.key

# 输出为 JSON 格式
ssldump -i eth0 -j

# 过滤特定端口
ssldump -i eth0 'port 443'
```

## 参考资料

- 官方仓库：https://github.com/adulau/ssldump
- OpenSSL：https://github.com/openssl/openssl
- libpcap：https://github.com/the-tcpdump-group/libpcap
- libnet：https://github.com/libnet/libnet