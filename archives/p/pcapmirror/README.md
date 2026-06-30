# pcapmirror — 远程网络流量镜像工具

pcapmirror 是一款命令行工具，用于在远程主机上捕获网络流量并通过 TZSP 或 ERSPAN 协议镜像到目标目的地。它利用 libpcap 库进行数据包捕获，支持 BPF 语法过滤，适用于网络监控、入侵检测和远程数据包分析场景。

## 核心功能

- 基于 libpcap 的网络流量捕获
- 支持 TZSP（TaZmen Sniffer Protocol）封装（默认）
- 支持 ERSPAN（Encapsulated Remote SPAN）封装
- BPF 语法过滤（如 `tcp port 80`）
- 可与 Wireshark 直接配合使用
- 支持网络接口列表、详细模式和包计数

## OpenHarmony 适配要点

| 适配项 | 说明 |
|--------|------|
| 构建系统 | 使用简单 Makefile（非 autotools），虽然注册信息标记为 autotools，实际无 configure 脚本 |
| 编译器覆盖 | 鸿蒙平台无 `cc` 命令，需 `make CC=clang` 覆盖 |
| 头文件路径 | `pcap.h` 在 `$DEFAULT_PREFIX/include`，需 CFLAGS 加 `-I` |
| 库路径 | `libpcap` 在 `$DEFAULT_PREFIX/lib`，需 LIBS 加 `-L` |
| man 目录 | Makefile install 未创建 `share/man/man8` 目录，需手动 mkdir 预创建 |
| 测试套件 | 无 `make check` 目标，功能验证通过实际运行确认 |
| 网络接口 | `-l` 选项因平台权限限制（SIOCETHTOOL ioctl）返回错误，属预期行为 |

## 依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| libpcap | 1.10.6 | cmd-pkgs 预编译包 |

## 用法示例

```bash
# 捕获 eth0 上的 TCP 80 端口流量，镜像到 192.168.1.100
pcapmirror -i eth0 -f "tcp port 80" -r 192.168.1.100 -p 47008 -v
```

## 许可证

BSD-3-Clause

## 主页

https://git.freestone.net/cramer/pcapmirror