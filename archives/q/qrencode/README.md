# libqrencode

## 软件简介

libqrencode 是一个快速且紧凑的 QR 码生成库。QR 码是一种二维条码,可以嵌入最大约7000个数字字符或约4000个字母数字字符,并具有优秀的错误纠正能力。

## 编译版本

- 4.1.1 (2026-05-25)

## 主要功能

- 高速符号生成
- 数据列的自动分析
- 运行时不需要外部文件
- QR 码模型2生成(JIS X0510:2004)

## 编译配置

### 4.1.1 版本

- 构建系统: CMake 4.1.2
- 编译器: Clang 15.0.4
- 配置选项:
  - `-DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local`
  - `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
  - `-DWITH_TESTS=YES`
  - `-DWITHOUT_PNG=YES` (禁用 PNG 支持以避免依赖)

## 依赖

### 运行时依赖
无(PNG 支持已禁用)

### 构建依赖
- libtool 2.4.7 (用于 autotools bootstrap)
- sed 4.10 (GNU sed,用于 autotools)

## 安装使用

安装后可通过以下命令使用:

```bash
qrencode --version
qrencode -o output.txt "Hello World"  # 生成文本格式 QR 码
```

注意: PNG 输出已禁用,仅支持文本和 ANSI 输出格式。

## 许可证

GNU Lesser General Public License (LGPL) version 2.1 or later

Copyright (C) 2006-2017 Kentaro Fukuchi

## 相关链接

- 官方网站: https://fukuchi.org/works/qrencode/
- GitHub: https://github.com/fukuchi/libqrencode