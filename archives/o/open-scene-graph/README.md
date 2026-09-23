# open-scene-graph

OpenSceneGraph — 开源高性能 3D 图形工具包，面向实时可视化与仿真。

- 上游：https://github.com/openscenegraph/OpenSceneGraph
- 适配版本：3.6.5（tag OpenSceneGraph-3.6.5）
- 构建：CMake，GLES3 profile（无桌面 GL）、OSG_WINDOWING_SYSTEM=None（无 X11/Wayland）、
  依赖零三方 conan 包（GLES3/EGL 头与桩库来自 OHOS SDK sysroot）
- 平台：OpenHarmony PC (aarch64, OHOS)
