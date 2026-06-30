# pcapmirror 0.6.1 适配笔记

## 编译环境
- 构建系统: makefile (简单 Makefile，非 autotools)
- 编译日期: 2026-06-24
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

该项目使用简单 Makefile，没有 configure 脚本。需要通过 make 变量覆盖适配鸿蒙平台：

```bash
cd $BUILD_SRC_DIR
make CC=clang PREFIX=$DEFAULT_PREFIX \
  CFLAGS="-Wall -g -fPIC -O2 -I$DEFAULT_PREFIX/include" \
  LIBS="-L$DEFAULT_PREFIX/lib -lpcap" \
  -j1

# Staging 安装
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/share/man/man8
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cc: command not found` | 鸿蒙平台无 cc 命令 | make CC=clang 覆盖 |
| 2 | `pcap.h not found` | 头文件在非标准路径 | CFLAGS 加 -I$DEFAULT_PREFIX/include |
| 3 | `unable to find library -lpcap` | 库在非标准路径 | LIBS 加 -L$DEFAULT_PREFIX/lib |
| 4 | MANDIR 目录不存在 | Makefile install 目标未创建 | 手动 mkdir -p 预创建 |
| 5 | make check 无此目标 | 简单 Makefile 无 check | 跳过，记录原因 |

## 依赖版本

- libpcap 1.10.6 (已预编译安装在 $DEFAULT_PREFIX)

## 源码信息

- 源码 URL: https://git.freestone.net/cramer/pcapmirror/-/archive/0.6.1/pcapmirror-0.6.1.tar.gz
- 源码 sha256: d5efbb9b8526b8b319f3040f6a7c9532c0ca9d862b1d21100e7fc8665d0bb638

## 验证结果

### 编译验证
```bash
$ make CC=clang ... -j1
clang -Wall -g -fPIC -O2 -I/storage/Users/currentUser/usr/local/include -c main.c -o main.o
clang -Wall -g -fPIC -O2 -I/storage/Users/currentUser/usr/local/include main.o -o pcapmirror -L/storage/Users/currentUser/usr/local/lib -lpcap
gzip -9 -c pcapmirror.8 > pcapmirror.8.gz
# 退出码: 0 — 编译成功，无警告无错误
```

### ELF 完整性
```bash
$ file pcapmirror
pcapmirror: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

### 功能验证
```bash
$ pcapmirror -h
Usage: pcapmirror [options]
Options:
  -i <interface>       Specify the capture interface
  -f <filter>          Specify the capture filter (BPF syntax)
  -r <host/ipv4/ipv6>  Specify the destination host (required)
  -p <port>            Specify the destination port (default: 37008)
  -e                   Use ERSPAN encapsulation (default: TZSP)
  ...
# 退出码: 0 — 帮助信息正常输出 ✅

$ pcapmirror -l
Error in pcap_findalldevs: dummy0: SIOCETHTOOL(ETHTOOL_GLINK) ioctl failed: Permission denied
# 退出码: 0 — libpcap API 调用正常，权限限制为预期行为 ✅
```

### 已安装二进制验证
```bash
$ /storage/Users/currentUser/usr/local/bin/pcapmirror -h
# 正常输出帮助信息，退出码 0 ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pcapmirror-0.6.1-ohos-aarch64.tar.gz | 440KB (450648 字节) | 主包（含二进制+依赖+man page） |
| pcapmirror-0.6.1-ohos-aarch64-debug.tar.gz | 72KB (74273 字节) | 调试符号包 |

## 注意事项

- 该项目虽然标记为 autotools，但实际使用简单 Makefile，无 configure 脚本
- 通过 make 变量覆盖 CC/CFLAGS/LIBS 适配，无需源码补丁
- make check 不存在（无测试套件），功能验证通过 -h/-l 实际运行确认
- -l 选项因平台权限限制（SIOCETHTOOL ioctl）返回错误，属预期行为
- 打包包含外部依赖 libpcap.so，确保独立运行
---

**编译结束**: 2026-06-24 14:59
**最终状态**: built
