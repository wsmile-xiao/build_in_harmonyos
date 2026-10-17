# colrc

A C library for easier terminal text coloring and formatting.

## 项目信息

- **官方仓库**: https://github.com/welbornprod/colrc
- **许可证**: MIT
- **语言**: C
- **构建系统**: Makefile

## 版本历史

- **0.3.7**: 首次适配 OHOS 平台

## 适配说明

colrc 是一个轻量级的终端颜色库，提供简单的 API 来输出彩色文本。适配过程中修复了以下平台兼容性问题：

1. 禁用 GNU extensions (printf.h) 以兼容 OHOS musl libc
2. 添加 `_GNU_SOURCE` 宏保护
3. 修复 ioctl 函数签名差异
