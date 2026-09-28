# robtk

robtk（rob's LV2 UI tool kit）是一个用于构建 **LV2 插件 UI** 的源码工具箱：它用 cairo/pango
重新实现了一套 GTK 风格的组件与布局，便于把已有的 GTK+ 插件界面移植到 LV2。

## 功能概述

- 组件：label / separator / push button / check button / check-img button / radio button /
  spinner / combo-box（selector）/ drawing area / x-y plot / image / dial / scale /
  multi-state button
- 布局：hbox / vbox / table（含 expand、fill、homogeneous）
- 事件：鼠标移动、按键、滚轮、enter/leave、size-request/allocate 回调（API 贴近 GTK）
- 后端：`ui_gl.c`（OpenGL，含 LV2 UI / external-UI 包装、缩放、OSC/文件对话框等辅助）、
  `ui_gtk.c`（GTK+，上游已标注 deprecated）
- 附带：`jackwrap.c`（x42 JACK app 包装）、`sofd/`（文件选择）、`weakjack/`（弱链接 JACK）

工具箱以**源码**形式交付：下游项目设置 `RW=<robtk 目录>`、`#include "robtk.h"`，并把
`$(RW)ui_gl.c`（或 `ui_gtk.c`）与自己的 UI 源码（`PLUGIN_SOURCE`）一起编译成 UI `.so`。

## OHOS 适配

- HarmonyOS 没有 X11/GLX，也没有桌面 OpenGL：新增 `pugl/pugl_ohos.c`
  （EGL 1.4 + OpenGL ES 3 + `OHNativeWindow`，含输入桥接与帧回读），
  并把 `ui_gl.c` 的固定管线呈现换成 `gl/gles_present.h`（GLES blit + 片元 `.bgra` swizzle）。
- 无窗口时（`puglCreate(parent=0)`）自动使用 EGL pbuffer 离屏渲染，可在无显示器环境构建、
  驱动与校验 UI；`puglGrabFrame()` 可回读帧用于像素断言或宿主快照。
- 宿主接口：`descriptor->extension_data("http://gareus.org/oss/lv2/robtk#ohosUi")` 返回
  `RTKOhosUi{ abi_version, view(), grab_frame() }`；拿到 `PuglView*` 后用
  `puglSetNativeWindow()` 挂接 XComponent 的 `OHNativeWindow`，用
  `puglSendMotion/Mouse/Scroll/Special/Keyboard/EnterLeave()` 转发 ArkUI 输入事件。
- 下游 make 工程：`make RTK_OHOS=1`（robtk.mk 自动追加 `pugl/pugl_ohos.c`、`-DRTK_GLES`、
  `-lEGL -lGLESv3 -lnative_window`）。
- 已知限制：X11/GLX 后端在 HarmonyOS 上不可用；GTK2 后端未在 OHOS 验证（上游已 deprecated）；
  文件选择对话框由 ArkUI 侧实现（`puglOpenFileDialog()` 返回 -1，经 file-selected 回调回填）；
  视图创建后 EGL 上下文保持 current，宿主应在同一线程驱动 `puglProcessEvents()`。

## 依赖关系

- 编译依赖（本包 `requires`）：`cairo/1.18.4`、`pango/1.50.14.1.1`、`lv2/1.18.11-git`
  （glib 2.84.0.1 经 pango 传递）
- 系统库（OHOS）：`EGL`、`GLESv3`、`native_window`、`m`、`pthread`
- 运行依赖：由宿主应用（ArkUI/XComponent）提供窗口与事件循环

## 参考资料

- 上游仓库：https://github.com/x42/robtk
- 使用方示例：meters.lv2、sisco.lv2、tuna.lv2、mixtri.lv2、fil4.lv2、setBfree
- 适配笔记：[0.8.6/notes.md](0.8.6/notes.md)
