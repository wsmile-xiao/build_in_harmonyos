# hellwal

**hellwal** 是一个快速、可扩展的调色板生成器，可以从图片或主题文件生成终端配色方案。

## 功能概述

- 从图片自动提取颜色并生成16色调色板
- 支持暗色模式（-d）和亮色模式（-l）
- JSON 输出格式（-j），便于程序化调用
- 反色模式（-v）、霓虹模式（-m）、灰度滤镜（-g）
- 自定义模板和主题文件夹
- 颜色对比度检查（--check-contrast）
- 预览功能（--preview, --preview-small）

## OHOS 适配要点

- 实际是 **Makefile 项目**（非 autotools），registry 标记有误
- 原始 Makefile 的 DESTDIR 用法非标准，需改为标准 DESTDIR+PREFIX 模式
- CFLAGS/LDFLAGS 使用 `=` 覆盖环境变量，需改为 `+=` 兼容 -fPIC 等环境参数
- PATH 中无 cc 软链接，需使用 CC=clang 环境变量
- 首次运行会尝试写入 ~/.cache/hellwal/ 和 ~/.config/hellwal/templates/，目录不存在时输出 WARN 但不影响核心功能
- hellwal.c 有 2 个编译警告（未初始化变量），不影响功能

## 依赖关系

- **编译依赖**: 无（仅需 libc/libm）
- **运行依赖**: libc.so（无外部库依赖）
- 二进制仅 186KB，轻量部署

## 参考资料

- 源码仓库: https://github.com/danihek/hellwal
- License: MIT