# pngmeta — PNG 元数据提取工具

pngmeta 是一个小型过滤器程序，读取 PNG 图像并把其中的元数据输出为纯文本、SOIF、HTML 或
RDF/XML 四种格式之一。由 Dave Beckett（ILRT, University of Bristol）于 1998–2001 年编写，
最初用于把 PNG 图像的描述信息喂给 Harvest/SOIF 索引系统与早期的 RDF 工具链。

## 功能概述

- 提取 PNG 的文本类块：`tEXt`（未压缩）、`zTXt`（压缩）、`iTXt`（国际化），
  以及 `tIME` 修改时间；`--all` 下还输出 `IHDR` 的几何信息
- 输出格式：
  - 默认：`Key: Value` 纯文本
  - `--soif`：SOIF 格式（`Key{长度}:\tValue`）
  - `--html`：HTML 定义列表
  - `--xrdf`：RDF/XML（`png:` 与 `dc:` 命名空间）
- 其他选项：`--uri URI` 指定 SOIF/RDF 主语，`--quiet` 抑制横幅，
  `--help` / `--version` 输出用法与版本（按上游设计写到 stderr 并以退出码 1 结束）

## OHOS 适配要点

- **构建系统**：autotools，`configure` 由 autoconf 2.13 生成（1998 年代），不认识
  `--datarootdir` 等后来引入的选项，配方在 `generate()` 中按白名单过滤 Conan 注入的
  `configure_args`
- **libpng 私有 API 迁移（主要工作量）**：上游用 `#define PNG_INTERNAL` 自行遍历 PNG 分块
  （`png_handle_IHDR` / `png_handle_tEXt` / `png_handle_zTXt` / `png_handle_iTXt` 等），
  并直接读取 `png_ptr->idat_size`、`info_ptr->bit_depth` 这类内部字段。libpng 1.4 起结构体
  不透明、内部头不再安装，这些写法全部失效。补丁删除自制的 `png_skip_till_end()`，改用
  `png_read_png()` 一次读完，字段统一走 `png_get_IHDR` / `png_get_text` / `png_get_tIME`，
  `setjmp` 改用 `png_jmpbuf()`，销毁改用 `png_destroy_read_struct()`。
  该模式已沉淀为知识草稿 `E600`
- **zlib 头文件**：libpng ≥1.5 的 `png.h` 不再内嵌 `zlib.h`，`--version` 里引用的
  `ZLIB_VERSION` 需显式 `#include <zlib.h>`
- **RDF/XML 正确性**：上游把主语写成 `about=`（应为 `rdf:about=`），并把含空格的 PNG 关键字
  直接当成 XML 元素名。补丁一并修正，`test4.xpt` 的期望输出同步更新
- **测试执行**：上游 `TESTS = test1 test2 test3 test4`，配方 `build()` 在能执行目标二进制的
  构建机上直接跑 `make check`；VPATH 构建下先把 `*.xpt` / `*.png` 复制到 build 目录
- **toybox diff**：OHOS 的 `diff` 是 toybox 实现，不支持上游测试脚本用的 `diff -c`（context 格式），
  补丁改为 POSIX 的 `diff -u`，比对语义不变

## 依赖关系

### 编译依赖
- libpng 1.6.58.3（conan 制品仓）
- zlib 1.3.2（conan 制品仓）

## 版本

| 版本 | 状态 | 日期 | 说明 |
|---|---|---|---|
| 1.11 | built | 2026-09-20 | 首次适配；上游测试 4/4 通过 |

## 上游

- 官方主页：https://pmt.sourceforge.io/pngmeta/
- 源码发布：SourceForge 项目 `pmt`
- 适配参考：https://salsa.debian.org/debian-phototools-team/pngmeta.git
  （Debian 打包仓库的 `debian/patches/` 提供了同类问题的修复思路）
