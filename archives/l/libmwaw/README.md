# libmwaw

## 软件描述

libmwaw 是一个解析旧版 Mac 文本文档（macOS X 之前格式）的 C++ 库，基于
librevenge 抽象流接口。支持 MacWrite、ClarisWorks、Microsoft Word (Mac)、
WriteNow、TeachTxt、StarOffice (Mac)、FrameMaker、OfficeWorks 等数十种
legacy 格式的导入。

本包为**库包**（libmwaw-0.3 + 头文件）；命令行转换工具集
（mwaw2text/mwaw2csv/mwaw2html/mwawFile/mwawZip 等）由
[libmwaw-tools/0.3.22](../libmwaw-tools/README.md) 单独适配。

## 版本信息

- 当前适配版本: 0.3.23（上游 2025 发布）
- 上游: https://sourceforge.net/projects/libmwaw/
- 许可证: LGPL-2.1-or-later OR MPL-2.0
- 构建系统: autotools

## OHOS 适配要点

- 0.3.23 自带的 config.guess/config.sub 为 2024 版：config.guess 仍无
  HarmonyOS 分支（补丁按新版 GUESS 风格插入识别分支），config.sub 已原生
  支持 linux-ohos 三元组（无需再打补丁）
- configure 的 umask 077 临时目录在 HMDFS 上不可写，补丁改为 022
- 依赖 librevenge 包发布的 .pc/.la 文件 prefix 硬编码为 /，在 conan 包布局下
  pkg-config 与 libtool 都会读错路径。解法是在配方 build() 内 staging 纯
  `.a` 副本 + 本地生成正确 prefix 的 `.pc`，`PKG_CONFIG_PATH` 指向 staging 目录
- 包内不发布 bin/ 与 *.la：src/tools 检查工具无条件构建但由 libmwaw-tools
  承载；.la 内嵌逐轮变化的构建绝对路径，下游走 CMakeDeps 元数据

## 依赖说明

编译依赖：
- librevenge 0.0.5（文档解析底层库）
- zlib 1.3.1.1（同源 -fPIC 静态变体；force 直接依赖，统一 librevenge 传递链）

静态默认构建下，链接方需同时链接 librevenge 与 zlib（cpp_info.requires 已声明，
CMakeDeps 自动传递）。

## 功能验证（0.3.23, aarch64/OHOS）

| 功能 | 状态 |
|------|------|
| conan create（补丁 + staging + configure + make） | ✅ 通过 |
| C++ API: MWAWDocument::isFileFormatSupported() | ✅ 通过（非 Mac 载荷/空流正确拒绝，4 个 CHECK 断言全过） |
| conan-verify G0-G4/L2/L4/L5 | ✅ 全 PASS |

## 参考资料

- 源码: https://sourceforge.net/projects/libmwaw/
- 本项目 conan 配方: archives/l/libmwaw/0.3.23/conanfile.py
