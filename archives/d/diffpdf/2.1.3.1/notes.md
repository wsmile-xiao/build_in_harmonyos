# diffpdf 2.1.3.1 适配笔记

## 软件身份

- **软件名**: diffpdf 2.1.3.1（qtrac.eu, Simon Guest）
- **类型**: Qt5 GUI PDF 对比工具（可执行程序，非库）
- **上游**: http://www.qtrac.eu/diffpdf.html
- **版本真实性**: 2.1.3.1 = 上游"Qt5 + CMake 移植版"（CHANGES 明确记载）；
  qtrac.eu 官网仅留 2.1.3 tar.gz，2.1.3.1 的官方载体是 Debian 源码包
  `diffpdf_2.1.3.1.orig.tar.xz`（sha256 a7cbea38...，orig 包 = 上游 tarball
  原样打包，无 Debian 修改）→ R39 采用 Debian 官方 pool 源

## 编译环境

- 构建系统: cmake（自研 CMakeLists，上游的需 ECM+poppler-qt5 不可用）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 / clang++（OHOS aarch64, musl）
- Profile: ohos-aarch64（cppstd17 / armv8 / Release）
- 状态: published（conan create + test_package PASS）

## 核心适配决策（W0 依赖探测结论）

制品仓 poppler（25.12.0/25.12.0.1/25.12.0.2）全部 ENABLE_QT5=OFF/QT6=OFF
（无 Qt 绑定），且无独立 poppler-qt5 包 → 上游 `find_package(Poppler Qt5)`
不可能满足。**适配方案：写 poppler-qt5 兼容 shim**（patches/poppler-qt5.h/.cpp），
把 diffpdf 用到的 API（Document::load/isLocked/numPages/page/infoKeys/info/
date/setRenderHint、Page::pageSize/renderToImage/textList、TextBox::text/
boundingBox/charBoundingBox）在 poppler-cpp 前端（poppler 包内 libpoppler-cpp.so）
之上重实现，上游 21 个源文件零修改。

API 映射要点：
- poppler-cpp 枚举在 poppler 全局命名空间（crop_box/rotate_0，非 page:: 成员）
- ustring::to_utf8() 返回 byte_array（非 std::string）
- page_renderer::render_page + image(format_argb32) → QImage::Format_ARGB32
  （0xAARRGGBB native endian，aarch64 LE 匹配）
- renderHint 存在 Document 上，渲染时经 page_renderer::set_render_hints 应用

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan 图 "Version conflict between zlib/1.3.1.1 and zlib/1.3.1" | qt5-qtbase/5.15.2.2 链锚定 zlib/1.3.1（非 PIC libz.a），poppler 链锚定 zlib/1.3.1.1（PIC） | consumer `zlib/1.3.1.1 override=True` 统一到 PIC 版；qt5-qtbase 因 pid 变化从源码构建（baka 2.0.4 先例，PR !6487 已验证此路径） |
| 2 | qt5-qtbase 源码构建 configure 阶段 qmake "Error relocating ... __cxa_pure_virtual" | 本机 shell 的 LD_LIBRARY_PATH 有畸形项（前导空格路径），musl loader 解析失败 | conan 命令前 export 干净的 LD_LIBRARY_PATH（前置 OHOS SDK c++ 目录 + /system/lib64） |
| 3 | 试错记录：override 到 zlib/1.3.1（保 qt5 binary）→ poppler 源码构建链非 PIC libz.a 报 R_AARCH64 relocation | zlib/1.3.1 的 libz.a 非 PIC，不能链进 libpoppler.so | 弃用该方向，回到方案 1（override 1.3.1.1 + qt5 源码构建） |
| 4 | patch 应用失败 "source/target file does not exist: diffpdf-v2.1.3.1/CMakeLists.txt" | source() 用了 strip_root=True，补丁路径含顶层目录 | source() 改 strip_root=False，外层 CMakeLists.txt（tarball 根）add_subdirectory(diffpdf-v2.1.3.1) |
| 5 | 编译报 'QtCore/qstring.h' file not found | 源码构建的 qt5 包 include/QtCore/5.15.2/ 布局 + `#include <QtCore/...>` 需以 include/ 根解析 | -I include 根 + 各模块目录 + 5.15.2 版本目录 |
| 6 | 链接报 undefined symbol AboutForm::staticMetaObject | CMAKE_AUTOMOC 报 "No valid Qt version found"（手动链 Qt5 无 find_package，AUTOMOC 无法发现 moc） | 弃 AUTOMOC，add_custom_command 显式调 qt5-qtbase/bin/moc（LD_LIBRARY_PATH=qt5 lib），moc_*.cpp 进 target sources |
| 7 | moc/rcc/lrelease 运行失败（探索期） | 同问题 2 的 loader 解析 | CMakeLists 里 cmake -E env LD_LIBRARY_PATH=${DIFFPDF_QT5_LIB_DIR} 包裹 moc；探索脚本同理 |

## 源码修改

- patches/0001-add-cmakelists-for-ohos-poppler-cpp-build.patch（新增 4 文件）：
  - `CMakeLists.txt`（tarball 根，add_subdirectory 引导）
  - `diffpdf-v2.1.3.1/CMakeLists.txt`（替换上游 ECM/poppler-qt5 版：手动 moc + 显式 Qt5/poppler-cpp 接线）
  - `diffpdf-v2.1.3.1/poppler-qt5.h` + `poppler-qt5.cpp`（poppler-qt5 → poppler-cpp 兼容 shim）
  - `diffpdf-v2.1.3.1/diffpdfversion.h`（上游 ECMSetupVersion 生成的等价物）
- 上游 21 个 .cpp/.hpp 零修改

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| qt5-qtbase | 5.15.2.2 | Core/Gui/Widgets/PrintSupport（zlib 统一后源码构建，与制品仓二进制同配方） |
| poppler | 25.12.0.1 | poppler-cpp 前端（binary 命中；25.12.0.2 链重 cairo/glib/boost，弃用） |
| zlib | 1.3.1.1 (override) | PIC 版，链进共享库 |

## 验证结果

```bash
conan create ...（G2 PASS，产物 diffpdf/2.1.3.1 aarch64 musl ELF）
======== Launching test_package ========
[test] diffpdf --help
✅ diffpdf --help OK (QApplication init + usage output verified)
```

- conan-verify：G1/G2/G3/G4 全 PASS（G2 含干净构建）
- W3 本地 CI 模拟：setup.sh ✅ + conan create ✅（.ci-result.json exit_code=0）
- R40 口径：Qt GUI 应用，OHOS PC 图形栈仅 offscreen/minimal/vnc 插件；
  链路级验证 = --help（QApplication 初始化 + 参数解析 + usage 输出），
  完整 GUI 交互不在验证范围（如实说明）

## 注意事项

- qt5-qtbase 源码构建（zlib 1.3.1.1 图下）要求运行环境 LD_LIBRARY_PATH 可解析
  libc++ 符号（本机默认 shell 有畸形路径项，需 export 干净值）；CI 沙箱无此问题
  （baka PR !6487 先例绿）
- poppler-qt5 shim 的 charBoundingBox 按 UTF-8 字节数索引 char_bbox（简单文字
  场景 glyph 数≈码点数；复杂文字脚本可能偏差，diffpdf 主场景 Latin/CJK 可用）
---

**编译结束**: 2026-09-03 20:07
**最终状态**: published
