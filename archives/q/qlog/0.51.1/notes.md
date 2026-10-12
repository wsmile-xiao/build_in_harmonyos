# qlog 0.51.1 适配笔记

## 编译环境
- 构建系统: qmake（上游 QLog.pro，Qt6）
- 编译日期: 2026-10-03
- 编译器: clang/clang++（/data/service/hnp/bin，aarch64-linux-ohos）
- 状态: built

## 编译步骤

```bash
cd archives/q/qlog/0.51.1
export TMPDIR=$HOME/tmp
conan create . -pr:h=$HOME/.conan2/profiles/ohos-aarch64 \
  -pr:b=$HOME/.conan2/profiles/ohos-aarch64 --build=missing
conan test test_package qlog/0.51.1 -pr:h=... -pr:b=...
```

配方 build() 关键动作：
1. `apply_conandata_patches()` 应用 13 个补丁；
2. 生成 qmake 参数：`CONFIG+=qlog_ohos`、`QMAKE_STRIP=`、`QMAKE_CC/CXX/LINK=clang++`、
   `HAMLIBVERSION_MAJOR=4/MINOR=7/PATCH=2`（绕过 pkg-config 探测）、`PREFIX=/usr`；
3. 为每个依赖包补 `INCLUDEPATH+=`、`QMAKE_LIBDIR+=`、`QMAKE_RPATHDIR+=`（多前缀 conan
   安装，运行期 RUNPATH 需覆盖全部依赖 lib 目录）；
4. 对 Qt 扩展模块（qtcharts/qtserialport/qtwebsockets）：复制改写
   `mkspecs/modules/*.pri` 中的路径为对应包前缀，经 `QMAKEMODULES` 暴露给 qmake
   （chinese/1.0.3.r58、qpdfview 先例），并对链接行中误解析到 qtbase 前缀的
   `libQt6Charts.so/libQt6SerialPort.so/libQt6WebSockets.so` 做路径改写；
5. `make -j1`（R9）+ `make install INSTALL_ROOT=<pkg>`，随后将 `<pkg>/usr/bin` 归位为
   `<pkg>/bin`；
6. 最后用 binary-sign-tool 对 ELF 做 .codesign 签章（必须放最后一步）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | QtWebEngine 不可用 | OHOS 制品仓无 qtwebengine | 新增 `qlog_ohos` CONFIG 选项，`QLOG_NO_WEBENGINE`：QLog.pro 把 WebEnginePage 移出源码树；新增 MapWidget 公开绘图接口 + MapPageControllerOffline.cpp 离线实现；StatisticsWidget.ui/QSODetailDialog.ui 中 QWebEngineView 替换为 MapWidget（customwidget extends=QGraphicsView） |
| 2 | QPrinter/QPrintDialog 不可用 | qtbase-sql-dbus 构建 FEATURE_printsupport=OFF | `QLOG_NO_PRINTSERVICE` 守卫 QSLPrintLabelRenderer/QSLPrintLabelDialog：printAll no-op、print()/exportPdf() 弹提示框；屏幕预览与图片导出保留 |
| 3 | QSslSocket 链接失败 | qtbase 构建 FEATURE_ssl=OFF，qtnetwork-config.h 定义 QT_NO_SSL=1 | main.cpp 与 MainWindow.cpp 中 `sslLibraryVersionString()` 用 `#ifndef QT_NO_SSL` 守卫 |
| 4 | qmake `qlog_ohos: file.cpp \` 行内条件在 SOURCES 块内解析成目标 | qmake 语法限制 | 改为独立行 `qlog_ohos: SOURCES += ...` |
| 5 | MapLayer::None 不存在 | 上游枚举无 None | 离线控制器用 `MapLayer::Layers()` 默认构造 |
| 6 | OnlineMapWidget::setIBPBand 签名不匹配 | 离线分支实现少一个参数 | 补齐第 4 个参数 |
| 7 | uic 生成 ui_QSODetailDialog.h 调 mapView->setUrl | .ui 中 QWebEngineView 的 url 属性被 uic 展开为 setUrl | 从 QSODetailDialog.ui 删除 `about:blank` url 属性 |
| 8 | 链接报 libQt6Charts.so 路径不存在 | qmake 多前缀下 QT 模块库路径解析到第一个（qtbase）前缀 | build() 中对生成的 Makefile 做正则改写，指向 qtcharts/qtserialport/qtwebsockets 实际包路径 |
| 9 | 包内无 bin 目录 | 上游 target.path=$$PREFIX/bin 且 PREFIX=/usr | make install 后将 `<pkg>/usr/bin` 归位为 `<pkg>/bin` |
| 10 | CI worker（MR #14448，#79959/#81268）`make install` 阶段 qinstall 拷贝任意文件报 `Value too large for data type`（EOVERFLOW）——#79959 是 qlog 二进制，#81268 改为 no-op 后连几十字节的 qlog.desktop 也失败 | qmake `qinstall`（QFile::copy）在部分 worker 的 hmdfs 上对任意文件拷贝返回 EOVERFLOW，与文件大小无关（编译/链接均正常，产物仅约 118MB；本机实测同盘 4.4GB 读/写循环拷贝正常） | package() 完全弃用 `make install`：按上游 QLog.pro INSTALLS 清单用 python `shutil.copy2` 直接安装（qlog 二进制 0755，desktop/icon/metainfo/manpage 按包内既有 hnp 布局仅保留 bin/qlog），带逐文件大小校验，缺失即报错 |

## 源码修改

补丁（archives/q/qlog/0.51.1/patches/，13 个）：
- QLog.pro.patch：QT 模块拆分、qlog_ohos 选项与条件源码、unix 硬编码 /usr/local 改 qlog_ohos 显式 LIBS
- ui_MapWidget.h/.cpp.patch：新增 addPoint/addHomePoint/addLine/clearPoints 公开接口
- ui_MapPageController.h.patch：attach 签名按 QLOG_NO_WEBENGINE 拆分、私有成员按模式拆分
- ui_MapPageControllerOffline.cpp.patch：新增离线地图控制器实现（点/家台/短线用 MapWidget 绘制，在线图层降级 no-op + qCDebug）
- ui_OnlineMapWidget.h/.cpp.patch：fallback 派生 MapWidget，drawWSJTXSpot 用 Gridsquare::mapDisplayGrid 转坐标
- ui_QSODetailDialog.ui.patch / ui_StatisticsWidget.ui.patch：QWebEngineView→MapWidget、移除 url 属性
- ui_QSLPrintLabelDialog.cpp.patch / core_QSLPrintLabelRenderer.cpp.patch：打印服务禁用守卫
- core_main.cpp.patch / ui_MainWindow.cpp.patch：QSslSocket 用法 QT_NO_SSL 守卫

## 依赖版本

qtbase/6.11.1、qtbase-gui/6.11.1、qtbase-sql-dbus/6.11.1、qtcharts/6.11.1、
qtserialport/6.11.1、qtwebsockets/6.11.1、qtkeychain/0.14.2、hamlib/4.7.2、
sqlite3/3.53.4、openssl/3.5.6.1.2、zlib/1.3.2.1

## 验证结果

```bash
conan test test_package qlog/0.51.1 ...   # exit 0
<package>/bin/qlog --version   # 输出: qlog 0.51.1
<package>/bin/qlog --help      # 输出全部命令行选项（--namespace/--language/--debug 等）
# ELF .codesign 签章校验通过；DT_NEEDED 修复检查: entries materialized: 0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/qlog | 约 15MB | aarch64-linux-ohos 主程序（已签章） |

## 注意事项

- **功能降级申报**：
  1. 在线地图（OpenStreetMap/Esri 瓦片）不可用，地图页为上游自带离线 QGraphicsView 地图；
     卫星图层、MUF/Aurora/IBP 覆盖层、在线航迹跟随等在线能力降级为 no-op（debug 日志提示）；
  2. QSL 标签打印与 PDF 导出不可用（qtbase 无 printsupport）；屏幕预览与卡片图片导出保留；
  3. TLS 版本信息显示降级（qtbase FEATURE_ssl=OFF，QSslSocket 相关仅影响 About 页展示文本）。
- **上游测试**：tests/ 下 18 个 QTest 套件（tests.pro SUBDIRS）。已在鸿蒙 PC 本机
  （aarch64 原生，Qt 6.11.1 conan 环境）真实构建并全部执行：
  **2501 passed / 0 failed / 5 skipped**（数据驱动参数化展开；函数口径 163，18/18 套件 exit=0）。
  skip 5 项均为 CredentialStoreTest 的 qtkeychain 后端不可用（鸿蒙无 D-Bus Secret Service，
  上游 QSKIP 设计）。详见 `reports/upstream-test/README.md` 与全套件结果文件；
  测试专用 3 处上游缺陷修复（QTEST_APPLESS_MAIN→QTEST_MAIN ×2、补 QTcpSocket include）
  仅用于测试执行，未进入交付补丁集。
- 上游编译有少量 deprecation 警告（setTimeSpec 等），不影响功能。
---

**编译结束**: 2026-10-10（CI #79959 EOVERFLOW 修复后本机全量 CI 重跑通过）
**最终状态**: built
