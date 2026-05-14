# iputils 20240905

## 简介

iputils 是 Linux 系统中一组小型网络实用工具的集合，包含 ping、tracepath、arping 和 clockdiff 等经典网络诊断工具。

## 工具列表

| 工具 | 功能 | IPv6 支持 |
|------|------|----------|
| ping | ICMP Echo 请求，检测网络连通性 | ✅ |
| tracepath | 路径 MTU 发现，追踪网络路径 | ✅ |
| arping | ARP 请求，检测局域网设备 | ❌ (IPv4 only) |
| clockdiff | ICMP Timestamp，测量主机时钟差异 | ❌ (IPv4 only) |

## IPv6 支持

**重要**: iputils 20240905 版本已统一 IPv4/IPv6 支持：
- ping 和 tracepath 使用单一工具支持两种协议
- 使用 `-4` 强制 IPv4，`-6` 强制 IPv6
- 自动根据目标地址选择协议

## 安装

运行预编译包中的 install.sh：

```bash
./install.sh
```

默认安装到 ~/usr/local/bin，可通过 PREFIX 环境变量修改：

```bash
PREFIX=/usr/local ./install.sh
```

## 使用示例

### ping IPv4
```bash
ping -c 4 192.168.1.1
ping -4 google.com
```

### ping IPv6
```bash
ping -c 4 ::1               # localhost IPv6
ping -6 ipv6.google.com
```

### tracepath IPv4
```bash
tracepath 192.168.1.1
tracepath -n google.com     # 不解析域名
```

### tracepath IPv6
```bash
tracepath ::1
tracepath -6 ipv6.google.com
```

### arping (仅 IPv4)
```bash
arping -c 4 192.168.1.1
arping -I eth0 192.168.1.1
```

### clockdiff (仅 IPv4)
```bash
clockdiff 192.168.1.1
clockdiff -T iso time.example.com
```

## 编译信息

- 版本: 20240905
- 平台: HarmonyOS aarch64
- 编译器: clang 15.0.4
- 构建系统: meson + ninja

## 功能限制

本次编译禁用了以下可选功能（依赖库未安装）：
- libcap capability 支持
- libidn2 IDN (国际化域名) 支持
- gettext 国际化支持

## 文件列表

```
archives/i/iputils/20240905/
├── README.md                    - 本文件
├── RELEASENOTE.md               - 版本说明
├── install.sh                   - 安装脚本
├── manifest.yaml                - 编译记录
├── PROGRESS.md                  - 编译进度
├── patches/                     - 补丁文件
│   └── 0001-harmonyos-compatibility.patch
├── reports/                     - 测试报告
│   └── test-report.md
└── packaging/                   - 预编译包
    └── iputils-20240905-ohos-aarch64.tar.gz
```

## 许可证

GPL-2.0-or-later

## 来源

- 官方网站: https://iputils.org
- 源码下载: https://iputils.org/iputils-20240905.tar.gz
- GitHub: https://github.com/iputils/iputils