# id3v2

命令行 ID3v1/v2 标签编辑器，基于 id3lib，用于为 MP3 文件增删改查 ID3 标签，
并可在 ID3v1 与 ID3v2 之间转换。

- 上游: https://id3v2.sourceforge.net/
- 许可证: LGPL-2.1
- 构建系统: 平 Makefile（上游）+ vendor id3lib autotools

## 说明

id3v2 依赖 id3lib。id3lib 在本仓库归档为 stub、未发布到制品仓，故 0.1.12
配方将 id3lib 3.8.3 源码 vendor 进来，静态编译后构建 id3v2（superbuild）。

## 版本

- **0.1.12**: 首次适配，vendor id3lib 3.8.3 静态编译，依赖 zlib/1.3.1
