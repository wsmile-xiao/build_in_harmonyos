# libpng

## 简介
PNG image format library

## OHOS 适配
- 构建系统: autotools
- 使用 libtool 生成正确的 `libpng16.so.16` SONAME。
- 使用 Conan 显式解析 zlib，并通过单作业执行完整上游测试。
- 保留上游安装的 `pngfix` 与 `png-fix-itxt` 命令行工具。
- 详见各版本 notes.md 获取适配详情

## 依赖
- zlib

## 功能验证
- 上游 `make check` 完整测试清单。
- Conan 消费者链接并调用 libpng 公开版本 API。

## 参考
- http://www.libpng.org/
