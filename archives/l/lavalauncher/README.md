# lavalauncher

A simple and highly configurable launcher for Wayland（Wayland 启动器，lavabar）。

- 主页: https://git.sr.ht/~leon_plickat/lavalauncher
- 许可证: GPL-3.0-or-later
- 构建系统: meson (C)

## 版本

| 版本 | 状态 | 构建日期 |
|------|------|----------|
| 2.1.1 | published | 2026-09-24 |

## 依赖

wayland/1.22.0 · wayland-protocols/1.36 · cairo/1.18.4 · libxkbcommon/1.6.0 · librsvg/2.62.3

## 适配要点

- wayland-scanner 从 wayland 源码静态编译替代（OHOS 沙箱禁止动态加载共享库工具）
- clang 警告白名单补丁（noop 跨签名回调）
- 无测试套件，--version 冒烟测试验证

## 使用

```bash
lavalauncher --help
```

详细配方见 `2.1.1/`。
