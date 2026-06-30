# swftools

SWF Tools 是一套用于处理 Adobe Flash (SWF) 文件的工具集合。

## 软件描述

swftools 提供了一系列命令行工具，用于创建、编辑、分析和转换 SWF 文件。主要工具包括：

- **swfcombine** - SWF 文件组合工具
- **swfdump** - SWF 文件分析和查看工具
- **swfc** - SWF 编译器，从脚本创建 SWF 文件
- **wav2swf** - WAV 音频转 SWF 工具
- **png2swf** - PNG 图片转 SWF 工具
- **swfextract** - 从 SWF 文件中提取资源
- **swfstrings** - 提取 SWF 文件中的文本
- **swfbbox** - SWF 边界框计算工具
- **font2swf** - 字体转 SWF 工具
- **swfrender** - SWF 渲染工具
- **as3compile** - ActionScript 3 编译器
- **swfbytes** - SWF 字节码分析工具
- **ttftool** - TTF 字体处理工具

## 编译版本

- **版本**: 0.9.2
- **状态**: built
- **编译日期**: 2026-06-08

## 编译说明

### 平台适配要点

1. **临时目录权限问题**: configure 和 config.status 使用 mktemp 创建临时目录时权限过严，需要修改为使用 TMPDIR 环境变量
2. **源码全局变量重复定义**: registry.h、swfc-feedback.h、swfc-history.h 中存在全局变量重复定义，需要修改为 extern 声明
3. **安装脚本语法错误**: swfs/Makefile.in 中的 rm 命令使用了错误的 `-o -L` 语法，需要修复

### 应用补丁

```bash
patch -p1 < patches/0001-configure.patch
patch -p1 < patches/0002-swfs-Makefile.in.patch
```

### 编译命令

```bash
export TMPDIR=$HOME/tmp/swftools-config-$$
mkdir -p $TMPDIR
chmod 755 $TMPDIR
./configure --prefix=/storage/Users/currentUser/usr/local --build=aarch64-unknown-linux-gnu
make -j1
make install DESTDIR=/path/to/staging
```

### 注意事项

- 缺少 jpeglib、giflib、freetype 等依赖，pdf2swf、jpeg2swf、gif2swf 工具被禁用
- 需要设置 TMPDIR 环境变量，避免 configure 在当前目录创建临时文件失败
- 源码有多处全局变量重复定义的 bug，需要修复头文件

## 预编译包

预编译包路径：`packaging/swftools-0.9.2-ohos-aarch64.tar.gz`

安装方法：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- swftools 0.9.2
```

## 依赖

- zlib (系统自带)
- clang/clang++ 编译器

## 许可证

GPL v2

## 相关链接

- 官方网站: http://www.swftools.org/
- 源码下载: https://distfiles.macports.org/swftools/swftools-0.9.2.tar.gz