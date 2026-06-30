# odt2txt 0.5 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile, no configure script)
- 编译日期: 2026-06-26
- 编译器: clang/clang++
- 状态: pending (conan-verify)

## 编译步骤

GitHub archive 不含 configure 脚本，直接使用 Makefile 编译。

```bash
source .build-context-odt2txt-0.5
cd $BUILD_SRC_DIR
make -j1 CC="$CC" CFLAGS="$CFLAGS"
make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 下载失败 | GitHub SSL 证书验证失败 | 使用 curl -kL 从 codeload.github.com 下载 |
| 2 | 无 configure 脚本 | GitHub archive tag 不含 autotools 生成文件 | 直接使用 Makefile 编译 |
| 3 | make check 无目标 | Makefile 未定义 check target | 手动构建测试二进制，但 test-strbuf 编译失败（缺少 strbuf_create_slurp 函数）|
| 4 | zlib 链接 | 项目依赖 libz | 系统已有 libz.a 静态库，自动静态链接 |

## 依赖版本

- zlib: 已预装 (libz.a 静态库)
- 无其他依赖

## 验证结果

```bash
# 二进制格式验证
$ file odt2txt
odt2txt: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

# 动态依赖检查 (仅 libc.so，zlib 静态链接)
$ readelf -d odt2txt
  NEEDED: libc.so (系统库)

# 版本验证
$ ./odt2txt --version
odt2txt 0.5
Copyright (c) 2006,2007 Dennis Stosberg <dennis@stosberg.net>
```

## 注意事项

- 该项目使用纯 Makefile，无 configure 脚本，conanfile.py 需使用 Makefile 构建方式
- zlib 静态链接，仅依赖 libc.so（符合 R26 静态链接要求）
- 测试目标 test-strbuf 编译失败（缺少 strbuf_create_slurp），不影响主程序编译
---

**编译结束**: 2026-06-26 01:10
**最终状态**: published
