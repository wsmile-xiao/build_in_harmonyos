# renderdoc 1.44 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-04
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 目标平台: HarmonyOS aarch64 (HongMeng Kernel 1.12.0, musl libc)
- 状态: built (with significant features disabled)

## 编译步骤

1. **初始化构建**:
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build renderdoc 1.44 \
     --url=https://github.com/baldurk/renderdoc/archive/refs/tags/v1.44.tar.gz
   ```
   (源码需手动下载，因 SSL 证书问题 ohc-run.py 下载失败)

2. **安装源码**:
   手动下载源码并解压到 `/storage/Users/currentUser/tmp/builds/renderdoc-1.44.orig/`，
   然后复制为 `.work` 目录。

3. **应用补丁**:
   - `0001-linux-hook-musl-rtld-deepbind.patch`: 为 musl libc 添加 RTLD_DEEPBIND 兼容
   - `0002-plthook-musl-libc-compat.patch`: 为 plthook_elf.c 添加 musl libc 兼容性处理

4. **CMake 配置**:
   ```bash
   cmake -S . -B build -G Ninja \
     -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
     -DCMAKE_SYSTEM_NAME=Linux \
     -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
     -DCMAKE_C_COMPILER=clang \
     -DCMAKE_CXX_COMPILER=clang++ \
     -DCMAKE_C_FLAGS="-fPIC -O2" \
     -DCMAKE_CXX_FLAGS="-fPIC -O2" \
     -DENABLE_GL=OFF \
     -DENABLE_GLES=OFF \
     -DENABLE_EGL=OFF \
     -DENABLE_VULKAN=OFF \
     -DENABLE_METAL=OFF \
     -DENABLE_XLIB=OFF \
     -DENABLE_XCB=OFF \
     -DENABLE_QRENDERDOC=OFF \
     -DENABLE_PYRENDERDOC=OFF \
     -DENABLE_RENDERDOCCMD=ON \
     -DHOST_NATIVE_CPP_COMPILER=clang++
   ```

5. **构建**:
   ```bash
   cd build && ninja -j4
   ```
   构建成功，产出:
   - `lib/librenderdoc.so` (4.9MB, ELF 64-bit LSB arm64)
   - `bin/renderdoccmd` (345KB, ELF 64-bit LSB arm64, musl libc)

6. **安装**:
   ```bash
   ninja install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书下载失败 | ohc-run.py 内部 urllib SSL 验证失败 | 手动用 curl 下载源码到 downloads 目录，然后用 `--no-download` 选项 |
| 2 | plthook_elf.c 编译失败: `RTLD_DL_LINKMAP`, `dladdr1`, `_r_debug` 未声明 | musl libc 不提供 glibc 扩展的 dlinfo/dladdr1/_r_debug | 补丁 0002: 添加 PLTHOOK_MUSL_LIBC 检测，为 glibc 特定功能提供 musl 回退 |
| 3 | linux_hook.cpp 编译失败: `RTLD_DEEPBIND` 未声明 | musl libc 不定义 RTLD_DEEPBIND 宏 | 补丁 0001: 添加 `#ifndef RTLD_DEEPBIND` 定义为 0 |
| 4 | `c++` 命令未找到 | renderdoc cmake 用 HOST_NATIVE_CPP_COMPILER=c++ 编译辅助工具 | 设置 `-DHOST_NATIVE_CPP_COMPILER=clang++` |
| 5 | cmake 将系统识别为 HarmonyOS（非 UNIX） | cmake 不识别 HarmonyOS 为 UNIX 平台 | 设置 `-DCMAKE_SYSTEM_NAME=Linux` |

## 禁用的功能

| 功能 | CMake 选项 | 原因 |
|------|-----------|------|
| OpenGL | ENABLE_GL=OFF | 无 GL/GLX 头文件和库 |
| OpenGL ES | ENABLE_GLES=OFF | 无 EGL 头文件和库 |
| EGL | ENABLE_EGL=OFF | 无 EGL 头文件和 pkg-config |
| Vulkan | ENABLE_VULKAN=OFF | 无 Vulkan 头文件和运行时 |
| Metal | ENABLE_METAL=OFF | 仅 Apple 平台 |
| XLib | ENABLE_XLIB=OFF | 无 x11 pkg-config |
| XCB | ENABLE_XCB=OFF | 无 xcb pkg-config |
| Wayland | ENABLE_UNSUPPORTED_EXPERIMENTAL_POSSIBLY_BROKEN_WAYLAND=OFF (默认) | 缺少 wayland-client pkg-config 完整支持 |
| qrenderdoc (Qt UI) | ENABLE_QRENDERDOC=OFF | 无 Qt5Core/Qt5Widgets/Qt5Gui/Qt5Svg |
| pyrenderdoc | ENABLE_PYRENDERDOC=OFF | 无 python3-config/python3-embed pkg-config |
| renderdoccmd | ENABLE_RENDERDOCCMD=ON | 可用，仅依赖核心库 |

**重要说明**: renderdoc 是一个图形调试工具，其核心功能依赖于 GL/GLES/Vulkan 图形 API。
在 HarmonyOS 上，由于缺乏这些图形 API 的支持，编译出的库仅包含核心框架代码，
无法进行实际的图形捕获和调试功能。但 renderdoccmd 命令行工具仍可使用基础功能。

## 依赖缺失情况

| 依赖 | 预编译包可用? | 说明 |
|------|-------------|------|
| libx11-dev | ❌ 不可用 | X11 头文件存在但 pkg-config 缺失 |
| libxcb-dev | ❌ 不可用 | 无 xcb 头文件和 pkg-config |
| pcre-dev | ❌ 不可用 | 有 libpcre2-posix 但无 pcre |
| python3-dev | ❌ 不可用 | python3 存在但无 python3-config 和 embed pkg-config |
| qt5-qtbase-dev | ❌ 不可用 | 无 Qt5Core/Qt5Widgets/Qt5Gui |
| qt5-qtsvg-dev | ❌ 不可用 | 无 Qt5Svg |
| qt5-qtx11extras-dev | ❌ 不可用 | 无 Qt5X11Extras |
| wayland-dev | ⚠️ 部分可用 | 有 wayland-server/cursor/egl pkg-config |
| xcb-util-keysyms-dev | ❌ 不可用 | 无 xcb-keysyms pkg-config |

## 源码修改

### 补丁 0001: linux-hook-musl-rtld-deepbind.patch
- 文件: `renderdoc/os/posix/linux/linux_hook.cpp`
- 修改: 在 `#include <dlfcn.h>` 后添加 RTLD_DEEPBIND 兼容定义
- 原因: musl libc 不定义 RTLD_DEEPBIND (glibc-specific flag)

### 补丁 0002: plthook-musl-libc-compat.patch
- 文件: `renderdoc/3rdparty/plthook/plthook_elf.c`
- 修改:
  1. 添加 PLTHOOK_MUSL_LIBC 检测（通过 `#ifndef __GLIBC__`）
  2. 为 musl libc 提供 dlinfo 回退（plthook_open_by_handle）
  3. 使 plthook_open_by_address 在 musl 下返回 PLTHOOK_NOT_IMPLEMENTED
  4. 使 plthook_open_executable 在 musl+Linux 下返回 PLTHOOK_NOT_IMPLEMENTED
  5. 为 plthook_open_shared_library 在 musl 下使用 dlopen handle 作为 link_map
- 原因: musl libc 不提供 glibc 扩展函数 dlinfo/dladdr1 和符号 _r_debug/RTLD_DL_LINKMAP

## 验证结果

```bash
# 文件类型验证
file /storage/Users/currentUser/usr/local/lib/librenderdoc.so
# ELF shared object, 64-bit LSB arm64, not stripped

file /storage/Users/currentUser/usr/local/bin/renderdoccmd
# ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

# 库大小
ls -la /storage/Users/currentUser/usr/local/lib/librenderdoc.so
# 4,921,792 bytes (4.9MB)

# 命令行工具大小
ls -la /storage/Users/currentUser/usr/local/bin/renderdoccmd
# 354,816 bytes (345KB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| librenderdoc.so | 4.9MB | renderdoc 核心库（仅核心框架，无图形驱动） |
| renderdoccmd | 345KB | renderdoc 命令行工具 |
| renderdoc_app.h | 36KB | renderdoc 应用 API 头文件 |
| 0001-linux-hook-musl-rtld-deepbind.patch | 502B | RTLD_DEEPBIND 兼容补丁 |
| 0002-plthook-musl-libc-compat.patch | 2.6KB | plthook musl libc 兼容补丁 |

## 注意事项

1. **功能性严重受限**: renderdoc 编译成功但几乎所有图形 API 功能被禁用，
   编译产物仅包含核心框架代码，不能进行实际的图形捕获和调试。
   这是 renderdoc 在 HarmonyOS 上的根本限制。

2. **仅核心库可用**: librenderdoc.so 提供了基础数据结构和序列化功能，
   但不包含任何图形驱动（GL、GLES、Vulkan）。

3. **renderdoccmd 可用**: 命令行工具可以运行基本操作，但因缺少图形驱动，
   大多数功能不可用。

4. **PLT hooking 限制**: 在 musl libc 下，plthook 功能有限：
   - `plthook_open_by_address` 不可用
   - `plthook_open_executable` 不可用
   - `plthook_open_by_handle` 有回退实现
   - `RTLD_DEEPBIND` 被定义为 0（跳过 deepbind 逻辑）

5. **CMAKE_SYSTEM_NAME=Linux**: 需要设置为 Linux 以使 cmake 正确检测 UNIX 平台，
   否则 renderdoc 的 POSIX/Linux 特定代码不会被包含。
---

**编译结束**: 2026-06-04 11:12
**最终状态**: built
