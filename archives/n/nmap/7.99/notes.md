# nmap 7.99 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-21
- 编译器: clang/clang++ (15.0.4)
- 状态: built
- 平台: aarch64-unknown-linux-ohos

## 编译步骤

```bash
# 1. 初始化
python3 ohc-run.py init-build nmap 7.99 --url=https://nmap.org/dist/nmap-7.99.tar.bz2

# 2. 配置（需要设置 TMPDIR）
export TMPDIR=~/.tmp
./configure --prefix=/ --with-openssl=$OPENSSL_PREFIX

# 3. 编译（跳过 zenmap）
make nmap
make -C ncat
make -C nping

# 4. 安装
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识图谱 |
|---|------|------|----------|----------|
| 1 | configure: umask 077 创建临时目录权限拒绝 | E011: HMDFS 文件系统 UID 映射导致权限问题 | sed -i 's/umask 077/umask 022/g' configure | E011 |
| 2 | config.guess 无法识别 HarmonyOS | E007: GNU config.guess 不包含 HarmonyOS 检测 | 使用 patch-autotools-ohos.pl 打补丁 | E007 |
| 3 | config.status /tmp 只读 | E002: /tmp 文件系统只读 | export TMPDIR=~/.tmp | E002 |
| 4 | sockaddr_storage 重定义冲突 | E091: OHOS 内核头文件 linux/socket.h 与 musl sys/socket.h 冲突 | 在 #include <linux/if.h> 前 #define sockaddr_storage __linux_sockaddr_storage | E091 |
| 5 | configure 脚本 shebang #!/bin/sh 不存在 | E165: HarmonyOS 没有 /bin/sh，需用 /system/bin/sh 或 CONFIG_SHELL | Conan profile 设置 CONFIG_SHELL=/data/service/hnp/bin/bash | E165 |
| 6 | libdnet-stripped configure 失败 "Ethernet support not found" | HarmonyOS 缺少 PF_PACKET 原始以太网套接字 | 移除 configure 中 as_fn_error 强制检查，使用 eth-none 模块 | 新发现 |

## sockaddr_storage 冲突影响文件
- libpcap/pcap-linux.c
- libdnet-stripped/src/tun-linux.c
- libdnet-stripped/src/route-linux.c
- libdnet-stripped/src/ndisc-linux.c

## 源码修改

### 补丁列表 (27 个)
- 0001-0002: 顶层 config.guess/config.sub HarmonyOS 识别
- 0003: 顶层 configure umask 077→022 修复
- 0004-0005: libdnet-stripped config.guess/config.sub
- 0006: libdnet-stripped configure 移除以太网强制检查
- 0007-0009: libdnet-stripped sockaddr_storage 守卫 (ndisc/route/tun)
- 0010-0013: libpcap config.guess/config.sub/configure umask/pcap-linux.c sockaddr_storage
- 0014-0016: libpcre config.guess/config.sub/configure umask
- 0017-0019: libssh2 config.guess/config.sub/configure umask
- 0020: nbase configure umask
- 0021-0023: ncat config.guess/config.sub/configure umask
- 0024-0026: nping config.guess/config.sub/configure umask
- 0027: nsock configure umask

## 依赖

- openssl/3.5.6 (Conan 制品仓)
- pcre2: 内嵌 libpcre2
- zlib: 系统自带
- lua: 内嵌 liblua

## 验证结果

```bash
# nmap 二进制生成成功
./nmap --version
# Nmap version 7.99 ( https://nmap.org )
# Platform: aarch64-unknown-linux-ohos
# Compiled with: nmap-liblua-5.4.8 openssl-3.5.6 nmap-libssh2-1.11.1 libz-1.3.1 nmap-libpcre2-10.47 nmap-libpcap-1.10.6 nmap-libdnet-1.18.0 ipv6

# ncat 二进制生成成功
./ncat/ncat --version
# Ncat: Version 7.99 ( https://nmap.org/ncat )

# nping 二进制生成成功
./nping/nping --version
# Nping version 0.7.99 ( https://nmap.org/nping )

# nping 功能测试
./nping/nping -c 1 127.0.0.1
# SENT (0.0039s) Starting TCP Handshake > 127.0.0.1:80
# RCVD (0.0042s) Possible TCP RST received from 127.0.0.1:80 --> Connection refused
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| nmap | 9.0MB | 主扫描工具 |
| ncat | 5.1MB | netcat 替代工具 |
| nping | 5.2MB | ping 工具 |

## 注意事项

1. zenmap (Python GUI) 因缺少 Python build 模块未编译，可跳过
2. 所有 configure 脚本需要修复 umask 077 → umask 022
3. 所有 config.guess/config.sub 需要应用 HarmonyOS 补丁
4. 包含 linux/if.h 或 linux/netlink.h 的源文件需要添加 sockaddr_storage 守卫
5. libdnet-stripped 需要移除以太网支持强制检查（HarmonyOS 无 PF_PACKET）
6. Conan 构建中使用 conanbuild.sh 环境自动设置 CC/CXX/CONFIG_SHELL（R33）

---

**编译结束**: 2026-07-21
**最终状态**: built
