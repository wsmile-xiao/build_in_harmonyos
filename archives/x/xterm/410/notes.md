# xterm 410 — X11 终端模拟器

## 编译摘要

xterm-410 在 HarmonyOS (aarch64) 上成功编译。

| 项目 | 状态 |
|------|------|
| 编译系统 | autotools (configure + make) |
| 编译器 | clang 15 |
| 库依赖 | libXt + libXmu（源码构建），libXaw(stub)，libX11，libXext，libSM，libICE，libXau（预编译） |
| 产物 | xterm (854KB)，resize (35KB)，uxterm，koi8rxterm |
| linking | 动态链接（预编译 X11 库仅有 .so） |

## 关键适配

1. **config.guess/sub**: `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos` 跳过平台检测
2. **libXaw stub**: xterm 需要链接 libXaw（Athena Widgets），但功能被 `--disable-toolbar` 禁用，使用最小 stub 替代
3. **curses.h stub**: 鸿蒙未提供 curses/termcap 头文件，创建最小 stub 提供 tigetstr/tgetstr 等声明
4. **utmpx 兼容**: 鸿蒙使用 `ut_tv.tv_sec` 替代 `ut_time`，通过 ohos_fix.h 宏映射
5. **ttyslot 缺失**: 鸿蒙 C 库未提供 `ttyslot()`，以 stub 替代
6. **Conan profile**: `tools.build:cxx_executable` 在 Conan 2.12 中改为 `tools.build:compiler_executables` 字典格式

## 已知限制

- 需要 X server 运行，当前无头环境仅验证二进制存在
- 预编译 X11 库提供 .so，不支持全静态链接
- libxcb.so.1 缺失（仅有 .a），libX11.so.6 运行时会因缺少 libxcb.so 而无法加载
- 菜单/工具栏功能通过 libXaw stub 占用链接符号（实际禁用）
---

**编译结束**: 2026-06-26 09:59
**最终状态**: built
