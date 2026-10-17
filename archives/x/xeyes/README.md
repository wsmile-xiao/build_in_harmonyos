# xeyes

xeyes 是 X Window System 的经典演示程序：绘制一对跟随鼠标移动的眼睛，
使用 X SHAPE 扩展实现异形窗口。本仓库提供其在 HarmonyOS PC (aarch64)
上的 Conan 配方。

## 官网

https://gitlab.freedesktop.org/xorg/app/xeyes

## 许可证

MIT

## 特性

- 眼球跟随鼠标移动（X SHAPE 扩展 + Xt 工具包）
- 多眼球配置（-biblicallyAccurate 等选项）
- 可选 XRender 抗锯齿渲染（检测到 libXrender 时自动启用）
- `-version` / `-help` 无需 X server 即可运行（供无头验证）

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 | 补丁数 |
|------|------|----------|----------|--------|
| 1.3.1 | built | 2026-08-19 | autotools | 0 |

## 已知平台问题

- 完整 GUI 运行需要 X server；无头环境（CI/真机无 X）下仅能验证
  -version/-help 路径（与 xterm 410、xclip 0.13.1 同款处理）
- 依赖编译环境预编译 X11 开发栈（libXi/libX11/libXt/libXext/libXmu/xorgproto）
