# yad

yad (Yet Another Dialog) 是一个 GTK+ 对话框显示工具，用于从 shell 脚本创建图形界面对话框。

## 功能概述

- 显示各种 GTK+ 对话框（消息、输入、文件选择、进度等）
- 支持 HTML、图标浏览器、通知等高级功能
- 支持嵌入模式（plug/socket，X11）

## OHOS 适配

- **构建系统**: autotools
- **X11移除**: HarmonyOS使用Broadway后端而非X11，plug/socket不可用
- **关键补丁**: 7个补丁（E007适配 + X11排除 + umask修复）
- **禁用功能**: html/spell/sourceview（webkit2/gspell/gtksourceview不可用）

## 运行依赖

- GTK3（Broadway 后端）

## 参考资料

- 源码: https://github.com/v1cont/yad
- 版本: 14.2
