# arp-scan 1.10.0 — OpenHarmony 编译记录

## 基本信息

- **软件**: arp-scan
- **版本**: 1.10.0
- **构建系统**: autotools
- **目标平台**: OpenHarmony (aarch64-unknown-linux-ohos)
- **编译日期**: 2026-05-15

## 软件简介

arp-scan 是一个用于网络发现和安全审计的工具，通过发送 ARP 请求并分析响应来扫描和识别本地网络上的主机。主要功能：

- ARP 扫描：快速扫描网络上的活跃主机
- MAC 地址指纹识别：通过 OUI 数据库识别设备制造商
- 支持多种输出格式：可导出为文本、CSV、XML 格式
- 灵活的扫描选项：支持 CIDR、范围、主机列表等多种目标指定方式

## 编译配置

### configure 参数

```bash
./configure --prefix=/storage/Users/currentUser/usr/local --build=aarch64-unknown-linux-ohos
```

### 编译命令

```bash
gcc -I. -I/storage/Users/currentUser/usr/local/include -include config.h \
    -DPKGDATADIR=\"${PKGDATADIR}\" -DPKGSYSCONFDIR=\"${PKGSYSCONFDIR}\" \
    -Wall -Wshadow -Wwrite-strings -c arp-scan.c error.c format.c utils.c \
    wrappers.c link-packet-socket.c mt19937ar.c my_getopt.c strlcpy.c

gcc -L/storage/Users/currentUser/usr/local/lib -o arp-scan \
    arp-scan.o error.o format.o utils.o wrappers.o \
    link-packet-socket.o mt19937ar.o my_getopt.o strlcpy.o \
    -lpcap
```

### 依赖库

- **libpcap**: 1.10.6 (已预编译安装)
- **C 标准**: C99
- **系统头文件**: netpacket/packet.h, net/if.h

## 编译指导

### 关键步骤

1. **autoreconf 问题**: aclocal 无法生成 aclocal.m4
   - 解决：设置 `PERL5LIB` 和使用 `--automake-acdir` 选项
   ```bash
   export PERL5LIB="/storage/Users/currentUser/builds/automake-1.16.5/lib:$PERL5LIB"
   perl aclocal.in --automake-acdir=/path/to/automake/m4 -I m4
   ```

2. **config.status 临时文件**: HMDFS 上 mktemp 失败
   - 解决：修改 config.status 使用预定义临时目录
   ```python
   # 替换 tmp 创建逻辑
   content = re.sub(r'tmp=\`\(umask 077 && mktemp -d "\./confXXXXXX"\) 2>\/dev\/null\`', 'tmp=./confWORKDIR', content)
   ```

3. **头文件包含顺序**: pcap_t 类型未定义
   - 解决：使用 `-include config.h` 确保宏定义生效

4. **PKGDATADIR 未定义**: 编译时缺少宏定义
   - 解决：手动添加 `-DPKGDATADIR` 和 `-DPKGSYSCONFDIR`

### 编译流程

```bash
# 1. 解压源码
cd /storage/Users/currentUser/builds/arp-scan-1.10.0.work

# 2. 复制 build-aux 文件
cp /path/to/automake/lib/install-sh build-aux/
cp /path/to/automake/lib/config.guess build-aux/
cp /path/to/automake/lib/config.sub build-aux/
cp /path/to/automake/lib/missing build-aux/
cp /path/to/automake/lib/depcomp build-aux/

# 3. 创建 m4 目录并复制 automake m4 文件
mkdir -p m4
cp /path/to/automake/m4/*.m4 m4/

# 4. 运行 autoreconf
autoreconf -fi -I m4

# 5. 运行 configure
export TMPDIR=/storage/Users/currentUser/tmp
./configure --prefix=$DEFAULT_PREFIX --build=aarch64-unknown-linux-ohos

# 6. 编译
make -j$(nproc) 或手动编译

# 7. 安装
make install DESTDIR=$TEST_PREFIX
```

## 补丁清单

无补丁文件。源码无需修改即可编译。

## 已知限制

1. **网络权限**: arp-scan 需要 CAP_NET_RAW 权限或 root 权限才能执行实际扫描
   - 原因：需要发送原始 ARP 包
   - 解决方案：使用 `setcap cap_net_raw+ep arp-scan` 或以 root 运行

2. **OpenHarmony 平台检测**: config.guess 不识别 HarmonyOS
   - 解决方案：手动指定 `--build=aarch64-unknown-linux-ohos`

3. **静态链接**: 当前编译为静态链接 libpcap
   - 原因：确保在不同环境中可用
   - 注意：如果需要更新 libpcap，需要重新编译

## 功能验证

### 版本检查

```bash
$ arp-scan --version
arp-scan 1.10.0
Copyright (C) 2005-2022 Roy Hills
License GPLv3+: GNU GPL version 3 or later
libpcap version 1.10.6 (64-bit time_t, with TPACKET_V3)
```

### 常用命令

```bash
# 扫描本地网络
arp-scan --localnet

# 扫描指定 IP 范围
arp-scan 192.168.1.0/24

# 显示接口列表
arp-scan --interface=?

# 输出到文件
arp-scan -o output.txt 192.168.1.0/24
```

## 文件清单

### 安装文件

| 文件 | 路径 | 说明 |
|------|------|------|
| arp-scan | bin/arp-scan | 主程序 (96KB) |
| ieee-oui.txt | share/arp-scan/ieee-oui.txt | OUI 数据库 (1.4MB) |
| mac-vendor.txt | etc/arp-scan/mac-vendor.txt | MAC-Vendor 映射 (2KB) |

### 预编译包

| 文件 | 大小 | 说明 |
|------|------|------|
| arp-scan-1.10.0-ohos-aarch64.tar.gz | 1.9MB | 主包 |
| arp-scan-1.10.0-ohos-aarch64-debug.tar.gz | 100KB | 调试符号包 |
| install-arp-scan-1.10.0.sh | - | 安装脚本 |

---

## 参考资料

- [arp-scan 官网](https://github.com/royhills/arp-scan)
- [arp-scan 文档](https://github.com/royhills/arp-scan/wiki)
- [libpcap 文档](https://www.tcpdump.org/)

---

**编译者**: OpenHarmony Compile Agent
**最后更新**: 2026-05-16