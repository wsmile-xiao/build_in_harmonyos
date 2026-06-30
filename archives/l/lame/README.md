# lame

LAME (Lame Ain't an MP3 Encoder) - 高质量MP3编码器

## 简介

LAME是一个开源的MP3编码器,以其高质量的音频编码而闻名。它遵循LPGL许可证,提供快速和高质量的MP3编码功能。

## 版本信息

- 当前版本: 3.100
- 发布日期: 2017-10-14
- 许可证: LGPL

## 特性

- 高质量MP3编码
- 支持多种比特率和采样率
- VBR (Variable Bit Rate) 支持
- 心理声学模型优化
- 跨平台支持

## HarmonyOS 编译状态

✅ 已成功编译并适配 HarmonyOS 平台

### 编译版本
- 3.100 (2026-05-21)

### 平台适配问题及解决方案

1. **E007**: config.guess/config.sub 添加 HarmonyOS 支持
   - 添加 aarch64-unknown-linux-ohos 三元组识别
   - 修改 config.guess 和 config.sub 脚本

2. **E011**: HMDFS 文件系统 umask 权限问题
   - 修改 configure 脚本中的 umask 077 → umask 022
   - 使用 hints/configure-umask.sh 脚本自动修复

### 编译依赖

- clang 编译器
- GNU make
- autotools (autoconf, automake)

## 下载

预编译包可通过 cmd-pkgs 仓库获取:
- lame-3.100-ohos-aarch64.tar.gz
- lame-3.100-ohos-aarch64-debug.tar.gz

## 参考链接

- 官方网站: https://lame.sourceforge.net/
- 源码仓库: https://sourceforge.net/projects/lame/