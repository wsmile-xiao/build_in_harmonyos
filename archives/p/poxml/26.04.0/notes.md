# poxml 26.04.0 — OpenHarmony PC 适配笔记

## 概览

| 项 | 值 |
|---|---|
| 包名 | poxml |
| 版本 | 26.04.0（KDE Gear 26.04.0 发布周期） |
| 上游 | KDE `invent.kde.org/sdk/poxml` |
| 源码 | `https://download.kde.org/stable/release-service/26.04.0/src/poxml-26.04.0.tar.xz` |
| sha256 | `dce68a16977ed0bc5b3e6d17600e2b58e15f336a731b403b4b2aaa0d13fc1055` |
| 构建系统 | CMake + ECM（extra-cmake-modules） |
| 产物 | `bin/split2po`、`bin/xml2pot`、`bin/po2xml`、`bin/swappo` + 四个 man 手册 |

## 软件简介

poxml 是 KDE 文档翻译工作流的核心工具集，在 **DocBook XML** 与 **gettext PO**
之间双向转换：

- `xml2pot` —— 从 DocBook 抽取可翻译字符串生成 POT 模板
- `po2xml` —— 把译文 PO 合回文档，产出对应语言的 XML
- `split2po` —— 从已翻译的文档反向拆出 PO
- `swappo` —— 交换 PO 的 msgid/msgstr

## 依赖（逐一来自上游 CMakeLists.txt）

| 上游声明 | 本仓提供 |
|---|---|
| `find_package(ECM REQUIRED NO_MODULE)` | `ecm/6.20.0`（tool_requires） |
| `find_package(GettextPO REQUIRED)` | `gettext/0.22.5.1`（`gettext-po.h` + `libgettextpo`） |
| `find_package(Gettext)` | 同上（`msgfmt`/`msgmerge`，测试用） |
| `find_package(Qt6 REQUIRED COMPONENTS Core Xml)` | `qtbase/6.11.1` |
| `find_package(KF6 REQUIRED COMPONENTS DocTools)` | `kdoctools/6.19.0` |

## 构建要点

### 1. GettextPO 是裸探测，必须手工铺 CMAKE_PREFIX_PATH

上游自带的 `cmake/modules/FindGettextPO.cmake` **不是 config 包**，而是最原始的：

```cmake
find_path(GETTEXTPO_INCLUDE_DIR gettext-po.h)
find_library(GETTEXTPO_LIBRARY NAMES gettextpo)
```

因此光有 Conan 的依赖图不够——gettext 包前缀必须真的出现在 CMake 的搜索路径里。
qtbase/KF6/gettext 在本仓均为 `cmake_find_mode=none`，生成的
`conan_cmakedeps_paths.cmake` 不含它们的 `lib/cmake`，所以配方自行重写该文件
（`_write_cmake_paths()`，沿用 baloo / keditbookmarks 先例）。

### 2. ECM 在 OHOS 上的两个开关

```cmake
-DKF_IGNORE_PLATFORM_CHECK=TRUE   # ECM 平台检查不含 HarmonyOS
-DKF_SKIP_PO_PROCESSING=ON        # 跳过与工具本身无关的翻译目录流水线
```

### 3. 共享库 soname

OHOS 无 Platform/HarmonyOS CMake 模块，需显式
`CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname,`。

### 4. 主机工具的运行环境

`moc`、`meinproc6`、`checkXML6` 是无 RPATH 的普通可执行文件，构建期必须能加载
Conan 的 Qt/KF 库。另需把 `/system/lib64` **最后** prepend（从而排在最前）——
因为 SDK 的 `aarch64-linux-ohos/libc++.so` 是链接脚本，运行期加载器无法使用，
必须让 `/system/lib64` 的 `libc++_shared.so` 遮蔽它（kconfig/kcrash 先例）。

## 上游测试（R51）

上游带 CTest 目标（`tests/CMakeLists.txt`，受 `GETTEXT_FOUND` 门控）：

| 测试 | 内容 |
|---|---|
| `lauri_de` | 用 `checkXML6` 校验 `po2xml` 产出的德语译文 XML 结构合法 |
| `split2po` | 对已翻译文档执行真实往返转换 |

配方 `BUILD_TESTING=ON` 并在 `build()` 内真实运行 `ctest`。

## test_package 设计（消费者视角）

`test_poxml.py` 不依赖上游测试数据，自带最小 DocBook 文档，驱动完整的
双向往返：

| # | 步骤 | 断言 |
|---|---|---|
| 1 | 检查四个二进制 | 均存在且可执行 |
| 2 | `xml2pot sample.docbook` | 产出 POT，含文档中的真实字符串 |
| 3 | `po2xml sample.docbook sample.po` | 产出合法 `<book>` XML |
| 4 | `split2po sample.de.docbook` | 反向拆出 PO |

## 已知平台限制

- `kdoctools_install(po)` 安装翻译目录；本例以 `KF_SKIP_PO_PROCESSING=ON` 跳过，
  不影响四个转换器的功能。
- 运行期需要 Qt6/KF6/gettext 的共享库（配方已在 `runenv_info` 铺 LD_LIBRARY_PATH）。
