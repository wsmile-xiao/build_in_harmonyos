# pinentry

## 简介
Pinentry是GnuPG项目的一个PIN输入程序，用于安全地输入密码、PIN码等敏感信息。它支持多种前端界面，包括curses（终端）、GTK+、Qt等。

## 功能特性
- 多种前端支持：curses、GTK+、Qt、Emacs
- 安全输入机制：防止密码被记录到日志
- GnuPG集成：与GPG、GPG-Agent紧密配合
- 上下文感知：根据调用环境选择合适的前端

## 版本信息
- **当前版本**: 1.3.2
- **状态**: built（编译成功，未发布）
- **构建系统**: autotools

## 编译状态

| 版本 | 状态 | 构建日期 | 说明 |
|------|------|----------|------|
| 1.3.2 | built | 2026-05-28 | 编译成功，存在运行时依赖问题 |

## 编译依赖
- libgpg-error（≥ 1.16）
- libassuan（≥ 2.1.0）
- ncurses（可选，用于curses frontend）

## 已知限制
- **libgpg-error符号缺失**: 平台预编译的libgpg-error未正确链接libintl，导致运行时错误
- **G0验证失败**: clean-verify脚本传递空host参数导致验证失败
- **阻塞发布**: 无法制作预编译包，需后续修复依赖

## 补丁说明
针对HarmonyOS平台适配，应用了以下补丁：
1. **0001-build-aux-config.sub.patch**: 添加HarmonyOS平台识别
2. **0002-configure.patch**: 修复libintl检测逻辑
3. **0003-pinentry-pinentry-emacs.c.patch**: 修复编译错误

## 后续任务
- 重新编译libgpg-error（正确链接libintl）
- 修复clean-verify传递空host参数问题
- 完成G0验证并制作预编译包

## 参考链接
- [官方网站](https://gnupg.org/related_software/pinentry/index.html)
- [下载地址](https://gnupg.org/ftp/gcrypt/pinentry/)
- [GnuPG项目](https://gnupg.org/)
