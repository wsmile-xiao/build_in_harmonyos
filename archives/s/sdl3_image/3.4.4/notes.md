# sdl3_image 3.4.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化: `ohc-run.py init-build sdl3_image 3.4.4 --url=...`
2. 编译SDL3依赖 (3.4.0): 从github git clone获取, cmake配置用CMAKE_SYSTEM_NAME=Linux
3. cmake配置SDL_image:
   ```
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_SYSTEM_NAME=Linux \
         -DSDL3_DIR=$DEFAULT_PREFIX/lib/cmake/SDL3 \
         -DSDLIMAGE_SAMPLES=OFF -DSDLIMAGE_TESTS=OFF \
         -DSDLIMAGE_STRICT=OFF \
         -DSDLIMAGE_AVIF=OFF -DSDLIMAGE_JXL=OFF \
         -DSDLIMAGE_WEBP=OFF -DSDLIMAGE_TIF=OFF \
         -DSDLIMAGE_PNG=OFF -DBUILD_SHARED_LIBS=OFF ..
   ```
4. 编译: `make -j2`
5. 安装: `make install DESTDIR=$TEST_PREFIX` (DESTDIR模式)
6. 打包: `ohc-run.py package sdl3_image 3.4.4`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SDL3 cmake无法识别OpenHarmony平台 | CMake SYSTEM_NAME为空，SDL_DetectCMakePlatform()不匹配OHOS | 设置CMAKE_SYSTEM_NAME=Linux |
| 2 | SDL3 cmake要求X11/Wayland | UNIX_SYS未被设置，SDL检测为Linux后强制要求显示服务器 | 设置SDL_UNIX_CONSOLE_BUILD=ON跳过检查 |
| 3 | SDL3共享库链接失败(pthread_setcanceltype) | musl libc不实现pthread cancellation功能 | 只编译静态库(SDL_SHARED=OFF) |
| 4 | SDL_image需要SDL3>=3.4.0 | SDL_image CMakeLists.txt中SDL_REQUIRED_VERSION=3.4.0 | 从源码编译SDL3 3.4.0 (git clone release-3.4.0) |
| 5 | cmd-pkgs无SDL3预编译包 | SDL3尚未发布到cmd-pkgs | 从源码编译SDL3 |
| 6 | SDL3 3.2.0版本不够 | 最初编译3.2.0但版本不满足SDL_image要求 | 重新编译3.4.0 |

## 源码修改

无源码修改。所有适配通过cmake命令行参数完成，无需生成补丁文件。

## 依赖版本

- SDL3: 3.4.0 (从源码编译，静态库)
- clang: 15.0.4

## 验证结果

```bash
PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig pkg-config --modversion sdl3-image
# 输出: 3.4.4
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sdl3_image-3.4.4-ohos-aarch64.tar.gz | 514KB | 预编译包(Release) |
| sdl3_image-3.4.4-ohos-aarch64-debug.tar.gz | 1.43MB | 预编译包(Debug) |

## 注意事项

- SDL3只编译了静态库(libSDL3.a)，未编译共享库(libSDL3.so)
- SDL_image也只编译了静态库(libSDL3_image.a)
- SDL3和SDL_image都使用了CMAKE_SYSTEM_NAME=Linux以绕过平台检测
- musl libc缺少pthread_setcanceltype函数，无法编译SDL3共享库
---

**编译结束**: 2026-05-25 22:51
**最终状态**: built
