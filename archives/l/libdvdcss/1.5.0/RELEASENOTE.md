# Release Notes — libdvdcss 1.5.0

**发布日期**: 2026-05-11  
**版本**: 1.5.0  
**平台**: OpenHarmony aarch64  
**编译器**: Clang 15.0.4

---

## 概述

libdvdcss 是一个用于访问 DVD 的跨平台库，能够解密 DVD 内容以便合法使用。此版本为 OpenHarmony 平台编译。

## 编译信息

### 构建系统
- **工具**: Meson 1.11.0 + Ninja 1.11.1
- **编译器**: Clang 15.0.4
- **C 标准**: C17
- **优化级别**: debugoptimized

### 编译选项
- `buildtype=debugoptimized` - 调试优化构建
- `c_std=c17` - C17 标准支持
- `default_library=both` - 同时构建动态库和静态库
- `warning_level=2` - 中等警告级别

### 平台特性
- ✅ Linux DVD 结构支持
- ✅ POSIX 兼容
- ✅ 函数可见性属性支持

## 安装包内容

### 主安装包
**文件**: `libdvdcss-1.5.0-ohos-aarch64.tar.gz`  
**大小**: 497 KB

#### 包含文件

**库文件**
- `lib/libdvdcss.so.2.3.0` - 动态库 (主库)
- `lib/libdvdcss.so.2` - 符号链接 (soname)
- `lib/libdvdcss.so` - 符号链接 (开发链接)
- `lib/libdvdcss.a` - 静态库

**头文件**
- `include/dvdcss/dvdcss.h` - 主头文件
- `include/dvdcss/dvdcpxm.h` - CPXM 扩展头文件
- `include/dvdcss/version.h` - 版本信息头文件

**开发文件**
- `lib/pkgconfig/libdvdcss.pc` - pkg-config 文件

**文档**
- `share/doc/libdvdcss/AUTHORS` - 作者列表
- `share/doc/libdvdcss/COPYING` - 许可证 (GPL)
- `share/doc/libdvdcss/NEWS` - 更新日志
- `share/doc/libdvdcss/README.md` - 说明文档

### 调试符号包
**文件**: `libdvdcss-1.5.0-ohos-aarch64-debug.tar.gz`  
**大小**: 342 KB

包含调试符号文件，用于开发和调试。

### 安装脚本
**文件**: `install-libdvdcss-1.5.0.sh`  
自动化安装脚本，将库文件安装到系统目录。

## 依赖

**无外部依赖**

libdvdcss 是一个独立的库，不需要额外的依赖库。

## 安装方法

### 方法 1: 使用安装脚本
```bash
tar -xzf libdvdcss-1.5.0-ohos-aarch64.tar.gz
cd libdvdcss-1.5.0
./install-libdvdcss-1.5.0.sh
```

### 方法 2: 手动安装
```bash
tar -xzf libdvdcss-1.5.0-ohos-aarch64.tar.gz
cp -r libdvdcss-1.5.0/* /usr/local/
ldconfig
```

### 使用 pkg-config
```bash
export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
pkg-config --cflags --libs libdvdcss
```

## 验证安装

检查动态库:
```bash
ls -l /usr/local/lib/libdvdcss.so*
```

检查头文件:
```bash
ls -l /usr/local/include/dvdcss/
```

使用 pkg-config 检查:
```bash
pkg-config --modversion libdvdcss
```

## 质量检查

| 检查项 | 结果 |
|--------|------|
| G1 二进制完整性 | ✅ 通过 |
| G2 功能可用性 | ✅ 通过 (1个预期警告) |
| G3 可移植性 | ✅ 通过 |
| G4 档案完整性 | ✅ 通过 |

## 已知问题

无已知问题。

## 许可证

GNU General Public License (GPL)

## 源码

- **来源**: libdvdcss-1.5.0.tar.xz
- **官方站点**: https://www.videolan.org/developers/libdvdcss.html

## 维护者

OpenHarmony 编译框架自动生成