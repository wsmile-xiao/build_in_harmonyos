# libabw-tools

## 软件描述

libabw 是 LibreOffice/Document Foundation 项目解析 AbiWord 文档（`.abw`）的
C++ 库，libabw-tools 是其源码树构建产物中的命令行转换工具集（与已发布的
libabw 库同源，本包整树构建并随包交付工具 + 静态库，同 libmwaw-tools 模式）：

- **abw2text**: 转换为纯文本（`--info` 输出文档元数据）
- **abw2html**: 转换为 HTML
- **abw2raw**: 输出原始解析结构（`--callgraph` 显示调用图嵌套层级）

## 版本信息

- 当前版本: 0.1.3
- 官方发布点: https://dev-www.libreoffice.org/src/libabw/
- 项目主页: https://wiki.documentfoundation.org/Development/libabw

## OHOS 适配

- 构建系统为 Autotools（dist 自带预生成 `configure`，GNU Autoconf 2.69），
  `--enable-static --disable-shared` 构建静态库，工具链接期吸收
- 与 libabw 0.1.4 同一源码树（configure.ac 仅版本号不同，src/lib/Makefile.am
  逐字节相同），0.1.4 已验证配方的 OHOS 构建机制整体平移，逐项对 0.1.3
  tarball 复核（umask 077 恰 2 处；config.sub 对两个三元组 rc=0）
- 无补丁：源码未做任何改动（patches_applied: []）
- 关键坑：
  - librevenge 包 `.la` 文件 libdir 硬编码 `//lib` → 「只放 .a 的干净 -L 目录」引用
  - 设备无 pkg-config → 五组 `PKG_CHECK_MODULES` 变量（REVENGE/
    REVENGE_GENERATORS/REVENGE_STREAM/LIBXML/ZLIB）逐个导出
  - 工具是 PIE 且链**共享** libxml2，CI L2 冒烟门禁无 LD_LIBRARY_PATH 跑
    bin/* → `LDFLAGS` 注入 `-Wl,-rpath,<libxml2 包>/lib` 内嵌运行时路径
  - configure 临时目录 `umask 077` 在 HMDFS 上不可写 → 内联改写 022

## 依赖说明

编译/运行依赖：
- librevenge 0.0.5（文档解析底层库，静态）
- libxml2 2.15.3.1（XML 读取，**共享**库，运行时经内嵌 RPATH 解析）
- zlib 1.3.1（压缩流，静态吸收）
- boost 1.90.0.3（tool_requires，仅构建期头文件）

abw2text/abw2html/abw2raw 运行时仅依赖 libxml2.so.16、libc++_shared.so 与
libc.so（RPATH 已内嵌）。

## 参考资料

- 源码: https://dev-www.libreoffice.org/src/libabw/
- 本项目 conan 配方: archives/l/libabw-tools/0.1.3/conanfile.py
