# openscenegraph 3.6.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-04
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# CMake配置（GLES3/EGL模式，无X11窗口系统）
cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_RPATH=/storage/Users/currentUser/usr/local/lib \
  -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
  -DOPENGL_PROFILE=GLES3 \
  -DOSG_GLES3_AVAILABLE=ON \
  -DOSG_GL1_AVAILABLE=OFF \
  -DOSG_GL2_AVAILABLE=OFF \
  -DOSG_GL3_AVAILABLE=OFF \
  -DOSG_GLES1_AVAILABLE=OFF \
  -DOSG_GLES2_AVAILABLE=OFF \
  -DOSG_GL_FIXED_FUNCTION_AVAILABLE=OFF \
  -DOSG_GL_DISPLAYLISTS_AVAILABLE=OFF \
  -DOSG_GL_MATRICES_AVAILABLE=OFF \
  -DOSG_GL_VERTEX_FUNCS_AVAILABLE=OFF \
  -DOSG_GL_VERTEX_ARRAY_FUNCS_AVAILABLE=OFF \
  -DOSG_WINDOWING_SYSTEM=None \
  -DOPENGL_INCLUDE_DIR=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include \
  -DOPENGL_opengl_LIBRARY=/system/lib64/libGLESv3.so \
  -DOPENGL_gl_LIBRARY=/system/lib64/libGLESv3.so \
  -DEGL_LIBRARY=/system/lib64/libEGL.so \
  -DEGL_INCLUDE_DIR=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include \
  ..

make -j2
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-openscenegraph-3.6.5
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HarmonyOS不被CMake识别为UNIX | CMAKE_SYSTEM_NAME=HarmonyOS不满足IF(UNIX) | 修改CMakeLists.txt添加HarmonyOS到UNIX检查 |
| 2 | sys/unistd.h文件不存在 | HarmonyOS使用顶层unistd.h | 替换sys/unistd.h为unistd.h |
| 3 | pthread_cancel等函数不存在 | musl libc不实现线程取消机制 | 用CHECK_FUNCTION_EXISTS检测后再添加HAVE_PTHREAD_*定义 |
| 4 | CMake版本兼容性问题 | CMakeLists.txt要求cmake_minimum_required(VERSION 2.6) | 添加-DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 5 | OpenGL/EGL找不到 | CMake默认FindOpenGL不支持EGL/GLES | 手动指定OPENGL_INCLUDE_DIR/EGL_LIBRARY等路径 |

## 源码修改

3个补丁文件：
- 0001-src-OpenThreads-CMakeLists.txt.patch: 添加HarmonyOS到UNIX-like平台检查
- 0002-src-OpenThreads-pthreads-CMakeLists.txt.patch: 用CHECK_FUNCTION_EXISTS替换无条件HAVE_PTHREAD_*定义，添加HarmonyOS到Linux匹配
- 0003-src-OpenThreads-pthreads-PThread.cpp.patch: 替换sys/unistd.h为unistd.h

## 依赖版本

- EGL/GLESv3: 系统库(/system/lib64/libEGL.so, libGLESv3.so)
- zlib: 1.3.1 (预编译)
- freetype: 2.14.3 (预编译)
- libjpeg: 预编译
- libpng: 1.6.44 (预编译)
- libtiff: 预编译
- libcurl: 8.19.0 (预编译)
- fontconfig: 预编译
- SDL2: 2.30.0 (预编译)

## 验证结果

```bash
# Staging验证：98个共享库, 6个二进制, 80个插件
ls $TEST_PREFIX/$DEFAULT_PREFIX/bin/  # osgversion, osgconv等
# make check: 无自动化测试(OpenSceneGraph需要图形显示)
```

## 交付物

| 文件 | 说明 |
|------|------|
| 0001-src-OpenThreads-CMakeLists.txt.patch | HarmonyOS UNIX检查补丁 |
| 0002-src-OpenThreads-pthreads-CMakeLists.txt.patch | pthread_cancel检测补丁 |
| 0003-src-OpenThreads-pthreads-PThread.cpp.patch | unistd.h替换补丁 |

## 注意事项

- 编译为GLES3模式（不使用桌面OpenGL），无X11窗口系统
- 二进制文件依赖EGL/GLESv3系统库运行时需要LD_LIBRARY_PATH包含/usr/local/lib
- OpenSceneGraph是3D图形库，完整功能测试需要图形显示服务器
---

**编译结束**: 2026-06-04 13:38
**最终状态**: built
