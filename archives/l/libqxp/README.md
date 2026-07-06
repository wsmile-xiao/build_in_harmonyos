# libqxp

libqxp 是一个用于解析 QuarkXPress 文档文件的 C++ 库，属于 LibreOffice 项目的一部分。它可以将 QXP 文件（3.1–4.x 版本）解析为结构化的文档对象，供文档转换和导入使用。

## 功能概述

- 解析 QuarkXPress 3.1/3.3/4.x (Windows & Mac) 文档格式
- 提供 `QXPDocument::isSupported()` 文件检测接口
- 提供 `QXPDocument::parse()` 解析接口，输出 SVG/Text/Raw 等格式
- 附带命令行工具：`qxp2raw`、`qxp2svg`、`qxp2text`
- 基于 librevenge 文档解析框架构建

> **注意**：不支持 QXP 5/6 格式（设计限制，非平台问题）。

## OHOS 适配

### 适配要点

| # | 问题 | 对策 |
|---|------|------|
| 1 | config.guess/config.sub 版本过旧（2016-10-02），不识别 OHOS | 替换为 automake-1.17 版本（2023-08-22），支持 `aarch64-unknown-linux-ohos` |
| 2 | HMDFS 文件系统上 `umask 077` 创建的目录无法写入（setgid + 077 权限冲突） | 将 configure/config.status 中 `umask 077` 改为 `umask 022`，或 Conan 配方中使用 mktemp wrapper |
| 3 | ICU 77.1 的 `LocalOpenPointer` 模板使用 C++17 `auto` 非类型模板参数 | CXXFLAGS 添加 `-std=c++17` |
| 4 | Savannah 源码 URL 返回 404 | 使用 LibreOffice 镜像 URL |
| 5 | Python ssl 模块证书验证可能失败 | 设置 `SSL_CERT_FILE` 指向 certifi 证书 |

### 已知差异（与 Linux）

- HMDFS 权限模型与 ext4 不同，`umask 077` 下 autoconf 临时目录创建会失败
- 源码包为 `.tar.xz` 格式，若系统缺少 Python lzma 模块需转换为 `.tar.gz`

## 依赖关系

### 编译依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| librevenge | 0.0.5 | Conan `` |
| icu | 77.1 | Conan `` |
| boost | (headers) | 预编译包 |
| cppunit | — | 预编译包（make check 用，Conan 配方中 `--disable-tests` 跳过） |

### 运行依赖

- librevenge（动态库）
- libc / libc++（系统库）

## 产物

| 产物 | 说明 |
|------|------|
| `lib/libqxp-0.0.a` | 静态库（Conan 配方强制 `--enable-static --disable-shared`） |
| `include/libqxp-0.0/` | 头文件 |
| `lib/pkgconfig/libqxp-0.0.pc` | pkg-config 文件 |
| `bin/qxp2raw`, `bin/qxp2svg`, `bin/qxp2text` | 命令行工具 |

## 参考资料

- 官网: https://wiki.documentfoundation.org/DLP/Libraries/libqxp
- 源码: https://dev-www.libreoffice.org/src/libqxp-0.0.1.tar.xz
- 许可证: MPL-2.0
