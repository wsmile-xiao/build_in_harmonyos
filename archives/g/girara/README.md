# girara - User interface library for zathura

## 简介
girara 是 zathura 文档查看器使用的用户界面库，提供数据结构（列表/树节点）、输入历史、模板、日志等通用工具函数。

## OHOS 适配
- 使用 meson 构建
- 依赖 glib/2.84.0（Conan 包，通过 PkgConfigDeps 暴露 glib-2.0/gobject-2.0/gio-2.0）
- 补丁条件化 tests subdir，禁用 doxygen 文档
- 共享库 libgirara.so 构建后用 binary-sign-tool 重签

## 功能
- 数据结构：列表、树节点、迭代器
- 输入历史管理
- 模板引擎
- 日志工具

## 许可证
Zlib
