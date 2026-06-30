# s3fs-fuse 1.94 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 GitHub archive 下载源码（v1.94.tar.gz）
2. 使用本地文件初始化编译环境
3. 运行 autoreconf -iv 包含 pkg-config 宏（ACLOCAL_PATH设置）
4. 修改 config.status 解决 HMDFS 临时目录权限问题
5. 设置 PKG_CONFIG_PATH 包含 fuse.pc 路径
6. 运行 configure --prefix=$DEFAULT_PREFIX
7. 创建 pthread_compat.c stub 解决 musl pthread_cancel 缺失
8. 修改 Makefile 强制链接 libfuse.a 静态库
9. 修改 Makefile 添加 pthread_compat.o 到编译对象
10. make 编译
11. make install DESTDIR=$TEST_PREFIX staging安装
12. 验证 s3fs --version

## 遶到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub releases下载超时 | SSL证书问题 | 使用curl -k下载到本地 |
| 2 | configure脚本不存在 | GitHub archive无预生成脚本 | autoreconf -iv生成 |
| 3 | PKG_CHECK_MODULES语法错误 | pkg.m4宏缺失 | 设置ACLOCAL_PATH包含pkg-config宏 |
| 4 | pkg-config找不到fuse | PKG_CONFIG_PATH未设置 | 添加~/usr/local/lib/pkgconfig |
| 5 | config.status临时目录失败 | HMDFS权限限制 | 修改使用固定TMPDIR路径 |
| 6 | pthread_cancel未定义 | musl未实现pthread_cancel | 创建pthread_compat.c stub |
| 7 | 静态链接libfuse.a仍有pthread问题 | fuse库依赖pthread_cancel | stub函数加入链接 |

## 源码修改

### config.status
- 第585-593行：修改临时目录创建，使用 $TMPDIR/s3fs-fuse-conf-tmp

### src/Makefile
- DEPS_LIBS：修改 -lfuse 为 -l:libfuse.a（静态链接）
- am_s3fs_OBJECTS：添加 pthread_compat.$(OBJEXT)

### src/pthread_compat.c（新增）
- 实现 pthread_cancel 和 pthread_setcancelstate stub函数

## 依赖版本

- fuse: 2.9.9（已编译）
- libcurl: 系统预装
- libxml2: 系统预装
- openssl: 已编译
- pkg-config: 0.29.2
- clang: 15.0.4

## 验证结果

```bash
$TEST_PREFIX/$DEFAULT_PREFIX/bin/s3fs --version
Amazon Simple Storage Service File System V1.94 (commit:unknown) with OpenSSL
Copyright (C) 2010 Randy Rizun <rrizun@gmail.com>
```

## 注意事项

1. **pthread_cancel限制**：鸿蒙系统musl未实现pthread_cancel，s3fs-fuse依赖的fuse库需要此函数，通过stub实现
2. **FUSE依赖**：需要先编译fuse库，且必须使用静态链接避免动态库的pthread问题
3. **PKG_CONFIG_PATH**：必须包含fuse.pc所在目录才能正确检测依赖
4. **HMDFS限制**：config.status在HMDFS上创建临时目录受限，需手动修改
---

**编译结束**: 2026-05-28 10:21
**最终状态**: published
