# scamp 2.15.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-02
- 编译器: clang (OHOS aarch64)
- 状态: built

## 编译步骤

```bash
# 1. 生成 configure（GitHub 源码包无预生成 configure）
#    注意: 需 automake/libtool/autoconf/perl，且本机 automake 包装器损坏，用 automake-1.16
./autogen.sh

# 2. configure（FFTW/OpenBLAS/cURL 均给出显式路径）
./configure --prefix=$DEFAULT_PREFIX \
  --with-fftw-incdir=/storage/Users/currentUser/usr/local/include \
  --with-fftw-libdir=/storage/Users/currentUser/usr/local/lib \
  --enable-openblas \
  --with-openblas-incdir=/storage/Users/currentUser/usr/local/include/openblas \
  --with-openblas-libdir=/storage/Users/currentUser/usr/local/lib \
  --with-curl-incdir=/storage/Users/currentUser/usr/local/include \
  --with-curl-libdir=/storage/Users/currentUser/usr/local/lib

# 3. 编译 + 测试
make -j2
make check   # 5/5 PASS
```

> 环境坑: 本机 `mktemp -d` 创建的临时目录内无法写文件（config.status 失败 Permission denied），
> 需在 PATH 前置一个 `mktemp` shim（exit 1）强制 config.status 走 mkdir 回退分支。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 FFTW 单精度库缺失 | 预编译 fftw 包只有双精度 libfftw3 | 从制品仓 fftw3f/3.3.9.1 取 libfftw3f.so 补入 /usr/local/lib |
| 2 | configure 报 ATLAS 头文件缺失 | cmd-pkgs 的 atlas 包是命令行工具非 BLAS 库 | 改 --enable-openblas，从制品仓 openblas/0.3.34 取库和头文件 |
| 3 | configure 硬性要求 cURL | ACX_CURL 失败即 AC_MSG_ERROR | 安装 cmd-pkgs curl 8.19.0 预编译包 |
| 4 | make 报 `M_MMAP_MAX` 未声明 | glibc 专属 mallopt 参数，OHOS musl libc 无 | src/prefs.c 增加 `#ifdef M_MMAP_MAX` 守卫 |
| 5 | 链接缺 libssl/libcrypto | curl 依赖，系统仅有 .so.3 无未版本软链 | ln -s 建立 libssl.so/libcrypto.so/libz.so 符号链接 |
| 6 | make check 测试链接失败 `error` 未定义 | error() 由 src/fits/fitsmisc.c 定义，tests 的 LDADD 漏链 libfits.a（glibc 靠 libc 兜底，musl 无） | tests/Makefile.am 给 test_chealpix/test_chealpixstore 补 libfits.a |
| 7 | test_integration01.py 126 退出 | shebang `#! /usr/bin/python3` 指向不存在路径 | 改为 `#!/usr/bin/env python3` |
| 8 | 集成测试 0 有效源（全部源被过滤） | `fflag` 仅在有 `HAVE_ISNAN2`（glibc）时赋值；OHOS musl 的 isnan 是宏非函数，configure 检测失败 → 未初始化随机值过滤全部源 | src/samples.c 增加 `#else fflag = 0;` 分支 |

## 源码修改

- `src/prefs.c`: mallopt(M_MMAP_MAX) 增加 `#ifdef M_MMAP_MAX` 守卫（OHOS musl 无此 glibc 参数）
- `src/samples.c`: `#ifdef HAVE_ISNAN2` 增加 `#else fflag = 0;`（防止未初始化过滤全部源）
- `tests/Makefile.am`: test_chealpix/test_chealpixstore 的 LDADD 补充 `$(top_builddir)/src/fits/libfits.a`（提供 error() 符号）
- `tests/test_integration01.py`: shebang 改为 `#!/usr/bin/env python3`

## 依赖版本

- fftw 3.3.10（双精度，cmd-pkgs）+ fftw3f 3.3.9.1（单精度，conan 制品仓）
- openblas 0.3.34（conan 制品仓）
- curl 8.19.0（cmd-pkgs）
- automake 1.16.5 / libtool 2.4.7 / autoconf 2.72 / perl 5.42.2（cmd-pkgs）
- numpy / astropy（pip，测试用）

## 验证结果

```bash
make check
# TOTAL: 5  PASS: 5  FAIL: 0
# PASS: test_chealpix, test_chealpixstore, test_crossid_single_catalog,
#       test_crossid_single_catalog_moving, test_integration01.py
```

## 注意事项

- 需在 PATH 前置 mktemp shim 规避 config.status 临时目录权限问题
- 需用 automake-1.16（默认 automake 包装器指向缺失的 1.17 目录）
---

**编译结束**: 2026-08-02 04:24
**最终状态**: built
