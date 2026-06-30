# OpenSceneGraph

OpenSceneGraph 是一个高性能的 3D 图形工具包，用于实时可视化和仿真应用。

## 描述
OpenSceneGraph (OSG) 是一个开源的高性能 3D 图形工具包，基于 OpenGL/GLES3 提供。它广泛应用于视觉仿真、虚拟现实、游戏、科学可视化和建模等领域。

## 已编译版本
- 3.6.5 (2026-06-04)

## 依赖
- OpenGL ES 3.0 / EGL
- zlib
- freetype
- libjpeg
- libpng
- libtiff
- fontconfig
- curl

## 特性
- 98 个共享库（.so）
- 80 个 osg 插件
- 6 个二进制工具（osgviewer, osgconv, osgversion 等）
- OpenGL ES 3.0 支持（无 X11 窗口系统）
- OpenThreads 多线程库

## 使用方法
```bash
# 查看版本
osgversion

# 转换3D文件格式
osgconv input.osg output.ive

# 查看3D场景
osgviewer model.osg
```

## 注意事项
- 使用 GLES3/EGL 模式编译（无 X11 窗口系统支持）
- 需要系统 libEGL.so 和 libGLESv3.so
- HarmonyOS 平台需要 CMake 策略版本最低设置为 3.5