# libcdk5 - Curses Development Kit (第 5 代)

## 概述

libcdk5 (CDK，Curses Development Kit) 是一个为 curses 终端应用程序提供预定义 widget 的开发工具库。它提供了丰富的 UI 组件（如按钮、菜单、滚动列表、对话框、日历等），简化了基于 curses 的终端应用开发。上游库名为 cdk，本仓归档键名/Conan 包名为 libcdk5（对应第 5 代主线）。

## 版本信息

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 5.0.20260119 | built | 2026-07-28 |

## 软件描述

- **名称**: libcdk5 (上游库名 cdk)
- **版本**: 5.0.20260119
- **描述**: Curses development kit provides predefined curses widget for apps
- **构建系统**: autotools
- **语言**: C
- **License**: MIT

## 主要 widget

CDK 提供以下 widget 类型：
- **Alphalist** - 字母排序列表
- **Button** / **Buttonbox** - 按钮
- **Calendar** - 日历选择器
- **Dialog** - 对话框
- **Entry** - 文本输入框
- **Fselect** - 文件选择器
- **Graph** / **Histogram** - 图形显示
- **Itemlist** - 项目列表
- **Label** - 文本标签
- **Marquee** - 跑马灯
- **Matrix** - 矩阵输入
- **Mentry** - 多行输入
- **Menu** - 菜单
- **Radio** - 单选按钮
- **Scroll** / **Scroller** - 滚动列表
- **Selection** - 选择列表
- **Swindow** - 滚动窗口
- **Scale** / **Slider** - 滑块
- **Template** - 模板输入
- **Viewer** - 文本查看器

## 依赖

| 依赖 | 版本 | 类型 |
|------|------|------|
| ncursesw | 6.4 | 必需 (curses 开发库, via cmd-pkgs) |

## HarmonyOS 适配说明

libcdk5 在 HarmonyOS 平台上需要以下适配：
1. **E007**: config.guess/config.sub 需要添加 HarmonyOS (__OHOS__) 检测分支
2. **ncursesw 依赖**: 通过 cmd-pkgs 安装 ncurses 6.4 静态库，用 --with-curses-dir 指向安装路径
3. **config.status workaround**: HMDFS 平台 mktemp 创建的目录内无法写入文件，需修改 config.status 的临时目录创建逻辑

## 编译产物

- 静态库: `libcdkw.a`
- 配置工具: `cdk5-config`
- 头文件: `cdk.h` + 各 widget 头文件
- Demo 程序: appointment, clock, command, fileview, rolodex, stopSign, vinstall 等
