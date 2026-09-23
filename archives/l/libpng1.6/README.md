# libpng1.6

## 简介
PNG image format library（1.6 系列）

## OHOS 适配
- 构建系统: autotools
- 使用 libtool 保证正确的 `libpng16.so.16` SONAME。
- 使用 Conan 注入 zlib，构建期执行完整上游测试。
- 构建产物安装 `pngfix` 与 `png-fix-itxt` 命令行工具。
- 具体版本见各版本 notes.md（如版本目录中的编译记录）。

## 依赖
- zlib

## 测试验证
- 上游 `make check` 完整测试清单。
- Conan 消费者测试调用 libpng 真实版本与读写 API。

## 参考
- https://libpng.sourceforge.io/
