# ipopt 3.14.19 编译笔记

## 编译环境

- **平台**: OpenHarmony (aarch64)
- **编译日期**: 2026-05-29
- **构建系统**: autotools

## 依赖

- OpenBLAS 0.3.26 (USE_THREAD=0, NO_FORTRAN=1)

## 编译步骤

### 1. 源码下载

使用 GitHub 加速镜像：
```
URL: https://ghfast.top/https://github.com/coin-or/Ipopt/archive/refs/tags/releases/3.14.19.tar.gz
```

### 2. 平台适配

- 应用 config.guess.patch：识别 OpenHarmony 系统
- 应用 config.sub.patch：支持 aarch64-unknown-linux-ohos triplet

### 3. Configure

```bash
./configure --prefix=$HOME/usr/local \
  --with-lapack-lflags="-L$HOME/usr/local/lib -lopenblas"
```

### 4. 编译

```bash
make -j2
```

### 5. 安装

```bash
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题

### 问题 1: OpenBLAS pthread_setaffinity_np

**描述**: 之前安装的 OpenBLAS 使用了 pthread_setaffinity_np，导致链接失败

**解决**: 重新编译 OpenBLAS 使用 USE_THREAD=0 禁用多线程

### 问题 2: LAPACK 检测

**描述**: OpenBLAS 使用 NO_FORTRAN=1，configure 无法通过 pkg-config 检测 LAPACK

**解决**: 使用 --with-lapack-lflags 手动指定库路径

## 产物

- libipopt.so.3.14.19 (2.3MB)
- libsipopt.so.3.14.19 (211KB)

## 验证

```bash
pkg-config --modversion ipopt
# 输出: 3.14.19
```
