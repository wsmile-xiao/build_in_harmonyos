# MPIR (Multiple Precision Integers and Rationals)

## 简介
MPIR 是源自 GMP 的高精度数学库，提供任意精度整数（mpz）、有理数（mpq）和浮点数（mpf）运算，
是 FLINT、NTL、PARI 等计算代数软件的基础依赖。

## 基本信息
- 官网: https://mpir.org/
- 源码: https://github.com/wbhart/mpir
- 许可证: LGPL-3.0-or-later OR GPL-2.0-or-later
- 构建系统: autotools

## 已编译版本
- 3.0.0 (2026-09-17) —— 开启 --enable-cxx，提供 libmpir / libmpirxx

## 依赖
无运行库依赖（纯 C 实现）；构建期 tool_requires：automake/1.18、libtool/2.5.4.1
（GitHub tag 归档自举用，均为制品仓已发布条目；autoconf/autom4te/m4/perl 由
设备 HNP 公共目录提供，配方内显式钉定）。

## 使用方式
```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- mpir 3.0.0

# 编译链接（C）
clang your_program.c -I$HOME/usr/local/include -L$HOME/usr/local/lib -lmpir

# 编译链接（C++ 接口）
clang++ your_program.cpp -I$HOME/usr/local/include -L$HOME/usr/local/lib -lmpirxx -lmpir
```
