# prefixsuffix homebrew 适配笔记

## 编译环境

- 构建系统：Autotools
- 编译日期：2026-07-15
- 编译器：clang++（C++ GUI 应用程序）
- 状态：failed

## 源码信息

- 版本：0.6.9（Homebrew 对应上游版本）
- 官方源码 URL：`https://download.gnome.org/sources/prefixsuffix/0.6/prefixsuffix-0.6.9.tar.xz`
- SHA256：`fc3202bddf2ebbb93ffd31fc2a079cfc05957e4bf219535f26e6d8784d859e9b`

## 软件简介

prefixsuffix 是 GNOME 桌面环境下的 GUI 批量文件重命名工具，使用 gtkmm3（C++ GTK 绑定）
开发。主要功能：
- 通过添加前缀或后缀批量重命名文件
- 支持目录递归处理
- 提供 GTK 图形界面交互

## 依赖

### 构建期依赖

| 依赖 | 类型 | 说明 |
|------|------|------|
| intltool | 构建工具 | 国际化处理，需 perl + XML::Parser |
| pkg-config | 构建工具 | GUI 依赖检测 |
| gettext | 构建工具 | 国际化运行时库 |

### 缺失依赖

| 依赖 | pkg-config 名称 | 说明 |
|------|-----------------|------|
| glib | glib-2.0 | GLib 基础库 |
| gtk+3 | gtk+-3.0 | GTK 图形工具包 |
| gtkmm3 | gtkmm-3.0 | C++ GTK 绑定 |
| glibmm | glibmm-2.4 | C++ GLib 绑定 |
| atkmm | atkmm-1.6 | C++ ATK 绑定 |
| cairomm | cairomm-1.0 | C++ Cairo 绑定 |
| pangomm | pangomm-1.4 | C++ Pango 绑定 |
| libsigc++ | sigc++-2.0 | C++ 信号框架 |

OHOS Conan 制品仓和 CI 环境缺少上述 GTK3 C++ 依赖链。

## 编译步骤

1. CI #3074 成功下载并解压 GNOME 官方源码。
2. 编译器检查、C++11 检查、交叉编译检测和 pkg-config 检查均通过。
3. configure 在检查 `gtkmm-3.0` 时失败。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败 | OHOS CI 无 `gtkmm-3.0.pc` | 上游必须依赖 gtkmm3，无法通过配置选项禁用 |
| 2 | 依赖链无法补齐 | 仓库缺少 glibmm、gtkmm3、pangomm、atkmm 和 cairomm-1.0 | 需要先分别适配完整 GTK3 C++ 依赖链 |

## 测试说明

prefixsuffix 上游无独立测试套件。由于 configure 阶段失败，未生成二进制，
无法执行 Homebrew 的 `prefixsuffix --version` 验证。

## 知识积累

- `CONFIG_SHELL` 并非本次失败原因，CI 已设置为 `/data/service/hnp/bin/bash`
- 上游 configure 直接要求 `gtkmm-3.0`，没有无 GUI 构建模式
- 现有 cairomm 1.18.0 提供 `cairomm-1.16`，不满足 gtkmm3 所需的 `cairomm-1.0`
- 完成 prefixsuffix 适配前，必须先独立适配并发布完整 GTK3 C++ 依赖链
