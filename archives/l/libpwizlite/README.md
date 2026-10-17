# libpwizlite

## 简介
PAPPSO 精简版 proteoWizard msdata 库——质谱数据（mzML/mzXML/MGF/MSn）读取，pappsomspp 的命脉前置。

## OHOS 适配
- 构建系统: CMake (C++17)
- vendored boostorg/thread+chrono（boost-1.84.0 tag）补制品仓 boost 无 thread/chrono 编译库的缺口
- 详见各版本 notes.md

## 依赖
- boost/1.84.0、zlib/1.3.1

## 功能验证
- test_package mzML 解析 8/8（见版本 notes.md）

## 参考
- https://forgemia.inra.fr/pappso/libpwizlite
