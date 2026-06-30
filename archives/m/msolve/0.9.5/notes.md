# msolve v0.9.5 编译笔记

## 编译日期
2026-06-16

## 编译状态
built

## 编译环境
- **平台**: OpenHarmony (aarch64-unknown-ohos)
- **编译器**: clang/clang++
- **构建系统**: autotools
- **安装路径**: ~/usr/local

## 编译步骤

### 1. 源码准备
下载 msolve 0.9.5 源码包并解压到 ~/tmp/builds/msolve-0.9.5/

### 2. 依赖准备
- GMP 6.3.0 (静态库，已编译)
- MPFR 4.2.1 (静态库，已编译)
- FLINT 3.5.0 (静态库，已编译)

### 3. 配置修改

#### E011 - HMDFS umask 077 修复
```bash
sed -i 's/umask 077/umask 022/g' configure
```

#### E007 - config.guess 更新
使用已更新的 config.guess/config.sub（从 FLINT/GMP 复制）

### 4. Configure
```bash
./configure --prefix=$DEFAULT_PREFIX \
    --with-gmp=$DEFAULT_PREFIX \
    --with-mpfr=$DEFAULT_PREFIX \
    --with-flint=$DEFAULT_PREFIX \
    --disable-shared \
    --enable-static
```

### 5. 编译与安装
```bash
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 问题与解决方案

### 问题 1: E011 - HMDFS umask 077
- **描述**: HMDFS 文件系统 umask 077 导致临时文件创建失败
- **解决方案**: 修改 configure 中的 `umask 077` 为 `umask 022`

### 问题 2: E007 - config.guess 不支持 OpenHarmony
- **描述**: config.guess 无法识别 `aarch64-unknown-ohos`
- **解决方案**: 使用已更新的 config.guess/config.sub（从 FLINT 复制）

### 问题 3: P002 - GMP 静态库 PIC 问题
- **描述**: GMP 静态库编译时未使用 -fPIC，导致链接共享库时报错
- **解决方案**: 使用 `--disable-shared --enable-static` 禁用共享库构建
- **影响**: FLINT 和 msolve 都需要相同处理

## 最终产物
- libmsolve.a
- msolve (可执行文件)
- include/msolve/*.h

## 依赖版本
- GMP 6.3.0 (静态库)
- MPFR 4.2.1 (静态库)
- FLINT 3.5.0 (静态库)

## 验证结果
```bash
msolve --version
# 输出: msolve version 0.9.5
```

---
**编译结束**: 2026-06-16 11:54
**最终状态**: built (预编译包已制作)
