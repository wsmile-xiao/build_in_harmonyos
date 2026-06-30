# libpaper

## 简介

libpaper 是一个处理纸张尺寸和纸张名称的库，主要用于打印系统和文档处理软件。

## 功能概述

- 提供纸张尺寸数据库和查询接口
- 支持国际标准纸张尺寸（A4, Letter 等）
- 提供 paperconf 命令行工具用于查询纸张配置
- 支持自定义纸张尺寸配置

## OHOS 适配要点

1. **缺少 configure 脚本**：Debian 源码包只包含 configure.ac，需要 autoreconf -fvi 生成
2. **bootstrap 补丁**：autoreconf 生成的文件（configure、ltmain.sh 等）需要打包为补丁
3. **umask 问题**：遇到 HMDFS 临时目录权限问题，已通过修改 configure 解决

## 依赖关系

- **编译依赖**：无外部依赖
- **运行依赖**：无外部依赖

## 参考资料

- Debian 源码：https://packages.debian.org/source/libpaper