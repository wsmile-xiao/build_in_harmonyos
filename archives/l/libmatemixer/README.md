# libmatemixer

MATE 桌面环境音频混音器库，提供音量控制的抽象层。

## 功能概述

- 提供音频设备音量控制的抽象接口
- 支持多种音频后端（Null、PulseAudio、ALSA）
- 提供 GObject 绑定

## OHOS 适配要点

1. **平台识别**：
   - config.guess 需添加 HarmonyOS 检测分支
   - config.sub 需添加 linux-ohos kernel-OS 组合和 OS 列表
2. **HMDFS 权限**：configure 中的 `umask 077` 需改为 `umask 022`
3. **依赖处理**：
   - glib 需要 PKG_CONFIG_PATH 正确设置
   - libintl 需使用 proxy-libintl 版本（含 g_libintl_* 符号）

## 依赖关系

- glib-2.0 >= 2.50.0
- gobject-2.0
- gmodule-2.0

## 注意事项

- Null 模块可正常编译
- PulseAudio/ALSA 模块因缺少依赖未构建

## 参考资料

- 官网：https://mate-desktop.org
- 源码：https://pub.mate-desktop.org/releases/