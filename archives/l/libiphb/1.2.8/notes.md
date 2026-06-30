# libiphb 1.2.8 编译笔记

## 编译日期
2026-06-04

## 源码来源
libiphb 1.2.8

## 构建系统
autotools (需要 autoreconf -fiv 生成 configure)

## 依赖
- glib-2.0 (已安装)
- dbus-1 (已安装)

## 移除的依赖（Sailfish OS 特有）
- mce (Mode Control Entity)
- libdsme (Device State Management Entity)

## 编译过程

### Step 1: 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libiphb 1.2.8
```

### Step 2: 生成 configure 脚本
源码包没有预生成的 configure 脚本，需要运行：
```bash
cd $BUILD_SRC_DIR
autoreconf -fiv
```

### Step 3: 配置和编译
```bash
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
```

### Step 4: 打包
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package libiphb 1.2.8
```

## 补丁说明

### 0001-INSTALL.patch
更新 INSTALL 文档

### 0002-Makefile.am.patch
移除 dbus-gmain 子目录构建

### 0003-configure.ac.patch
- 移除 PKG_CHECK_MODULES(MCE, mce)
- 移除 AC_CHECK_LIB([dsme])
- 移除 dbus-gmain/Makefile

### 0004-src-Makefile.am.patch
调整库构建配置

### 0005-src-iphb_internal.h.patch
移除 MCE 相关头文件依赖

## 质量检查结果

| 门禁 | 状态 | 说明 |
|------|------|------|
| G0 | FAIL | 需要 autoreconf，原始 tarball 无 configure |
| G1 | PASS | 二进制完整性通过 |
| G2 | PASS | 功能可用性通过（无可执行测试） |
| G3 | PASS | 可移植性通过 |
| G4 | PASS | 归档完整性通过 |

## 预编译包
- libiphb-1.2.8-ohos-aarch64.tar.gz (254KB)
- libiphb-1.2.8-ohos-aarch64-debug.tar.gz (99KB)

## 知识提取
- E019: autotools 项目无 configure 需 autoreconf