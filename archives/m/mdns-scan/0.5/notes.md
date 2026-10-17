# mdns-scan 0.5 适配笔记

## 编译环境
- 构建系统: makefile (raw Makefile, no configure script)
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# Source the build context
source .build-context-mdns-scan-0.5

cd $BUILD_SRC_DIR

# Build with clang
make CC=clang -j1

# Install to staging
mkdir -p $TEST_PREFIX/usr/bin
DESTDIR=$TEST_PREFIX make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 configure 脚本 | 项目使用原始 Makefile | 直接 make CC=clang 编译 |
| 2 | 无 make check 目标 | 上游无测试套件 | 使用 smoke test (test.sh) 验证二进制可执行 |

## 源码修改

无源码修改。原始源码可以直接编译，无需补丁。

## 依赖版本

无外部依赖。仅依赖标准 C 库 (glibc/musl)。

## 验证结果

```bash
$ file mdns-scan
mdns-scan: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ readelf -d mdns-scan | head -5
Dynamic section at offset 0x48e8 contains 25 entries:
  Tag        Type                         Name/Value
  0x0000000000000001 (NEEDED)             Shared library: [libc.so]
  0x000000000000001e (FLAGS)              BIND_NOW
  0x000000006ffffffb (FLAGS_1)            Flags: NOW PIE

$ timeout 3 ./mdns-scan 2>&1 | head -3
Browsing ... /
Browsing ... -
Browsing ... \
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mdns-scan | 59776 bytes | ELF 64-bit ARM aarch64 可执行文件 |
| mdns-scan.1 | 2029 bytes | man page |

## 注意事项

- mdns-scan 运行后会持续扫描 mDNS 服务，不会自动退出
- 需要网络接口支持 multicast (IFF_MULTICAST)
- 使用 IP multicast 224.0.0.251 端口 5353
---

**编译结束**: 2026-08-07 03:06
**最终状态**: built
