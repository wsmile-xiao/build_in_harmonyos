# qt5-qtcharts 5.15.2 编译笔记

## 编译环境
- 平台: aarch64-linux-ohos (鸿蒙)
- 编译器: clang++ (OHOS SDK)
- Qt5版本: 5.15.2 (已安装在 ~/usr/local/Qt5/)
- 构建系统: qmake

## 依赖
- qt5-qtbase 5.15.2 (Qt Core, Gui, Widgets, Network)
- qt5-qtdeclarative 5.15.2 (Qml, Quick, QmlModels)

## 编译步骤

### 1. 设置环境
```bash
export PATH=/storage/Users/currentUser/usr/local/Qt5/bin:$PATH
export QTDIR=/storage/Users/currentUser/usr/local/Qt5
```

### 2. qmake配置
```bash
cd ~/tmp/qt5-qtcharts-src
/storage/Users/currentUser/usr/local/Qt5/bin/qmake qtcharts.pro
```
成功，生成了.qmake.stash和.qmake.cache文件。

### 3. 编译
```bash
make -j2
```
成功完成，耗时约478秒。有一个deprecation warning（createTextureFromId -> createTextureFromNativeObject），不影响编译。

### 4. 安装
```bash
make install
```
安装到 ~/usr/local/Qt5/，包括：
- libQt5Charts.so.5.15.2 (1669192 bytes, stripped)
- libQt5Charts.prl, libQt5Charts.la
- Qt5Charts.pc (pkgconfig)
- Qt5Charts headers (include/QtCharts/)
- qt_lib_charts.pri, qt_lib_charts_private.pri
- Qt5Charts cmake config
- QML plugin: qml/QtCharts/libqtchartsqml2.so
- QML types: qml/QtCharts/plugins.qmltypes, qmldir
- Designer QML files

## 安装产物验证
- `file libQt5Charts.so.5.15.2`: ELF 64-bit LSB shared object, ARM aarch64, dynamically linked, stripped ✅
- 所有头文件正确安装 ✅
- pkgconfig文件正确安装 ✅
- QML插件正确安装 ✅

## 无源码修改
本次编译无需修改任何源码，直接使用原始git clone的v5.15.2源码即可编译通过。

## 编译结束
**最终状态**: built
---

**编译结束**: 2026-05-31 03:37
**最终状态**: built
