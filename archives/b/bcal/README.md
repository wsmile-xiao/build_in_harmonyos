# bcal

## 简介

bcal（Byte CALculator）是一个存储表达式计算器，支持字节单位换算、混合运算、基数转换和位运算。

## 功能概述

- **字节单位计算**：支持 B/KiB/MiB/GiB/TiB/kB/MB/GB/TB 等单位的混合运算
- **基数转换**：将数字转换为二进制、十进制、十六进制表示
- **位运算**：支持 AND(&)、OR(|)、XOR(^)、左移(<<)、右移(>>) 操作
- **通用表达式模式**：切换到数学表达式模式，支持 pow() 等函数
- **REPL 交互模式**：支持交互式输入，按 `q` 或双回车退出
- **CHS/LBA 转换**：支持磁盘寻址方式转换

## OHOS 适配

- 纯 Makefile 项目，无 configure 脚本，通过 `make PREFIX=...` 编译安装
- 依赖 readline 库（需安装 readline 8.2 预编译包以获取头文件和库文件）
- 编译时 Makefile 包含 `-Werror`，在 clang 15 下无警告可直接编译通过
- 无需任何源码修改即可在 OHOS 上编译运行
- bcal 不支持 `--version` 参数（返回 exit 255），使用 `-h` 查看版本信息
- 动态依赖：libreadline.so.8、libc.so（musl）

## 依赖

### 编译依赖
- readline 8.2（头文件 + 库文件）

### 运行依赖
- libreadline.so.8（运行时需 readline 预编译包）
- musl libc

## 功能验证

```bash
# 字节计算
bcal -m 10 mb           # → 10000000 B
bcal -m 1 kib           # → 1024 B

# 基数转换
bcal -c 255             # → (b) 11111111 (d) 255 (h) 0xff

# 位运算
bcal -m "5 & 3"         # → 1

# 版本确认
bcal -h | grep Version  # → Version 2.5
```

## 参考

- 源码仓库：https://github.com/jarun/bcal
- 许可证：GPLv3
