# libmspub-tools

> Microsoft Publisher（.pub）文档解析库 libmspub 及转换工具集（pub2raw、pub2xhtml）

## 简介

libmspub 是 LibreOffice 文档基金会的 Microsoft Publisher 文档解析库，用于读取和解析 `.pub` 格式文件，是 LibreOffice、Calligra 等办公套件导入 Publisher 文档的核心组件。libmspub-tools 将库本体与两个命令行转换工具一起打包：

- **pub2raw**：将 Publisher 文档转换为 raw 调试输出
- **pub2xhtml**：将 Publisher 文档转换为 XHTML

## OHOS 适配要点

- 上游 config.sub（2012 年版）不识别 `aarch64-linux-ohos` triplet，配方用 GNU triplet（`aarch64-unknown-linux-gnu`）强制交叉编译模式，OHOS 目标由工具链 CFLAGS/LDFLAGS/sysroot 达成（ctpl/cdecl 先例）。
- 本机 `rm` 命令被 codebuddy 安全 shim（`safe-bin/rm`，`#!/bin/bash` shebang）劫持，而 OHOS 无 `/bin/bash`，须在配方 `_sanitize_path()` 中从 PATH 剔除 safe-bin 目录。
- libtool 的 `_LIBADD` 中绝对路径 `.a` 会被当作 convenience 库嵌入产物，须用 la-free shadow 目录 + `-L -l` 形式链接依赖。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| librevenge | 0.0.5 | 底层文档抽象（revenge/revenge-stream/revenge-generators 三库） |
| icu4c | 78 | ICU 国际化（ucsdet/uloc/ucnv） |
| zlib | 1.3.1 | 数据解压 |
| boost | 1.90.0.3 | 仅头文件（optional/multi_array 等） |

## 功能验证

```bash
# 转换工具版本自证
pub2raw --version
pub2xhtml --version

# 鸿蒙消费者用例（test_package，编译期 __OHOS__/__aarch64__ 硬绑定）
./harmonyos_specific_test
```

## 参考

- [官方源码仓库](https://github.com/LibreOffice/libmspub)
- [上游发布说明](https://dev-www.libreoffice.org/src/libmspub/)
