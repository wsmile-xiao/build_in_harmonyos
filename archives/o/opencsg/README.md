# OpenCSG

OpenCSG 是一个基于图像的 CSG（Constructive Solid Geometry，构造实体几何）渲染库：它用 OpenGL 的深度/模板缓冲组合简单实体（union / intersection / subtraction），而不显式计算 CSG 边界的几何表示。常用于 CAD / 建模类软件（如 OpenSCAD）的实时布尔显示。

## 功能概述

- 图像式（z-buffer）CSG 渲染，不生成显式几何边界
- 两种算法族：Goldfeather（支持凸/凹实体、相机在模型内）与 SCS（仅凸实体、更快）
- 多层次深度复杂度策略：NoDepthComplexitySampling / OcclusionQuery / DepthComplexitySampling
- 离屏渲染走帧缓冲对象（ARB / EXT FBO）
- 可选顶点着色器接口；支持多 OpenGL context 资源隔离（setContext）
- 自带私有 glad（符号收入 `OpenCSG` 命名空间），运行时 `dlopen` 解析 GL 入口点

## OHOS 适配

- 构建系统为 CMake，纯 C++17，无第三方编译期依赖。
- **GL 库不是链接依赖**：OpenCSG 只在 `render()` 内通过自带 glad 运行时 `dlopen` 解析 GL 入口点，`libopencsg.so` 实测 `DT_NEEDED` 只有 `libc++_shared.so` 与 `libc.so`。
- 需要两处平台适配（见 `1.8.2/patches/`）：
  1. `0001-glad-ohos-opengl-loader.patch`：让 glad 认识 HarmonyOS 的桌面 GL 入口库 `libGLv4.so`，并从 `libEGL.so` 取 `eglGetProcAddress` 作为过程地址助手。
  2. `0002-src-CMakeLists-optional-opengl-lookup.patch`：`src/CMakeLists.txt` 原本 `find_package(OpenGL REQUIRED)`，但目标并不链接 GL；HarmonyOS 无 GL 开发包，改为可选查找。
- 已知限制：`render()` 的真实渲染路径需要真实 OpenGL context，只能在真机上验证（见版本 notes 的设备 shadow CI 计划）。
- 与 Linux 的差异：桌面 Linux 通常有 `libGL.so.1` 可供 glad 直接 dlopen；HarmonyOS 提供的是 `libGLv4.so` + `libEGL.so` / `libGLESv3.so`。

## 依赖关系

- 编译依赖：CMake ≥ 3.11、支持 C++17 的 clang。无需 Conan 依赖。
- 运行依赖：设备侧 `libGLv4.so`（桌面 GL 入口）与 `libEGL.so`；C++ 运行时 `libc++_shared.so`。
- 测试/示例依赖：`example/` 需要 GLUT，适配中关闭（`BUILD_EXAMPLE=OFF`）。

## 参考资料

- 官网: http://www.opencsg.org
- 源码仓库: https://github.com/floriankirsch/OpenCSG
