# adwaita-fonts-mono 50 适配笔记

## 概述

将 GNOME Adwaita Mono 字体（v50.0）适配为 HarmonyOS PC 的 Conan 数据包。
Adwaita Fonts 是 GNOME 桌面的默认字体家族，包含 Adwaita Mono 和 Adwaita Sans。

## 安装内容

仅安装 **Adwaita Mono** 字体（4 个 TTF 文件），排除 Adwaita Sans：

- `AdwaitaMono-Regular.ttf`
- `AdwaitaMono-Bold.ttf`
- `AdwaitaMono-Italic.ttf`
- `AdwaitaMono-BoldItalic.ttf`

安装目录：`share/fonts/AdwaitaMono/`

## 上游测试情况

上游 `adwaita-fonts` 项目是纯字体数据包，`meson.build` 中仅有 `install_data()`，
没有自动化测试用例（test 目标数为 0）。所有验证在 `test_package/conanfile.py` 中完成。

## Sans 字体说明

上游 tarball 同时包含 Adwaita Sans（2 个 TTF 文件：Regular、Italic）。
本包名称为 `adwaita-fonts-mono`，按约定只打包 Mono 字体。
如果需要 Adwaita Sans，应另行创建 `adwaita-fonts-sans` 包，或使用完整的 `adwaita-fonts` 包名。

## 构建系统

Meson（仅 `install_data`，无编译步骤），Conan 配方按纯数据包处理：
- `package_type = "unknown"`
- 无 `cpp_info.libs`
- 无 `cpp_info.bindirs`
- 通过 `cpp_info.resdirs` 暴露字体目录供 fontconfig 等工具发现

## 来源

- Source URL: `https://download.gnome.org/sources/adwaita-fonts/50/adwaita-fonts-50.0.tar.xz`
- SHA256: `4c927fbfeec1c503801ba510c2c94e0054c82c522cf7ba0d3be5d4d41fcf5c86`
- License: SIL Open Font License 1.1 (OFL-1.1)
---

**编译结束**: 2026-08-05 08:28
**最终状态**: built
