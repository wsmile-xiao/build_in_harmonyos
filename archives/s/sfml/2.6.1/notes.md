# sfml 2.6.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-30
- 编译器: clang/clang++
- 状态: partial（仅编译 System 和 Network 模块）

## 编译步骤

1. 下载源码（使用 GitHub tarball URL）：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build sfml 2.6.1 --url=https://github.com/SFML/SFML/archive/refs/tags/2.6.1.tar.gz
   ```

2. 配置 CMake（只编译 System 和 Network 模块）：
   ```bash
   cd $BUILD_SRC_DIR/build
   cmake .. \
       -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
       -DCMAKE_BUILD_TYPE=Release \
       -DBUILD_SHARED_LIBS=ON \
       -DSFML_BUILD_EXAMPLES=OFF \
       -DSFML_BUILD_TEST_SUITE=OFF \
       -DSFML_BUILD_AUDIO=OFF \
       -DSFML_BUILD_WINDOW=OFF \
       -DSFML_BUILD_GRAPHICS=OFF
   ```

3. 编译：
   ```bash
   make -j1
   ```

4. 安装到 DESTDIR：
   ```bash
   make install DESTDIR=$TEST_PREFIX
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不识别 HarmonyOS | cmake/Config.cmake 只支持 Windows/Linux/FreeBSD/Darwin/Android | 修改 cmake/Config.cmake，添加 HarmonyOS 支持 |
| 2 | OpenGL 找不到 | HarmonyOS 使用 OpenGL ES 而不是 OpenGL | 修改 src/SFML/Window/CMakeLists.txt，添加 OpenGL ES 支持 |
| 3 | UDev 缺失 | HarmonyOS 没有 UDev | 修改 src/SFML/Window/CMakeLists.txt，跳过 UDev |
| 4 | OpenAL 缺失 | 没有预编译的 OpenAL | 禁用 Audio 模块 (-DSFML_BUILD_AUDIO=OFF) |
| 5 | X11 缺失 | HarmonyOS 没有 X11 | 禁用 Window 和 Graphics 模块 |
| 6 | pthread_cancel 不支持 | HarmonyOS pthread 不支持线程取消 | 修改 src/SFML/System/Unix/ThreadImpl.cpp，使用 pthread_detach |
| 7 | SIGUSR1 不存在 | HarmonyOS 没有 SIGUSR1 | 修改 ThreadImpl.cpp，使用 pthread_detach |

## 源码修改

1. **cmake/Config.cmake** - 添加 HarmonyOS 支持：
   - 修改第 19 行，将 HarmonyOS 视为类 Linux 系统
   - 添加 OPENGL_ES = 1 设置

2. **src/SFML/Window/CMakeLists.txt** - 添加 OpenGL ES 和跳过 UDev：
   - 添加 OpenGL ES (GLES) 和 EGL 库配置
   - 跳过 UDev 查找

3. **src/SFML/System/Unix/ThreadImpl.cpp** - 修复线程取消问题：
   - 使用 pthread_detach 代替 pthread_cancel

## 依赖版本

- HarmonyOS SDK: 26.0.0.18
- clang: 15.0.4
- cmake: 4.1.2

## 模块状态

| 模块 | 状态 | 说明 |
|------|------|------|
| System | ✅ 已编译 | 基础系统模块 |
| Network | ✅ 已编译 | 网络模块 |
| Window | ❌ 禁用 | 需要 X11 或 DRM 支持 |
| Graphics | ❌ 禁用 | 依赖 Window 模块 |
| Audio | ❌ 禁用 | 需要 OpenAL |

## 验证结果

```bash
ls -la $TEST_PREFIX/$DEFAULT_PREFIX/lib/
# libsfml-system.so
# libsfml-network.so
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libsfml-system.so | ~88KB | 系统模块 |
| libsfml-network.so | ~170KB | 网络模块 |

## 注意事项

1. SFML 在 HarmonyOS 上只能使用 System 和 Network 模块
2. Window/Graphics/Audio 模块需要额外的依赖：
   - Window: X11 或 DRM + UDev
   - Graphics: 依赖 Window + OpenGL
   - Audio: OpenAL
3. 完整的 SFML 支持需要进一步适配工作：
   - 实现 HarmonyOS 窗口系统后端
   - 编译 OpenAL 或使用替代音频库
   - 实现 OpenGL ES 线程支持
---

**编译结束**: 2026-05-30 00:17
**最终状态**: built
