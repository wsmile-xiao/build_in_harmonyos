# libwpe

Web Platform Engine 基础库。

## 描述

libwpe 是 WPEWebKit 的平台抽象层，提供：
- 图形渲染后端接口
- 输入事件处理
- 与不同窗口系统集成

## 版本

- 1.16.0 (2026-06-15) - built

## 依赖

- 无必需依赖（EGL/xkbcommon 可选）

## 编译说明

- 构建系统：meson
- 关键修复：移除 EGL 必需检查，禁用 xkbcommon
- 平台：aarch64-unknown-linux-ohos
- 功能限制：禁用了 EGL 和键盘输入功能

## 许可证

BSD-2-Clause