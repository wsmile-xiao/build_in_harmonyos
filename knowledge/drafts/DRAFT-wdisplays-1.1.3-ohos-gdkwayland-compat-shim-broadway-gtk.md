# DRAFT-wdisplays-1.1.3-ohos-gdkwayland-compat-shim-broadway-gtk：OHOS GTK3 仅 broadway 后端——依赖 `<gdk/gdkwayland.h>` 的 Wayland GTK 客户端需自建访问器兼容层

> Contributor: OpenDesk | Status: Draft | Updated: 2026-09-24
> Source: wdisplays 1.1.3 适配 HarmonyOS PC（分支 `feat/wdisplays-1.1.3`）
> 对应：`knowledge/drafts/DRAFT-wdisplays-1.1.3-ohos-gdkwayland-compat-shim-broadway-gtk.kv`

## 现象

Wayland 专有的 GTK3 客户端在 OHOS PC 上编译，先卡头文件、再卡链接、最后卡 meson 断言：

```console
../src/main.c:5:10: fatal error: 'gdk/gdkwayland.h' file not found
ld.lld: error: undefined symbol: GDK_IS_WAYLAND_DISPLAY
>>> referenced by main.c
```

若把上游的硬断言留着，`meson configure` 阶段就直接终止：

```
src/meson.build:9: ERROR: Assert failed: Wayland GDK backend not present
```

先确认不是"缺依赖"：

```console
$ pkg-config --variable=targets gdk-3.0
broadway                       # ← OHOS 制品仓 gtk/3.24.43 只有 broadway 后端
$ ls $GTK_PKG/include/gtk-3.0/gdk/gdkwayland.h
ls: ... No such file or directory
```

## 根因

OHOS 没有 X11 / Wayland 原生显示面，GTK3 以 **broadway（HTML5）** 后端构建：
`gdk-3.0.pc` 的 `targets=broadway`，既不安装 `libgdk` 的 Wayland 后端，也不安装
`<gdk/gdkwayland.h>`。而这类工具（显示器布局、layer-shell 覆盖层、screencopy
截屏、wlr 系协议客户端）必须通过 GDK 的 Wayland 私有访问器拿到
`wl_display` / `wl_output` / `wl_surface`：

| 上游用法 | 作用 |
|---|---|
| `gdk_wayland_display_get_wl_display(display)` | 取 GTK 会话背后的 `wl_display*` |
| `gdk_wayland_monitor_get_wl_output(monitor)` | 取 `GdkMonitor` 对应的 `wl_output*` |
| `gdk_wayland_window_get_wl_surface(window)` | 取窗口背后的 `wl_surface*` |
| `GDK_IS_WAYLAND_DISPLAY(display)` | 会话是否 Wayland（非 Wayland 直接拒绝启动） |

关键点：`wayland-client` 在 OHOS **是可用的**（制品仓 `wayland/1.22.0` 提供
`wayland-client.pc` 与 `wayland-scanner`），缺的不是 Wayland 客户端库，而是
**GDK 与 Wayland 之间的连接面**。

## 方案（推荐：wayland-client 支撑的 gdkwayland 兼容层）

新增一个极小的兼容层（补丁内新增 `.h/.c`），并由补丁把上游源码的
`#include <gdk/gdkwayland.h>` 换成它：

```c
/* gdkwayland-compat.h（节选） */
struct wl_display *gdk_wayland_display_get_wl_display(GdkDisplay *display);
struct wl_output  *gdk_wayland_monitor_get_wl_output(GdkMonitor *monitor);
struct wl_surface *gdk_wayland_window_get_wl_surface(GdkWindow *window);
void gdk_wayland_window_set_use_custom_surface(GdkWindow *window);

/* 以“本进程是否建立了 Wayland 连接”语义化 GDK 的会话判定宏 */
#define GDK_IS_WAYLAND_DISPLAY(display) \
  (gdk_wayland_display_get_wl_display(GDK_DISPLAY(display)) != NULL)
```

```c
/* gdkwayland-compat.c（节选） */
struct wl_display *gdk_wayland_display_get_wl_display(GdkDisplay *display) {
  if (wl_display_singleton == NULL) {
    wl_display_singleton = wl_display_connect(NULL);   /* 真连接，不是空壳 */
    if (wl_display_singleton != NULL) {
      struct wl_registry *r = wl_display_get_registry(wl_display_singleton);
      wl_registry_add_listener(r, &registry_listener, NULL);
      wl_display_roundtrip(wl_display_singleton);
    }
  }
  return wl_display_singleton;
}
```

配套三点：

1. **meson 断言放宽**（上游 `src/meson.build`）：
   `assert(targets.contains('wayland'))` → `assert(targets.contains('wayland')
   or targets.contains('broadway'))`。
2. **调用点 NULL 守卫**：`wl_surface` 在 broadway 窗口背后确实不存在，
   `resize()/window_map()` 里 `if (surface != NULL) ...`，`activate()` 里
   `wl_display == NULL` 时给出明确致命错误而不是段错误。
3. **补丁内不得出现平台宏**（`__OHOS__` 等，见 R8/PF5）：平台差异由运行期探测
   表达，补丁对上游语义是"补上缺失的访问器 + 放宽后端要求"。

验证证据（wdisplays 1.1.3 实测）：

```console
$ conan create archives/w/wdisplays/1.1.3 --version=1.1.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
[32/32] Linking target src/wdisplays
wdisplays/1.1.3: Package 'fdeb1e25...' created
  [PASS] OHOS gdkwayland compat layer symbol present (patch 0001 linked)
  [PASS] binary runs on device: 'wdisplays --help' exit 0 with usage output
[test] RESULT: pass=9 fail=0 skip=0 (total=9)
```

## 回退方案

若该工具的 Wayland 专有功能在 OHOS 上整体不可用、且上游支持裁剪，可改为
**构建开关裁掉相关源文件**（保留核心可用部分），并在 `notes.md`/PR 说明标注
"某功能在 OHOS 不可用"。侵入面更大，但比自建兼容层语义更直白。

## 禁止做法

- ❌ 让 `GDK_IS_WAYLAND_DISPLAY` 恒真，或让访问器返回假值/空壳：
  程序会在无 compositor 的系统上继续执行并以段错误或协议错误崩溃——
  R40 明令禁止的空壳 stub，且误导后续适配者。
- ❌ 为适配消费方去重新编译/改配置 GTK 的后端（`-Dwayland_backend=true`）：
  违反 R36（依赖先发布再构建下游），且 OHOS 无原生 Wayland 显示面，
  broadway 是本平台既定后端。

## 已知边界

- 本方案让这类工具在 OHOS 上**可编译、可链接、可加载、可启动**；完整交互功能
  仍需具备相应协议（如 `wlr-output-management-unstable-v1`）的 Wayland 会话。
  这一点必须在 notes.md 与 PR 里如实声明，不得以"编译通过"冒充"适配完成"。
- 关联既有条目：E527（GTK3 broadway 后端与构建工具包装）、E463（broadway +
  已签名私有工具副本 + 无显示消费方探针）；本条是其"消费方需要 GDK Wayland 面"
  的下游延伸，错误签名与处置对象均不同。
