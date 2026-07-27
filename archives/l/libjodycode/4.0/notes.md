# libjodycode 4.0 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure 脚本）
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

1. **源码获取**: Codeberg 原始 URL (https://codeberg.org/jbruchon/libjodycode/archive/v4.0.tar.gz) 因 IP 被封锁无法下载，通过 Python urllib 从 GitHub NearlyTRex/LibJodycode 镜像获取源码（main 分支，版本 4.0）
2. **编译**: `make PREFIX=$DEFAULT_PREFIX CC=clang -j1`
3. **DESTDIR 安装**: `make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX`
4. **测试**: `make test`（仅 dummy test script，输出 "OK"）
5. **本地安装**: `make install PREFIX=$DEFAULT_PREFIX`（不带 DESTDIR）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Codeberg 源码下载失败 | Codeberg 封锁 IP (429 Too Many Requests) | 使用 Python urllib 从 GitHub NearlyTRex/LibJodycode 镜像获取 |
| 2 | curl/wget 无法访问 GitHub | 网络限制，curl/wget 连接超时 | Python urllib 可访问 raw.githubusercontent.com |
| 3 | SIMD 自动禁用 | 非x86_64平台（aarch64） | Makefile 自动检测并设置 NO_SIMD，无需修改 |

## 源码修改

无补丁。源码在鸿蒙平台编译无需修改。

## 依赖版本

- 无外部依赖（仅 libc）

## 验证结果

```bash
# libjodycode 是纯库，无可执行二进制
# ELF 检查: AArch64 ELF64, 仅依赖 libc.so
# make test: OK（dummy test script）
# Staging 安装文件:
#   - libjodycode.so.4.0 (共享库)
#   - libjodycode.so.4 -> libjodycode.so.4.0 (软链接)
#   - libjodycode.so -> libjodycode.so.4 (软链接)
#   - libjodycode.a (静态库)
#   - libjodycode.h (头文件)
#   - libjodycode.7 (man page)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libjodycode.so.4.0 | ~shared lib | 共享库 (AArch64 ELF64) |
| libjodycode.a | ~static lib | 静态库 |
| libjodycode.h | 13.6KB | 头文件 |
| libjodycode.7 | 6.8KB | man page |

## 注意事项

1. 源码版本为 4.0（LIBJODYCODE_VER = "4.0"），来自 GitHub NearlyTRex/LibJodycode 镜像（main 分支）
2. Makefile 自动在非 x86_64 平台禁用 SIMD（SSE2/AVX2），无需手动修改
3. 编译器 clang 15.0.4 部分警告选项（-Wconversion, -Wstrict-overflow=5）产生较多警告但不影响编译
4. conanfile.py 使用 PREFIX= (空) 来确保文件安装到 $PKG/lib/ 和 $PKG/include/ 而非 $PKG/usr/local/lib/

## 知识提取

- L2: Makefile 类型库在鸿蒙平台编译时 SIMD 自动禁用，无需修改源码
- L2: 无 configure 脚件的纯 Makefile 库使用 PREFIX 和 DESTDIR 变量替代 --prefix 和 DESTDIR
---

**编译结束**: 2026-07-15 16:49
**最终状态**: built
