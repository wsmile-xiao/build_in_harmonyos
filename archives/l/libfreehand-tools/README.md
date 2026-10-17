# libfreehand-tools

Macromedia/Adobe FreeHand（`.fh`）矢量绘图文档的解析库与命令行转换工具集，来自 LibreOffice
文档基金会（Document Liberation Project）；本包为 **-tools 子包**，与父包 `libfreehand`
同源 tarball，交付三个转换工具并一并交付库本体。

## 功能概述

| 产物 | 功能 |
|------|------|
| `bin/fh2raw` | FreeHand → raw 调试输出（`--callgraph` 显示调用图嵌套层级） |
| `bin/fh2svg` | FreeHand → SVG |
| `bin/fh2text` | FreeHand → 纯文本 |
| `lib/libfreehand-0.1.a` | 解析库本体（静态；公共 API `FreeHandDocument::isSupported/parse`） |
| `include/libfreehand-0.1/libfreehand/` | 公共头（`libfreehand.h`、`FreeHandDocument.h`） |

支持 FreeHand 5+（`AGD` 魔数）与 FH3（`FH3` 魔数）文件；彩色/多页文档经 librevenge 抽象输出。

## OHOS 适配

- **交叉编译**：上游 `config.guess/sub`（2012）不识别 `aarch64-linux-ohos`，用 GNU triplet
  `--build/--host=aarch64-unknown-linux-gnu` 强制交叉模式，OHOS 目标由工具链 CFLAGS/LDFLAGS/sysroot 达成。
- **`--disable-werror`**：上游 `configure.ac` 的 `--enable-werror` 默认 `yes`（开发默认），
  2017 年代码 + clang 15 触发新告警即编译失败，打包按发行版惯例关闭。
- **上游测试**：`--enable-tests` 默认 `yes`，`src/test` 的 CPPUnit 套件默认进构建；配方
  `tool_requires("cppunit/1.15.1")` 并在 `build()` 内真实 `make check`（HOME 指向构建目录内沙箱）。
- **代码生成器**：`src/lib` 的 `BUILT_SOURCES` 需 `gentoken.pl`(perl) 与 `gperf`；perl 走
  `tool_requires`，gperf 制品仓无 binary、依赖 HNP 工具链提供的 `/data/service/hnp/bin/gperf`。
- **链接语义**：libtool `_LIBADD` 里绝对路径 `.a` 会被当 convenience 库嵌入产物，依赖统一走
  la-free shadow 目录 + `-L<shadow> -l<name>`；包内不留 `.la`。
- **lcms2 为动态依赖**：制品仓只有 `.so`（无 `.a`），工具产物带 `DT_NEEDED=liblcms2.so.2`；
  配方写 `-Wl,-rpath,<lcms2 libdir>` 使包内 `bin/` 可直接执行，换机运行需消费侧 conan runtime env。
- **已知限制**：`--help` 在上游一律 `return -1`（退出码 255）；`src/fuzz` 的 fuzz 目标未构建
  （需 `-lFuzzingEngine`，上游 `--enable-fuzzers` 默认 `no`）。

## 依赖关系

编译依赖：librevenge/0.0.5、icu4c/78、zlib/1.3.1、lcms2/2.19、boost/1.90.0.3（仅头）、
cppunit/1.15.1（上游测试框架）、pkgconf/3.0.5、perl/5.42.2.3（tool_requires）。

运行依赖：librevenge、icu4c、zlib（静态链入产物）、lcms2（动态，`liblcms2.so.2`）。

## 参考资料

- 官网/DLP 主页：https://wiki.documentfoundation.org/DLP/Libraries/libfreehand
- 源码仓库：https://github.com/LibreOffice/libfreehand
- 上游发布目录：https://dev-www.libreoffice.org/src/libfreehand/
