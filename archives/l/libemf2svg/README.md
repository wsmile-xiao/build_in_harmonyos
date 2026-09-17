# libemf2svg

## 简介
libemf2svg 是 Microsoft EMF (Enhanced Metafile) 到 SVG 的转换库，常用于处理内嵌在其他 MS 文件格式中的 EMF/EMF+ 数据。

## OHOS 适配
- 构建系统: cmake（Library-only：演示工具需要 glibc argp，OHOS 上缺失）
- 编译器: clang 15
- libuemf 使用上游自带源码，无需额外系统依赖
- 上游无 ctest/make-check 目标；测试经 test_package 直调库入口覆盖核心转换路径

## 依赖
- libpng/1.6.58.2
- freetype/2.14.3
- fontconfig/2.18.1.1
- libxml2/2.15.3.1

## 参考
- 上游: https://github.com/kakwa/libemf2svg
