# Shapelib 1.5.0 编译笔记

## 编译环境
- 系统: HarmonyOS (HongMeng Kernel 1.12.0)
- 架构: aarch64
- 构建系统: CMake 4.1.2
- 编译器: Clang 15.0.4

## 编译过程

### 2026-05-26 编译记录

#### 问题1: Autotools 构建失败
**现象**: configure 运行时 config.status 无法创建临时文件
```
./config.status[1021]: can't create ./confNBMeLl/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**分析**: HMDFS 文件系统对临时子目录创建有限制，autotools 的 config.status 在尝试创建临时目录时遇到权限问题。

**解决**: 改用 CMake 构建系统

#### 问题2: config.guess 无法识别 HarmonyOS
**现象**: 
```
config.guess: unable to guess system type
config.guess timestamp = 2015-08-20
```

**解决**: 从 automake-1.16 安装目录复制更新的 config.guess/config.sub (2023-08-22 版本)

#### 问题3: CMake 版本兼容性
**现象**: 
```
CMake Error at CMakeLists.txt:29 (cmake_minimum_required):
  Compatibility with CMake < 3.5 has been removed from CMake.
```

**原因**: CMakeLists.txt 中 cmake_minimum_required(VERSION 2.8.5) 太旧

**解决**: 
1. 将 cmake_minimum_required 移到 project() 之前
2. 更新版本为 VERSION 3.5

#### 问题4: LOCATION 属性废弃
**现象**: 
```
CMake Error at CMakeLists.txt:179 (get_target_property):
  The LOCATION property may not be read from target "shpcreate".
```

**原因**: CMake 4.x 完全废弃了 LOCATION 属性

**解决**: 注释掉使用 LOCATION 属性的测试代码块

## 构建结果

### 产物
- 静态库: libshp.a (74KB)
- 可执行文件: shpcreate, shpadd, shpdump, shprewind, dbfcreate, dbfadd, dbfdump, shptreedump
- 头文件: shapefil.h
- CMake 配置: share/shp/export_shp.cmake

### 验证
```bash
$ ~/usr/local/bin/shpcreate --help
shpcreate shp_file [point/arc/polygon/multipoint][/m/z]

$ ~/usr/local/bin/shpdump --help
shpdump [-validate] [-ho] [-precision number] shp_file
```

## 补丁文件
- 0001-update-config.guess.patch: 更新 config.guess 支持 HarmonyOS
- 0002-update-config.sub.patch: 更新 config.sub 支持 HarmonyOS
- 0003-fix-cmake-compatibility.patch: 修复 CMake 4.x 兼容性问题

## 编译结束
**最终状态**: built
**制品包**: shapelib-1.5.0-ohos-aarch64.tar.gz
---

**编译结束**: 2026-05-26 11:28
**最终状态**: built
