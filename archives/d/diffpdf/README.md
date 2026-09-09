# DiffPDF

DiffPDF 是 Qt5 图形界面的 PDF 对比工具（作者 Simon Guest, qtrac.eu）：
逐词（words）、逐字符（characters）或外观（appearance）三种模式对比两个
PDF 文件，并把差异高亮显示。支持页码范围对比、差异页跳转与打印导出。

- 上游: http://www.qtrac.eu/diffpdf.html
- 版本: 2.1.3.1（Qt5 + CMake 移植版；官方发布载体为 Debian 源码包
  `diffpdf_2.1.3.1.orig.tar.xz`，上游 tarball 原样打包）
- 许可证: GPL-2.0-or-later

## HarmonyOS PC 适配（aarch64 / musl / clang 15）

| 项 | 说明 |
|----|------|
| Qt5 | conan 包 `qt5-qtbase/5.15.2.2`（Core/Gui/Widgets/PrintSupport） |
| Poppler | conan 包 `poppler/25.12.0.1`（poppler-cpp 前端） |
| poppler-qt5 绑定 | 制品仓 poppler 未启用 Qt 绑定（ENABLE_QT5=OFF）→ 本适配新增 **poppler-qt5 兼容 shim**（patches/poppler-qt5.h/.cpp），在 poppler-cpp 之上重实现 diffpdf 用到的 `Poppler::Document/Page/TextBox` API，上游 21 个源文件零修改 |
| 构建 | 自研 CMakeLists（上游的需 ECM + poppler-qt5），moc 由 qt5-qtbase/bin/moc 显式调用 |
| 测试 | test_package 链路级冒烟（`diffpdf --help`，offscreen 平台） |

用法：`diffpdf [options] [file1.pdf [file2.pdf]]`（详见 `diffpdf --help`）
