# ruby-build

## 简介

ruby-build 是一个命令行工具，用于在 Unix-like 系统上从源码编译安装 Ruby。它可作为 rbenv 的插件使用（`rbenv install` 命令），也可独立使用（`ruby-build` 命令）。

## 功能特性

- 支持 685+ 个 Ruby 版本（从 1.8.5 到最新版本）
- 支持多种 Ruby 实现：
  - CRuby（标准Ruby）
  - JRuby（JVM上的Ruby）
  - mruby（轻量级Ruby）
  - TruffleRuby（高性能Ruby）
- 自动下载 Ruby 源码
- 自动配置编译选项
- 自动处理 OpenSSL 等依赖

## 在鸿蒙系统上的使用

### 安装

通过预编译包安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | \
  sh -s -- ruby-build 20260512
```

### 使用示例

```bash
# 安装最新稳定版 Ruby
ruby-build 3.4.9 ~/.rubies/ruby-3.4.9

# 安装 JRuby
ruby-build jruby-10.0.0 ~/.rubies/jruby-10.0.0

# 列出可用版本
ruby-build --list

# 安装到 rbenv
rbenv install 3.4.9
```

### 鸿蒙特性和限制

1. **运行时依赖**：
   - bash（脚本执行）
   - git（下载Ruby源码）
   - curl/wget（下载工具）
   - 编译工具链（clang/gcc、make）
   - OpenSSL、readline、zlib等（Ruby依赖）

2. **已知限制**：
   - Ruby 编译时间较长（30分钟-2小时）
   - 需确保编译依赖已安装
   - 部分Ruby版本可能不兼容musl libc

3. **推荐使用**：
   - 优先安装预编译的Ruby版本（如有）
   - 编译时注意资源占用
   - 建议在夜间或空闲时编译

## 依赖关系

**无编译依赖**（脚本软件）

**运行时依赖**：
- bash
- git
- curl/wget
- 编译工具链（用于编译Ruby）
- OpenSSL（Ruby依赖）

## 版本信息

- **当前版本**: 20260512
- **发布日期**: 2026-05-12
- **源码**: https://github.com/rbenv/ruby-build
- **包含**: 685个Ruby版本定义

## 相关链接

- GitHub: https://github.com/rbenv/ruby-build
- 文档: https://github.com/rbenv/ruby-build#readme
- rbenv: https://github.com/rbenv/rbenv

## 归档信息

- 归档目录: `archives/r/ruby-build/20260512/`
- 编译日期: 2026-05-19
- 状态: built（待打包）