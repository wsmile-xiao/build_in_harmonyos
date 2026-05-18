# Polipo

**Polipo 是一个轻量级的 HTTP 代理缓存服务器**

## 软件描述

Polipo 是一个小巧、快速的 HTTP 代理服务器，具有以下特性：
- HTTP 缓存代理功能
- 支持 IPv4 和 IPv6
- 内容过滤能力
- 适合个人或小型网络使用

## 基本信息

- **作者**: Juliusz Chroboczek
- **许可证**: MIT/GPL
- **主页**: https://www.pps.jussieu.fr/~jch/software/polipo/
- **下载**: https://download.savannah.nongnu.org/releases/polipo/

## 版本信息

### polipo 1.1.1

- **发布日期**: 2014-05-14
- **状态**: published ✅
- **特点**: 
  - 修复 SOCKS 服务器连接崩溃问题
  - 修复隧道模式无限循环问题
  - Windows 端口改进

## 依赖关系

Polipo 无特殊依赖，仅需标准 C 库：
- libc (musl)
- 标准 socket API

无外部库依赖，完全自包含。

## 构建系统

Polipo 使用纯 Makefile 构建系统：
- 无 configure 脚本
- 使用 PREFIX 变量控制安装路径
- 使用 TARGET 变量作为 DESTDIR

## 安装使用

### 通过预编译包安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- polipo 1.1.1
```

### 手动编译

```bash
# 编译
make CC=clang PREFIX=/usr/local all

# 安装
make install PREFIX=/usr/local
```

## 配置示例

创建配置文件 `~/.polipo`：

```
proxyAddress = "127.0.0.1"
proxyPort = 8123
cacheIsShared = false
diskCacheRoot = ""
```

## 鸿蒙适配要点

1. **构建系统**: 纯 Makefile 项目，无 configure 脚本
2. **编译器**: 使用 clang，支持 CFLAGS 自定义
3. **依赖**: 无外部依赖，标准 C 库即可
4. **文档**: 缺少 makeinfo 工具会导致文档生成失败，但不影响二进制文件
5. **MD5 代码**: 包含旧式 C 函数定义（非致命警告）

## 使用限制

- polipo 已停止维护（最后版本 1.1.1 发布于 2014 年）
- 仍可正常使用，但建议用于测试或学习目的
- 生产环境建议使用更现代的代理解决方案

## 相关软件

- proxychains-ng - 代理链工具
- socat - 网络工具
- squid - 功能更全面的代理服务器