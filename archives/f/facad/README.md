# facad

**描述**: Modern, colorful directory listing tool for the command-line
**许可证**: MIT
**主页**: https://github.com/yellow-footed-honeyguide/facad

## 简介

facad 是一个现代的、带彩色 emoji 的命令行目录列表工具。它替代传统的 `ls` 命令，提供更直观、更美观的目录内容展示方式，使用 emoji 和颜色区分不同文件类型。

## 已编译版本

| 版本 | 构建系统 | 状态 | 编译日期 |
|------|---------|------|---------|
| 2.20.16 | meson | ✅ published | 2026-06-13 |

## 功能特性

- 彡 彩色 emoji 文件类型标识（📁 目录、📦 压缩包、📝 文本等）
- `-l` 长格式列表：显示文件大小、修改时间、权限信息
- `-a` 分析模式：统计总大小、文件数量、最大/最旧/最新文件等
- `-v` 版本信息，`-h` 帮助信息
- 无外部依赖，仅依赖 libc 和 libm

## 编译说明

- **构建系统**: meson
- **配置命令**: `meson setup builddir --prefix=$DEFAULT_PREFIX`
- **构建命令**: `ninja -C builddir`
- **安装命令**: `DESTDIR=$TEST_PREFIX ninja -C builddir install`
- **无需补丁**: 源码在鸿蒙平台可直接编译
- **无需额外依赖**: 仅依赖 libc 和 libm

## 注意事项

- meson 运行需要设置 `LD_LIBRARY_PATH` 以正确加载 Python3.12 共享库
- DESTDIR install 需设置 `PYTHONHOME=/data/service/hnp/python.org/python_3.12`
