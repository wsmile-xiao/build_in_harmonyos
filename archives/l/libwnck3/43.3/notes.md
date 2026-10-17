# libwnck3 43.3 适配笔记

## 编译环境

- 构建系统：Meson 1.10.1
- 编译日期：2026-09-09
- 目标：HarmonyOS 6.0 / arm64-v8a
- 编译器：OpenHarmony Clang 15.0.4
- 状态：built

## 上游测试清点

上游 `libwnck/meson.build` 定义 7 个交互测试程序：`test-wnck`、`test-tasklist`、`test-selector`、`test-pager`、`test-urgent`、`test-shutdown`、`test-icon-cache`。上游没有调用 Meson `test()` 注册自动测试，因此 `meson test --list` 的注册数为 0；本次把 7 个程序逐项作为集成测试清点和运行。

## 编译方案

```bash
conan create archives/l/libwnck3/43.3 \
  -pr:h ohos-aarch64 -pr:b ohos-aarch64 \
  --build=libwnck3/43.3
```

配置关闭未发布且可选的 startup-notification、仅构建期需要的 introspection/gtk-doc 和非库交付工具。核心 `libwnck-3.so.0.3.0`、公共头文件、翻译资源和 pkg-config 元数据均正常安装。

## 适配实现

仓库中的 GTK 3.24.43 采用 Broadway 后端，不包含 `gdk/gdkx.h`；Cairo 1.18.4 也未构建 Cairo-Xlib。补丁增加独立 X11 胶水层：

- GDK-X11 显示、Atom、错误陷阱、屏幕能力和窗口 XID 调用映射到真实 libX11。
- X11 Pixmap 通过 `XGetImage` 转为 Cairo image surface，保留图标缓存路径。
- GTK 的窗口控件仍由 Broadway 渲染，libwnck 的窗口枚举和 EWMH 数据面连接真实 X server。
- GLib 主循环按 16 ms 周期分发 X11 事件，窗口创建、属性变更、配置及销毁可持续更新 libwnck 状态。
- 兼容源由默认关闭的 `x11_compat` Meson 选项纳入 libwnck 目标；Linux 默认构建不启用该路径，也不使用空实现或固定返回值替代窗口功能。
- Meson 的 GLib 构建工具显式指向 Conan GLib 包：两个生成脚本由构建机 Python 执行，`glib-compile-resources` 在 ARM 主机原生执行或在 x86_64 主机经 QEMU 执行，并注入 Conan 依赖库路径；无 QEMU 时的系统工具兜底会先隔离目标 `LD_LIBRARY_PATH`，避免宿主 `libffi.so.8` 被错误遮蔽。

## 依赖版本

- glib/2.84.0.1
- gtk/3.24.43
- cairo/1.18.4
- libx11/6.4.0
- libxres/1.2.1
- libxi/6.1.0
- Meson 1.10.1（构建机工具）

## 验证结果

- 官方源码 SHA-256：通过。
- 宿主兼容层全目标编译：通过。
- Conan OHOS/arm64 交叉构建及消费者 API/ABI 测试：通过。
- 赛事 `ohos-aarch64` profile 与本地隔离 profile：均通过。
- QEMU OHOS/arm64 运行：通过。
- Conan `glib-compile-resources` 工具及运行库隔离回归：通过。
- 上游 7 个交互测试程序：7/7 通过。
- 项目测试与静态门禁：全部通过。

详细命令和输出摘要见 `reports/test-report.md`。

## 交付物

- `lib/libwnck-3.so.0.3.0` 及 SONAME 链接
- `include/libwnck-3.0/libwnck/*.h`
- `lib/pkgconfig/libwnck-3.0.pc`
- `share/locale/*/LC_MESSAGES/libwnck-3.0.mo`

COMPLETED — libwnck3 43.3 适配完成，状态: built
---

**编译结束**: 2026-09-09 09:47
**最终状态**: built
