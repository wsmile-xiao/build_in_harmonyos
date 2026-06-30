# libusbgx 0.3.0 编译笔记

## 编译日期
2026-06-12

## 编译环境
- 系统: OpenHarmony (aarch64)
- 编译器: clang 15.0.4
- 构建系统: autoconf

## 编译过程

### 依赖
- libconfig >= 1.4 (已安装)

### 编译步骤
1. autoreconf -fi (生成 configure)
2. ./configure --prefix=$DEFAULT_PREFIX
3. make -j2
4. make install DESTDIR=$TEST_PREFIX

### 遇到的问题

#### 问题1: libconfig.h 头文件找不到
- 原因: PKG_CONFIG_PATH 未设置
- 解决: export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig"

#### 问题2: libconfig.so 软链接缺失
- 原因: libconfig 安装时未创建 .so 软链接
- 解决: ln -s libconfig.so.11.1.0 libconfig.so

### 编译结果
- 状态: built
- 产物: libusbgx.so.3.0.0, libusbgx.a
- 头文件: include/usbg/usbg.h

## 知识提取
- 无新知识发现（常规 autoconf 项目编译）
