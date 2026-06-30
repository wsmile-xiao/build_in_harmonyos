# sslscan 2.2.0-r0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 初始化编译环境：`ohc-run.py init-build sslscan 2.2.0-r0 --no-download`
2. 编译 sslscan，设置 RPATH：
```bash
make PREFIX=$DEFAULT_PREFIX \
    CFLAGS="-I$HOME/usr/local/include" \
    LDFLAGS="-L$HOME/usr/local/lib -Wl,-rpath,$HOME/usr/local/lib" \
    LIBS="-l:libssl.so.3 -l:libcrypto.so.3 -ldl -lpthread" \
    CC=clang
```
3. 安装到 staging 目录
4. 创建打包文件
5. 安装到本地

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接错误 undefined symbol: EVP_PKEY_get_id | libssl.so/libcrypto.so 符号链接指向 1.1 版本，而 sslscan 需要 OpenSSL 3.x API | 使用 `-l:libssl.so.3 -l:libcrypto.so.3` 直接链接到 .so.3 版本 |
| 2 | `install` 命令不存在 | 系统缺少 coreutils install 命令 | 手动用 `cp` 复制文件 |
| 3 | RPATH 未设置 | 默认 Makefile 不设置 RPATH | 通过 LDFLAGS 传递 `-Wl,-rpath,$HOME/usr/local/lib` |

## 源码修改

无补丁，仅通过编译参数解决依赖问题。

## 依赖版本

- OpenSSL 3.5.6 (已预安装在 ~/usr/local)

## 验证结果

```bash
# 检查 RPATH/RUNPATH
$ readelf -d ~/usr/local/bin/sslscan | grep RUNPATH
  0x000000000000001d (RUNPATH)  Library runpath: [/storage/Users/currentUser/usr/local/lib]

# 检查依赖库
$ readelf -d ~/usr/local/bin/sslscan | grep NEEDED
  0x0000000000000001 (NEEDED)   Shared library: [libssl.so.3]
  0x0000000000000001 (NEEDED)   Shared library: [libcrypto.so.3]
  0x0000000000000001 (NEEDED)   Shared library: [libc.so]

# 验证版本（无 LD_LIBRARY_PATH）
$ unset LD_LIBRARY_PATH && ~/usr/local/bin/sslscan --version
        2.2.0
        OpenSSL 3.5.6 7 Apr 2026
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sslscan-2.2.0-r0-x86_64.tar.gz | 218KB | 预编译包，包含 bin/sslscan 和 share/man/man1/sslscan.1 |

## 注意事项

1. 必须使用 `-l:libssl.so.3 -l:libcrypto.so.3` 而不是 `-lssl -lcrypto`，因为符号链接指向 1.1 版本
2. RUNPATH 设置为 `$HOME/usr/local/lib`，确保可以在无 LD_LIBRARY_PATH 环境下运行
3. 依赖 OpenSSL 3.5.6，用户需要预先安装 OpenSSL 3.x
---

**编译结束**: 2026-05-20 12:09
**最终状态**: built
