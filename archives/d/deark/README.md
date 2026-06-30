# deark

> 文件格式转换与提取工具，支持多种老旧文件格式

## 软件信息

- **名称**: deark
- **描述**: A utility for extracting data from various file formats（文件格式数据提取工具）
- **主页**: https://entropymine.com/deark/
- **许可证**: MIT
- **语言**: C (C99)
- **构建系统**: Makefile（纯 Makefile，非 autotools）

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.7.2 | built | 2026-06-25 |

## 功能概述

deark 是一个命令行工具，用于从各种（特别是较老的）文件格式中提取数据。支持 362 个模块，涵盖：

- **归档格式**: ZIP、TAR、AR、ARJ、CAB、LHA、RAR、ZOO 等
- **图像格式**: GIF、BMP、PNG、JPEG、TIFF、ICO、PCX、TGA、ILBM 等
- **磁盘镜像**: Amiga ADF、Apple II DSK、HFS 等
- **其他格式**: ANSI Art、Amiga 图标、BinHex、MacBinary 等

## 编译说明

deark 使用纯 Makefile 构建系统，无 configure 脚本。

```bash
# 编译
make CC=clang CFLAGS="-fPIC -O2 -std=c99 -Wall -Wextra -Wmissing-prototypes -Wformat-security -Wno-unused-parameter" -j1

# 安装（注意：不要使用 make install，因其使用 -s strip 会丢失 ELF 签名）
install deark /usr/local/bin/deark
```

## 注意事项

- Makefile 的 `install` 目标使用 `-s`(strip) 标志，在鸿蒙上会导致 ELF 签名丢失，需手动使用不带 `-s` 的 `install` 命令
- 无外部依赖，自包含 C 程序
- 无 make check 目标，不包含测试套件
