# libfreehand

Library for parsing and converting Macromedia/Adobe FreeHand (.fh) drawing files.

## 概述

libfreehand 是一个开源 C++ 库，用于解析 FreeHand 矢量绘图文件格式 (.fh)。它是 Document Liberation Project (DLP) 的一部分，由 LibreOffice 社区维护。

该库提供：
- FreeHand 文件格式检测 (AGD/FH3 魔数)
- 文档解析和内容提取
- 三种输出格式的命令行转换工具

## 安装产物

### 命令行工具

| 工具 | 功能 | 用法 |
|------|------|------|
| fh2raw | FreeHand → Raw | `fh2raw [--callgraph] <file.fh>` |
| fh2svg | FreeHand → SVG | `fh2svg <file.fh>` |
| fh2text | FreeHand → Text | `fh2text <file.fh>` |

### 库文件

| 文件 | 说明 |
|------|------|
| libfreehand-0.1.so.1.0.1 | 共享库 (461KB) |
| libfreehand-0.1.pc | pkg-config 文件 |
| libfreehand/ | 开发头文件目录 |

## 依赖

| 依赖 | 版本 | 类型 |
|------|------|------|
| librevenge | 0.0.5 | 编译 + 运行时 |
| liblcms2 | 2.x | 运行时 (颜色管理) |
| zlib | - | 运行时 (压缩支持) |

## 使用示例

### 命令行
```bash
fh2raw drawing.fh > output.raw
fh2svg drawing.fh > output.svg
fh2text drawing.fh > output.txt
```

### C++ API
```cpp
#include <libfreehand/libfreehand.h>
#include <librevenge-stream/librevenge-stream.h>
#include <librevenge-generators/librevenge-generators.h>

librevenge::RVNGFileStream input("drawing.fh");
if (libfreehand::FreeHandDocument::isSupported(&input)) {
    input.seek(0, librevenge::RVNG_SEEK_SET);
    librevenge::RVNGRawDrawingGenerator generator(false);
    libfreehand::FreeHandDocument::parse(&input, &generator);
}
```

### 编译链接
```bash
clang++ myprogram.cpp $(pkg-config --cflags --libs libfreehand-0.1) \
    -lrevenge-stream-0.0 -lrevenge-generators-0.0
```

## 支持的 FreeHand 版本

- FreeHand 3.x (FH3 魔数)
- FreeHand 5+ (AGD 魔数, 包括 FH 5/6/7/8/9/10/MX/MX2004)

## OpenHarmony 平台适配

### 编译信息
- 构建系统: autotools
- 编译器: clang/clang++
- 平台: ohos-aarch64
- 补丁: 17 个 (平台适配 + 编译修复)

### 主要适配点
1. config.guess/config.sub 添加 HarmonyOS 平台识别
2. configure umask 077 → 022 (HMDFS 权限修复)
3. FHPath.h 前向声明 class→struct 修复 (-Wmismatched-tags)
4. FHTransform 拷贝赋值运算符修复 (-Wdeprecated-copy)
5. U16_NEXT 宏分号修复

### 功能验证
- ✅ 三个命令行工具正常运行
- ✅ 库 API 编译链接和调用正常
- ✅ pkg-config 集成完整
- ✅ ELF 二进制格式和依赖链正确
- ✅ 错误处理优雅，无崩溃

## 许可证

MPL-2.0 (Mozilla Public License 2.0)

## 链接

- 源码: https://dev-www.libreoffice.org/src/libfreehand-0.1.1.tar.bz2
- 项目主页: https://wiki.documentfoundation.org/DLP/Libraries/libfreehand
