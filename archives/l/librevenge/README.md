# librevenge

librevenge 是 Document Liberation Project 的基础库，为文档导入/导出过滤器提供核心数据结构和接口抽象。它被 libwpd、libetonyek、libvisio、libpagemaker 等文档解析库广泛依赖。

## 功能概述

- **RVNGString** — UTF-8 字符串操作（构造、追加、格式化、XML 转义、迭代器、比较）
- **RVNGStringVector** — 字符串向量容器
- **RVNGProperty / RVNGPropertyList** — 属性管理（支持 int/bool/double/string/binary 多类型，迭代器遍历，序列化）
- **RVNGBinaryData** — 二进制数据处理（追加、Base64 编解码、数据流）
- **RVNGInputStream** — 输入流抽象基类
  - RVNGStringStream — 内存数据流
  - RVNGFileStream — 文件系统流
  - RVNGDirectoryStream — 目录流
- **RVNGDrawingInterface** — 绘图接口抽象（矩形、椭圆、多边形、路径、文本、表格等）
- **RVNGTextInterface** — 文本接口抽象（段落、样式、链接、字段等）
- **RVNGSVGDrawingGenerator** — SVG 输出生成器（端到端绘图导出）
- **RVNGHTMLTextGenerator** — HTML 文本输出生成器
- **RVNGCSVSpreadsheetGenerator** — CSV 电子表格输出生成器

## OHOS 适配

### 适配要点

| 要点 | 说明 |
|------|------|
| 平台识别 (E007) | config.guess/config.sub 不含 OHOS 检测分支，需用 automake-1.17 版本替换 |
| umask 限制 | HarmonyOS 默认 umask 077 创建目录权限 drwx--S---，configure 中需改为 022 |
| 编译警告 | boost spirit headers 触发 -Wshadow 被 -Werror 拦截，需 -Wno-error=shadow |
| 静态链接 | 终端工具需静态链接（R26: --enable-static --disable-shared） |

### 功能验证

功能测试覆盖 7 大模块 + 跨模块集成，共 55 项测试全部通过（100%）：
- RVNGString: UTF-8 多字节字符（含中文）的 len() 计数和迭代器遍历正确
- RVNGFileStream: 鸿蒙文件系统 I/O 完全兼容（创建/读取/seek/EOF）
- RVNGSVGDrawingGenerator: SVG 输出格式正确（矩形/椭圆/文本/多页面）
- 跨模块集成: BinaryData→Stream 转换、1000 属性压力测试均正常

### 已知差异

- `drawEllipse` 方法需要 `svg:cx/cy/rx/ry`（中心坐标+半径）属性，而非 `svg:x/y/width/height`，与部分下游软件的调用约定不同
- 库使用 pimpl 模式，不暴露 STL 符号，ABI 稳定性良好

## 依赖关系

### 编译依赖
- **boost** — header-only，使用 spirit classic 模块
- **zlib** — 数据压缩

### 运行依赖
- 无额外运行时依赖（静态链接后自包含）

### 下游依赖
librevenge 被以下软件依赖：
- libwpd (WordPerfect 文档解析)
- libetonyek (Apple Keynote/Pages 文档解析)
- libvisio (Microsoft Visio 文档解析)
- libpagemaker (Adobe PageMaker 文档解析)
- libqxp (QuarkXPress 文档解析)
- libfreehand (FreeHand 文档解析)

## 参考资料

- **官网**: https://sourceforge.net/projects/libwpd/files/librevenge/
- **Document Liberation Project**: https://www.documentliberation.org/
- **源码**: https://sourceforge.net/p/libwpd/code/ci/master/tree/
- **许可证**: MPL-2.0 / LGPLv2.1+