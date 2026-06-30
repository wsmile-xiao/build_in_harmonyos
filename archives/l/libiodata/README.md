# libiodata

## 简介

libiodata 是一个基于 Qt 的数据语言库，主要用于输入法配置文件的解析和处理。它是 Sailfish OS 输入法框架的组成部分。

## 功能概述

- 数据语言解析器（datalang parser）
- Qt 集成的配置文件处理
- 支持输入法配置文件的读写
- 提供易于使用的 C++ API

## OHOS 适配要点

1. **Qt 安装问题**：当前 Qt 安装不完整，缺少 mkspecs/features 目录，qmake 无法正常工作
2. **手动编译方案**：使用 flex/bison 生成解析器，然后用 clang++ 手动编译所有源文件
3. **环境变量**：需要设置 QT_INCLUDE 和 QT_LIB 指向 Qt5 的头文件和库目录
4. **版本号设置**：通过 IODATA_VERSION 环境变量设置版本号

## 依赖关系

### 编译依赖
- flex >= 2.6.4（词法分析器生成器）
- bison >= 3.8.2（语法分析器生成器）
- Qt5 >= 5.15.2（Qt5Core 模块）

### 运行依赖
- Qt5Core

## 编译方法（手动编译）

```bash
# 设置环境变量
export QT_INCLUDE=/path/to/qt/include
export QT_LIB=/path/to/qt/lib
export IODATA_VERSION=0.19.14

# 生成解析器
bison -v -d -o parser.cpp datalang.y
flex -o tokens.cpp datalang.l

# 编译源文件
clang++ -std=c++14 -fPIC -I$QT_INCLUDE -I$QT_INCLUDE/QtCore -DQT_CORE_LIB -c *.cpp

# 创建共享库
clang++ -shared -o libiodata-qt5.so.0.19.14 *.o -L$QT_LIB -lQt5Core -Wl,-rpath,$QT_LIB

# Strip 优化
llvm-strip libiodata-qt5.so.0.19.14

# 创建符号链接
ln -sf libiodata-qt5.so.0.19.14 libiodata-qt5.so
ln -sf libiodata-qt5.so.0.19.14 libiodata-qt5.so.0
```

## 参考资料

- 官方仓库：https://github.com/sailfishos/libiodata