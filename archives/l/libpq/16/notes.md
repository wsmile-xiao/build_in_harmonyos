# libpq 16 适配笔记

## 编译环境
- 构建系统: autoconf
- 编译日期: 2026-05-27
- 编译器: clang 15.0.4 (HarmonyOS LLVM)
- 状态: published

## 编译步骤

1. 源码下载：postgresql-16.2.tar.gz (31MB)
2. VPATH构建：在~/tmp/libpq-build目录执行configure
3. configure：
   ```bash
   ../configure --prefix=$HOME/usr/local --without-readline --without-zlib --without-icu --disable-nls
   ```
4. 编译：`make -j$(nproc)`
5. 安装：`make install DESTDIR=$TEST_PREFIX`
6. 打包：`ohc-run.py package libpq 16`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson构建失败 | meson无法识别编译器路径 | 改用autoconf方式 |
| 2 | HMDFS权限问题 | SELinux限制 | VPATH构建 + sed修改umask |
| 3 | ICU库缺失 | configure检测到依赖 | --without-icu |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libpq-16-ohos-aarch64.tar.gz | 627KB | 预编译包 |
| libpq.so.5.16 | 321KB | 动态库 (ELF arm64) |
| libpq.a | 243KB | 静态库 |

## 验证结果

```bash
$ pkg-config --modversion libpq
16

$ nm -D libpq.so.5.16 | grep PQconnectdb
0000000000048a70 T PQconnectdb
```