# Suil

## 简介
Suil 是 LV2 生态的插件 GUI 承载库：宿主通过 libsuil 把 Qt/GTK/X11/Cocoa 等 GUI 工具包实现的 LV2 插件界面嵌入宿主窗口，而宿主代码不直接依赖任何 GUI 工具包（按需 dlopen 适配模块）。

## 功能概述
- LV2 插件 UI 实例化（suil_instance_new）
- 多工具包 UI 包装（X11 in GTK2/GTK3/Qt5/Qt6、Cocoa、Win32）
- 宿主回调契约（port write/index/subscribe/unsubscribe/touch）
- UI 支持能力探测（suil_ui_supported）

## OHOS 适配
- 构建系统: meson 1.11.0（上游 0.10.26 已从 waf 迁移 meson，LV2 全家桶 2021 迁移）
- 核心库 libsuil-0.so 零补丁交叉编译通过（aarch64-linux-ohos clang 15）
- OHOS PC 无 X11/GTK/Qt 窗口系统接入，GUI 适配模块按上游 feature 开关禁用（gtk2/gtk3/qt5/qt6/x11/cocoa=disabled）；主库按上游 PACKAGING.md 设计本就不依赖工具包
- 上游 headers 测试（编译+链接 suil_dep）+ 消费者 API 测试通过

## 依赖
- lv2/1.18.11-git（制品仓已发布）

## 功能验证
```bash
# 消费者测试：suil_init + host 生命周期 + ui_supported 探测
./test_suil  # 输出: suil consumer test PASSED
pkg-config --modversion suil-0  # 输出: 0.10.26
```

## 参考
- 官网: https://drobilla.net/software/suil.html
- 源码: https://gitlab.com/lv2/suil
