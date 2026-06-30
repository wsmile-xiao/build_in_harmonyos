# John the Ripper 1.9.0-jumbo-1 编译笔记

## 编译环境
- 目标平台: aarch64-linux-gnu (HarmonyOS)
- 编译器: gcc (clang 15.0.4)
- 构建系统: Makefile.legacy (autotools configure 无法正常工作)

## 依赖
- OpenSSL 1.1.1w (预编译包)

## 遇到的问题

### 1. configure 无法运行
- config.guess 无法识别 HarmonyOS
- config.status 无法创建临时文件 (权限问题)
- 解决方案: 使用 Makefile.legacy 直接编译

### 2. OpenSSL 链接问题
- 预编译的 OpenSSL 库使用 FORTIFY_SOURCE，导致 `__fd_chk` 未定义
- 解决方案: 使用 `-Wl,--allow-shlib-undefined` 链接器选项

### 3. SIMD 编译问题
- NEON vroti_epi32 宏在 clang 下编译失败
- 解决方案: 使用 `-DJOHN_NO_SIMD` 禁用 SIMD

## 编译命令
```bash
cd src
make -f Makefile.legacy linux-arm64le \
    CFLAGS="-I/path/to/openssl/include -DJOHN_NO_SIMD" \
    LDFLAGS="-L/path/to/openssl/lib -Wl,--allow-shlib-undefined -lssl -lcrypto"
```

## 测试结果
- make test: 通过 (基准测试正常运行)
---

**编译结束**: 2026-06-10 11:42
**最终状态**: built
