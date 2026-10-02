# libodsstream

## 简介
PAPPSO ODS (OpenDocument Spreadsheet) / TSV 流式读写库（Qt6），质谱桌面软件 XPfeeder/XTPCPP 家族的基础件。

## OHOS 适配
- 构建系统: CMake (C++20)
- vendored QuaZip 1.4（Qt6 线）——制品仓 quazip 包是 Qt5 线，与 Qt6 ABI 断裂
- 详见各版本 notes.md

## 依赖
- qtbase/6.11.1、qt5compat/6.11.1、zlib/1.3.1

## 功能验证
- 上游 Catch2 测试 5/5 + test_package 往返 11/11（见版本 notes.md）

## 参考
- https://forgemia.inra.fr/pappso/libodsstream
