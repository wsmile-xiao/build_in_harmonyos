# drawing 1.0.2 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-30
- 编译器: clang / clang++
- 状态: success

## 编译步骤

1. 下载并解压 drawing 1.0.2 源码
2. 应用 2 个补丁（跳过 help 子目录、跳过 update-desktop-database）
3. 执行 meson setup 配置（禁用翻译和帮助文档）
4. meson compile 编译
5. DESTDIR 方式安装验证通过
6. 预编译包制作完成（含主包和 debug 包）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | help 子目录编译失败 | itstool 需要 libxml2 Python 模块，OHOS 上不可用 | 注释掉 meson.build 中的 `subdir('help')` |
| 2 | postinstall 脚本执行 update-desktop-database 失败 | OHOS 上不存在 update-desktop-database 工具 | 在 postinstall.py 中跳过该步骤 |

## 依赖版本

- GTK+3
- glib
- meson >= 0.50
- gdk-pixbuf, cairo, pango, harfbuzz, freetype, fontconfig

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| drawing-1.0.2-ohos-aarch64.tar.gz | 840KB | 主包 |
| drawing-1.0.2-ohos-aarch64-debug.tar.gz | 10KB | debug 包 |