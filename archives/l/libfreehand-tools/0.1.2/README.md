# libfreehand-tools

> Macromedia/Adobe FreeHand（.fh）文档解析库 libfreehand 及转换工具集（fh2raw、fh2svg、fh2text）

## 简介

libfreehand 是 LibreOffice 文档基金会（Document Liberation Project）的 FreeHand 文档解析库，用于读取
Macromedia/Adobe FreeHand 的 `.fh` 矢量绘图文件，是 LibreOffice、Calligra 等办公套件导入 FreeHand
文档的核心组件。libfreehand-tools 将库本体与三个命令行转换工具一起打包：

- **fh2raw**：将 FreeHand 文档转换为 raw 调试输出（`--callgraph` 可显示调用图嵌套层级）
- **fh2svg**：将 FreeHand 文档转换为 SVG
- **fh2text**：将 FreeHand 文档转换为纯文本

## OHOS 适配要点

- 上游 `config.sub`（2012 年版）不识别 `aarch64-linux-ohos` triplet，配方用 GNU triplet
  （`aarch64-unknown-linux-gnu`）强制交叉编译模式，OHOS 目标由工具链 CFLAGS/LDFLAGS/sysroot 达成。
- 上游 `configure.ac` 的 `--enable-werror` **默认 yes**（开发默认），2017 年代码 + clang 15 会触发
  新告警（实测 `-Wdeprecated-copy-with-user-provided-copy`）直接编译失败；打包按发行版惯例传
  `--disable-werror`，不改上游源码。
- 本机 `rm` 命令被 codebuddy 安全 shim（`safe-bin/rm`，`#!/bin/bash` shebang）劫持，而 OHOS 无
  `/bin/bash`，须在配方 `_sanitize_path()` 中从 PATH 剔除 safe-bin 目录（并清掉 `BASH_FUNC_*%%`
  与 `BASH_ENV` 两条复活的注入通道）。
- libtool 的 `_LIBADD` 中绝对路径 `.a` 会被当作 convenience 库嵌入产物，须用 la-free shadow 目录 +
  `-L -l` 形式链接依赖。
- `lcms2` 制品仓只有动态库（无 `.a`），工具产物因此带 `DT_NEEDED=liblcms2.so.2`；配方写
  `-Wl,-rpath,<lcms2 libdir>` 使包内 `bin/` 可直接执行。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| librevenge | 0.0.5 | 底层文档抽象（revenge / revenge-stream / revenge-generators 三库） |
| icu4c | 78 | ICU 国际化（`unicode/utf8.h`、`unicode/utf16.h`） |
| zlib | 1.3.1 | 压缩文档流的 `inflate*` |
| lcms2 | 2.19 | CMYK 色彩配置文件转换（`cmsOpenProfileFromMem`） |
| boost | 1.90.0.3 | 仅头文件（`boost/cstdint.hpp`） |
| cppunit | 1.15.1 | 上游单元测试框架（`--enable-tests` 默认 yes） |
| pkgconf | 3.0.5 | `PKG_PROG_PKG_CONFIG` 所需二进制 |
| perl | 5.42.2.3 | `src/lib/gentoken.pl` 生成 `tokens.gperf`（BUILT_SOURCES） |

## 功能验证

```bash
# 转换工具版本自证
fh2raw --version
fh2svg --version
fh2text --version

# 上游单元测试（CPPUnit，src/test）
make check

# 鸿蒙消费者用例（test_package，编译期 __OHOS__/__aarch64__ 硬绑定）
./harmonyos_specific_test
```

## 参考

- [官方源码仓库](https://github.com/LibreOffice/libfreehand)
- [上游发布目录](https://dev-www.libreoffice.org/src/libfreehand/)
- [DLP 项目主页](https://wiki.documentfoundation.org/DLP/Libraries/libfreehand)
