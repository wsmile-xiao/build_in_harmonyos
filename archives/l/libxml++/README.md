# libxml++

## 简介
libxml++ 是一个 C++ XML 解析库，封装了 libxml2 库，提供现代化的 C++ API。

## 功能特性
- XML 文档解析和生成
- DOM 树操作
- XPath 查询支持
- SAX 解析器
- 文档验证（DTD、XML Schema）

## 编译信息
- 构建系统：meson
- 静态链接 libxml2.a（绕过 HMDFS 动态库权限限制）
- 不依赖 libxml2.so

## 已编译版本
- 5.4.0

## 参考
- 官网：https://libxmlplusplus.github.io/libxml++/