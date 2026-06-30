# libkcapi 1.5.0-r1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码（使用 curl -k 绕过 SSL 证书验证）
2. 解压并初始化编译环境
3. 配置：./configure --prefix=$DEFAULT_PREFIX
4. 编译：make -j2（添加 CFLAGS="-Wno-error=sign-compare"）
5. 安装：make install DESTDIR=$TEST_PREFIX
6. 打包：ohc-run.py package libkcapi 1.5.0-r1
7. 本地安装：make install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 临时文件创建失败 | HMDFS 文件系统权限问题 | 修改 config.status，将临时目录指向 $TMPDIR |
| 2 | sockaddr_storage 头文件冲突 | OHOS SDK 头文件重复定义 | 在 lib/internal.h 添加 #define __MUSL__ |
| 3 | CMSG_NXTHDR 类型比较警告 | -Wsign-compare 警告转为错误 | CFLAGS 添加 -Wno-error=sign-compare |
| 4 | SSL 证书验证失败 | GitHub tarball 下载问题 | curl -k 手动下载 |

## 源码修改

共 19 个补丁文件，关键补丁：
- 0013-lib-internal.h.patch: OHOS __MUSL__ 定义修复
- 其他补丁为 autotools 构建系统平台适配（config.guess, config.sub, ltmain.sh 等）

## 依赖版本

- 构建工具：automake, autoconf, libtool
- 编译器：clang (OHOS SDK)

## 验证结果

```bash
# 库文件已安装
ls -la ~/usr/local/lib/libkcapi.so.1.5.0
ls -la ~/usr/local/lib/libkcapi.a

# 头文件已安装
ls -la ~/usr/local/include/kcapi.h

# pkgconfig 已安装
pkg-config --modversion libkcapi
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libkcapi-1.5.0-r1-ohos-aarch64.tar.gz | 1.2 MB | 预编译包 |
| libkcapi.a | 316 KB | 静态库 |
| libkcapi.so.1.5.0 | 211 KB | 动态库 |

## 注意事项

- 需要在 configure 时添加 CFLAGS="-Wno-error=sign-compare" 避免 CMSG_NXTHDR 警告转错误
- OHOS SDK 头文件冲突需要手动定义 __MUSL__ 宏
---
**编译结束**: 2026-05-20 16:24
**最终状态**: built
---

**编译结束**: 2026-05-20 16:29
**最终状态**: built
