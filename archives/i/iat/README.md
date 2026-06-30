# iat — Iso9660 Analyzer Tool

iat（Iso9660 Analyzer Tool）是一个用于检测 DVD/CD-ROM 镜像文件格式结构的工具。它支持多种光盘数据镜像格式，并能将任意镜像格式转换为 UDF/ISO 格式以方便挂载。

## 支持的镜像格式

- MODE1/2048
- MODE1/2368
- MODE1/2352
- MODE1/2448
- MODE2/2336
- MODE2/2352

不支持：压缩镜像格式（如 zlib）和音频镜像。

## 基本用法

```bash
iat -i <镜像文件>              # 分析镜像结构
iat -i <镜像文件> --iso        # 转换为 ISO9660 镜像
iat -i <镜像文件> --cue        # 创建 Cue Sheet
iat -i <镜像文件> --toc        # 创建 TOC 文件
iat --version                  # 显示版本号
iat --help                     # 显示帮助信息
```

## 编译版本

- **版本**: 0.1.7
- **构建系统**: autotools
- **依赖**: 无（仅依赖系统 C 库 musl libc）
- **平台**: HarmonyOS (OpenHarmony) aarch64

## 来源

- 项目主页: https://iat.berlios.org（已关闭）
- 源码下载: https://downloads.sourceforge.net/project/iat.berlios/iat-0.1.7.tar.bz2