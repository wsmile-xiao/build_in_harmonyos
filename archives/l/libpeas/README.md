# libpeas

GObject-based plugins engine.

## 描述

libpeas 是一个基于 GObject 的插件引擎，支持多种编程语言的插件加载。

## 编译版本

- 2.2.1

## 依赖

- glib 2.88.0

## 编译说明

使用 meson 构建系统，禁用不必要的功能（gtk_doc、introspection、vapi等）。

## 平台适配

- libintl 头文件宏重命名问题（使用 extern 声明绕过）

## 产物

- libpeas-2.so: 插件引擎库
- 头文件、pkg-config文件
