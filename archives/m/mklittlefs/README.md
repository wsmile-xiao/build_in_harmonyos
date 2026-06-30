# mklittlefs

为 ESP8266/ESP32/Pico 微控制器创建 LittleFS 文件系统映像的命令行工具。

## 简介

mklittlefs 是一个命令行工具，用于创建（-c）、列出（-l）和解包（-u）LittleFS 文件系统映像。它在 Arduino/ESP8266/ESP32 生态系统中广泛使用，用于将文件系统内容打包为 flash 映像。

## 基本用法

```bash
# 创建映像
mklittlefs -c <源目录> -s <映像大小> <映像文件>

# 列出映像内容
mklittlefs -l <映像文件>

# 解包映像
mklittlefs -u <目标目录> <映像文件>
```

## 属性

- **主页**: https://github.com/earlephilhower/mklittlefs
- **许可证**: MIT
- **语言**: C/C++（内嵌 littlefs 库 v2.11.1）
- **构建系统**: 自定义 Makefile（非 autotools/cmake）
- **依赖**: 无外部依赖

## 已编译版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 4.1.0 | published | 2026-06-13 | HarmonyOS aarch64 预编译包 |

## HarmonyOS 适配要点

1. 源码为 zip 格式（非 tar.gz）
2. Makefile OS 检测需手动设 `TARGET_OS=linux64`
3. 无 git 仓库需手动设 `VERSION=4.1.0`
4. 编译后必须 ELF 签名才能在 HarmonyOS 上执行
5. 测试脚本 shebang `/bin/bash` 需适配
6. Makefile 无 install 目标，需手动安装
