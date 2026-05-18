# hping

网络探测工具，类似于 ping 但支持 TCP/UDP/ICMP 等多种协议。

## 版本

- **3.0.0-alpha-1** - HarmonyOS 适配版本

## 功能

- TCP/IP 数据包构造和发送
- 支持 TCP、UDP、ICMP、RAW-IP 协议
- 网络探测和安全测试
- Traceroute 模式
- 分片测试

## 依赖

- libpcap（网络数据包捕获库）

## HarmonyOS 适配说明

hping 需要进行以下适配才能在 HarmonyOS 上编译：

1. **系统类型定义**：创建 `systype.h` 定义 `OSTYPE_HARMONYOS`
2. **字节序定义**：创建 `byteorder.h` 定义 `__LITTLE_ENDIAN_BITFIELD`
3. **平台适配**：getifname.c 已包含 Linux 分支，兼容 HarmonyOS
4. **libpcap 依赖**：从 Alpine Linux 预编译包获取，绕过 bison/flex pipe 限制

## 编译选项

```bash
make CC=clang PCAP=-lpcap
```

## 参考

- 官方仓库: https://github.com/antirez/hping
- 官方网站: http://www.hping.org/