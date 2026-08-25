# arpoison 0.6 适配笔记

## 编译环境
- 构建系统: makefile (simple single-file C program)
- 编译日期: 2026-08-14
- 编译器: clang/clang++
- 状态: published

## 编译步骤

arpoison 使用极简 Makefile（非 autotools/cmake），只有单个 C 源文件 arpoison.c。

1. 通过 conan 安装 libnet/1.2 依赖
2. 使用 libnet-config 获取编译标志和库路径
3. 手动使用 clang 编译 arpoison.c，链接 libnet

### 实际编译命令
```bash
clang -Wall -D_BSD_SOURCE -D_DEFAULT_SOURCE -DHAVE_NET_ETHERNET_H \
  -I/storage/Users/currentUser/usr/local/include \
  arpoison.c -o arpoison \
  -L/storage/Users/currentUser/usr/local/lib -lnet
```

### 安装
```bash
mkdir -p $TEST_PREFIX$DEFAULT_PREFIX/bin
cp arpoison $TEST_PREFIX$DEFAULT_PREFIX/bin/
cp arpoison.8 $TEST_PREFIX$DEFAULT_PREFIX/share/man/man8/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 gcc | 上游 Makefile 使用 gcc | 使用 clang 替代 |
| 2 | libnet-config --defines 输出 | libnet-config 是 libnet conan 包提供的 | 直接调用获取编译参数 |

## 依赖版本

- libnet/1.2 (已发布到制品仓)

## 验证结果

```bash
$ file arpoison
arpoison: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ ./arpoison
Must be run as root
```

## 注意事项

- arpoison 需要 root 权限运行（运行时检查 getuid()）
- arpoison 没有测试套件，make check 不适用
- 构建产物是可执行文件，不是库
---

**编译结束**: 2026-08-14 16:04
**最终状态**: published

