# SDL2 2.30.0 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-07-14
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **源码下载**: 从 GitHub releases 下载 SDL2-2.30.0.tar.gz
2. **解压**: tar xf 解压到构建目录
3. **CMake 配置**: `cmake -S . -B build -DCMAKE_SYSTEM_NAME=Linux -DSDL_X11=OFF -DSDL_WAYLAND=OFF -DSDL_KMSDRM=OFF -DSDL_OPENGL=OFF -DSDL_OPENGLES=OFF -DSDL_VULKAN=OFF -DSDL_HIDAPI=OFF -DSDL_DUMMYVIDEO=ON -DSDL_OFFSCREEN=ON -DSDL_TESTS=OFF -DSDL_TEST=OFF`
4. **make**: `cmake --build build`
5. **install**: `cmake --install build --prefix <prefix>`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识条目 |
|---|------|------|----------|----------|
| 1 | SDL2 CMake 不识别 OHOS 平台 | sdlplatform.cmake 缺少 OHOS 枚举 | CMake 配置中设置 CMAKE_SYSTEM_NAME=Linux | E092 |
| 2 | pthread_setcanceltype 链接错误 | musl/OHOS 不实现 POSIX 线程取消 API | 修改 SDL_systhread.c 添加 #ifndef __OHOS__ 守卫 | E085 |
| 3 | make jobserver FIFO 权限错误 | HMDFS 不支持 mkfifo | 使用 cmake 构建（cmake 内部管理并行度，不依赖 make jobserver） | E076 |
| 4 | CI: conandata.yml 补丁格式错误 | Conan 2.x 要求 patches 按版本号索引 | 改为 dict-by-version 格式 | - |
| 5 | CI: librt 在 OHOS/musl 上不存在 | musl 将实时扩展函数集成在 libc 中 | OHOS 移除 rt，仅 Linux 保留 | - |
| 6 | AI 审查: 后端禁用未用 OHOS 守卫 | 所有平台统一禁用 X11/Wayland 等后端 | 包裹在 if self.settings.os == "OHOS" 内 | - |

## 源码修改

### 1. src/thread/pthread/SDL_systhread.c（第 174-186 行）
```diff
 #ifdef PTHREAD_CANCEL_ASYNCHRONOUS
     /* Allow ourselves to be asynchronously cancelled */
+#ifndef __OHOS__
     {
         int oldstate;
         pthread_setcanceltype(PTHREAD_CANCEL_ASYNCHRONOUS, &oldstate);
     }
+#endif /* __OHOS__ */
 #endif
```

## 依赖版本

本次编译未依赖外部库（SDL2 自包含）。

## 验证结果

```bash
# 验证 sdl2-config（如果安装了 sdl2-config）
$ sdl2-config --version
2.30.0

# 验证库文件存在
$ ls lib/libSDL2*
libSDL2.a
libSDL2main.a
```

## 交付物

| 文件 | 说明 |
|------|------|
| libSDL2.a | SDL2 静态库 |
| libSDL2main.a | SDL2 主入口静态库 |
| include/SDL2/ | SDL2 头文件集合 |

## 注意事项

1. **CMake 构建**: SDL2 同时支持 autotools 和 CMake，推荐使用 CMake（更稳定，避免 jobserver 问题）
2. **视频驱动**: OHOS 上无 X11/Wayland/KMSDRM，需使用 dummy 和 offscreen 视频驱动
3. **音频驱动**: OHOS 上无 ALSA/PulseAudio，需使用 dummy 音频驱动
4. **OpenGL/Vulkan**: OHOS 上暂不支持，已禁用
5. **HIDAPI**: OHOS 上无 libusb，已禁用
6. **无测试套件**: SDL2 不提供 `make check`，测试需手动编译测试程序
7. **线程取消 API**: musl/OHOS 不支持 POSIX 线程取消功能（pthread_cancel, pthread_setcanceltype），已通过条件编译跳过
8. **难度标签**: low — 基本无外部依赖，仅需平台适配补丁

---

**编译结束**: 2026-07-14
**最终状态**: built