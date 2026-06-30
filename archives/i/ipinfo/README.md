# ipinfo

IP 网络计算工具，用于计算和分析 IP 地址的网络信息。

## 描述

ipinfo 是一个简单的命令行工具，用于显示 IP 地址的各种信息，包括：

- IP 地址及其十进制表示
- 地址类别（A/B/C/D/E 类）
- 私有地址识别
- 网络掩码
- 前缀长度（CIDR）
- 网络地址
- 通配符掩码
- 广播地址
- IP 总数
- 可用主机数
- 最小/最大主机地址

ipmatch 是配套工具，用于检查 IP 地址是否在指定网络范围内。

## 使用示例

### ipinfo 基础用法

```bash
# CIDR 格式
ipinfo 192.168.1.0/24

# IP + 网掩码格式
ipinfo 10.0.0.0 255.0.0.0

# 单项输出
ipinfo -i 8.8.8.8           # 只显示 IP
ipinfo -n 172.16.0.0/16     # 只显示网络地址
ipinfo -b 192.168.1.0/24    # 只显示广播地址
```

### ipmatch 基础用法

```bash
# 检查 IP 是否在范围内（输出 IN/OUT）
ipmatch -t 192.168.1.100 192.168.1.0/24

# 检查是否为网络地址
ipmatch -n 192.168.1.0 192.168.1.0/24

# 检查是否为主机地址
ipmatch -h 192.168.1.1 192.168.1.0/24

# 检查是否为广播地址
ipmatch -b 192.168.1.255 192.168.1.0/24
```

## 版本信息

| 版本 | 编译状态 | 发布日期 | 补丁 |
|------|---------|----------|------|
| 1.2 | built | 2026-06-09 | 1 个 |

## 来源

- **官网**: https://kyberdigi.cz/projects/ipinfo/
- **源码**: https://kyberdigi.cz/projects/ipinfo/files/ipinfo-1.2.tar.gz
- **许可证**: 未明确标注

## 编译信息

- **构建系统**: Makefile
- **编译器**: clang 15.0.4
- **编译选项**: `-fPIC -O2`
- **依赖**: 无（仅需标准 C 库）

## 已编译版本详情

### 1.2

**编译日期**: 2026-06-09

**问题修复**:
- Makefile 硬编码 `/usr/bin/gcc` → 改为可配置 `CC?=clang`
- Makefile 硬编码 `/usr/bin/install` → 改为可配置 `INSTALL?=install`
- 添加 DESTDIR 支持（用于预编译包制作）

**交付物**:
- `ipinfo-1.2-ohos-aarch64.tar.gz` (100K)
  - bin/ipinfo (42K, 已 ELF 签名)
  - bin/ipmatch (38K, 已 ELF 签名)
  - man/man1/ipinfo.1
  - man/man1/ipmatch.1

**测试验证**: 6 个功能测试全部通过

## 特性

- ✅ 支持 CIDR 和网掩码两种格式
- ✅ 自动识别私有地址范围
- ✅ 单项输出选项（-i, -n, -b 等）
- ✅ IP 范围匹配检查
- ✅ 无外部依赖