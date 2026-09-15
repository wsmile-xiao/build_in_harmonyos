# cream — Cream (for Vim)，Vim 编辑器的现代化配置层

## 概述

cream 是 Vim 编辑器的 GUI 化配置层（纯 Vim script），提供菜单驱动的
现代化编辑界面（CUA 键位、颜色主题、文件类型增强等），让初学者更容易
使用 Vim。上游托管于 SourceForge，0.43（2011-01-25）为最终发布版本。

## 版本

- 上游版本: 0.43（最终版）
- 许可证: GPL-3.0-or-later
- 上游 URL: https://cream.sourceforge.net
- 源码: https://downloads.sourceforge.net/project/cream/Cream/0.43/cream-0.43.tar.gz
- SHA256: b7adee33d5464f985a71722fdbe133e726bffebf34eae14c33674c4c5327d777

## 构建说明

- 类型: 纯 Vim script 数据/脚本发行（无需编译，拷贝安装）
- 构建系统: manual（conanfile 内 copy 按 `<prefix>/share/vim/cream` 布局安装）
- 编译器: 不适用
- 目标平台: OHOS aarch64
- 运行宿主: vim（仓内 archives/v/vim 9.1.1000 为旧式归档、无 conan 配方，
  不作为 conan requires，仅运行时组合使用）

## 功能

- 菜单驱动的编辑界面与 CUA 键位（Ctrl-C/Ctrl-V、Shift 方向键选择等）
- 行为模式切换（behaviours: 默认/Vim 兼容/专家）
- 颜色主题、文件类型增强、拼写检查、日历/模板等附加功能
- 多语言菜单（含简体中文 menu_zh_cn.utf-8.vim）
