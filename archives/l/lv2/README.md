# LV2

## 简介
LV2 是一个开放标准的音频插件规范，提供头文件和规范定义，用于开发符合 LV2 标准的音频插件。

## 功能概述
- LV2 插件规范核心定义
- 头文件和 API 定义
- 25 个扩展包：core, atom, midi, state, ui, worker 等
- lv2_validate 插件验证工具

## OHOS 适配
- 构建系统: meson 1.11.1
- 纯头文件库，无共享库生成
- 测试全部通过（5/5）

## 依赖
- 无外部依赖

## 功能验证
```bash
pkg-config --modversion lv2  # 输出: 1.18.11
```

## 参考
- 官网: https://lv2plug.in
- 源码: https://gitlab.com/lv2/lv2