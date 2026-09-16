# Coin（Coin3D core）

Coin 是 Coin3D 项目核心库：兼容 SGI Open Inventor 2.1 API 的高层 3D 可视化
工具包（场景图 + OpenGL 渲染），广泛用于 CAD/可视化/仿真软件（与 SIM 的
Coin 一脉相承，即原 "SIM Coin"）。

> **命名辨析**：本包是 `coin3d/coin`（3D 图形库，BSD-3-Clause）。
> 另有一个同名但完全无关的 **COIN-OR**（Common Optimization Interface for
> Operations Research，运筹优化套件，EPFL/IBM 系）——两者只是名字相同，
> 源码、社区、功能均无任何关系。本目录只收录 Coin3D。

## 功能概述

- Open Inventor 2.1 场景图 API（节点/字段/引擎/传感器/动作遍历）
- VRML97 支持（含 JavaScript 能力开关）、3DS 导入、IV/WRL 读写
- 渲染：OpenGL 场景遍历 + 离屏渲染（SoOffscreenRenderer）
- 大量节点：几何（SoCone/SoCube/SoIndexedFaceSet…）、属性、节点套件
  （NodeKit/Dragger/Manipulator）、传感器/引擎动画
- 自研 testsuite（CoinTests，不依赖 Boost）

## OHOS 适配

- **GL 接线**：OHOS PC 只有 OpenGL ES 3.2 + EGL（`/system/lib64/libGLESv3.so`、
  `libEGL.so`），无桌面 libGL。Coin 静态引用定点管线符号（`glMatrixMode`/
  `glBegin`/`glColor3f` 等），因此必须链接 [gl4es](../g/gl4es/1.1.6)（桌面
  GL 1.5/2.1 → GLES2 翻译层）提供的 `libGL.so`；`COIN_BUILD_GLX=OFF`（无 X11），
  EGL 走 SDK sysroot 的 libEGL.so。
- **运行时环境**：消费方需设置 `LIBGL_GLES=/system/lib64/libGLESv3.so`、
  `LIBGL_EGL=/system/lib64/libEGL.so`（conan 的 conanrun 环境已通过
  `runenv_info` 自动带上）；否则 `SoDB::init()` 内 gl4es 初始化会崩溃。
- **已知问题**：`SoDB::finish()` 在 gl4es 栈下析构 GL glue 时 SIGSEGV
  （初始化/解析/渲染均正常，仅显式收尾崩溃）；进程退出不调用即可干净结束。
- **签名**：产物 .so 经 `binary-sign-tool` 自签（OHOS PC XPM 要求，未签名
  动态库加载会被拒）。
- **CMake 消费**：`find_package(Coin)` → 目标 `Coin::Coin`；pkg-config 名
  `Coin`。
- zlib/bzip2/freetype 等为运行时 dlopen（缺库不阻塞构建）；vendored expat
  默认内置，无外部编译期 conan 依赖（除 gl4es）。

## 依赖关系

- 编译期（conan）：`gl4es/1.1.6`
- 运行时（系统库）：`/system/lib64/libGLESv3.so`、`/system/lib64/libEGL.so`、
  `libc++_shared.so`；可选 dlopen：zlib/bzip2/freetype/fontconfig/simge 等

## 参考资料

- 官网/文档：<https://coin3d.github.io>
- 源码仓库：<https://github.com/coin3d/coin>
- 本地版本笔记：[4.0.10/notes.md](4.0.10/notes.md)
