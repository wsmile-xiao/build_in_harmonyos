# GMP (GNU Multiple Precision Arithmetic Library)

## 简介
GMP 是 GNU 高精度数学运算库，提供任意精度的整数、分数和浮点数运算功能。

## 基本信息
- 官网: https://gmplib.org/
- 源码: https://ftp.gnu.org/gnu/gmp/
- 许可证: LGPLv3 / GPLv2
- 构建系统: autotools

## 已编译版本
- 6.3.0.1 (2026-08-12) —— 开启 --enable-cxx，提供 gmpxx C++ 接口
- 6.3.0 (2026-05-18)

## 依赖
无外部依赖（纯 C 实现）

## 使用方式
```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- gmp 6.3.0

# 编译链接
clang -fuse-ld=bfd your_program.c -I$HOME/usr/local/include -L$HOME/usr/local/lib -lgmp
```
