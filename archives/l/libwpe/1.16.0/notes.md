# libwpe 1.16.0 适配笔记

## 编译环境
- 构建系统: meson（手动编译）
- 编译日期: 2026-06-15
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

1. 下载源码：https://wpewebkit.org/releases/libwpe-1.16.0.tar.xz
2. 修改 CMakeLists.txt：将 cmake_minimum_required VERSION 从 3.0 改为 3.5（适配 CMake 4.1.2）
3. 修改 meson.build：移除 EGL 必需检查，允许在没有 EGL 的情况下编译
4. 使用 meson 编译（禁用 xkbcommon）：
   ```bash
   meson setup --prefix=$DEFAULT_PREFIX -Denable-xkb=false build
   ninja -C build -j1
   meson install -C build --destdir=$TEST_PREFIX
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 版本不兼容 | cmake_minimum_required(VERSION 3.0) 低于 CMake 4.1.2 支持的最低版本 3.5 | 修改 CMakeLists.txt 第 1-2 行，改为 VERSION 3.5 |
| 2 | 缺少 EGL 库 | 鸿蒙系统没有预装 EGL/Mesa 图形库，且 CMakeLists.txt 中 find_package(EGL REQUIRED) | 切换到 meson 构建系统，修改 meson.build 移除必需检查 |
| 3 | 缺少 xkbcommon | 鸿蒙系统没有预装 xkbcommon 键盘库 | 使用 -Denable-xkb=false 禁用 xkbcommon |

## 源码修改

1. **CMakeLists.txt** (第 1-2 行)：
   - 原：`cmake_minimum_required(VERSION 3.0)` + `cmake_policy(VERSION 3.0)`
   - 改：`cmake_minimum_required(VERSION 3.5)` + `cmake_policy(VERSION 3.5)`

2. **meson.build** (第 57-67 行)：
   - 原：EGL 未找到时在非 Windows 系统上强制检查 EGL/eglplatform.h
   - 改：移除强制检查，允许在没有 EGL 的情况下编译

## 依赖版本

- meson: 1.11.0
- ninja: 1.13.1
- clang/clang++: 15.0.4
- pkg-config: 0.29.2

## 验证结果

```bash
# 编译产物
ls -lh /storage/Users/currentUser/test-install-libwpe-1.16.0/storage/Users/currentUser/usr/local/lib/
libwpe-1.0.so -> libwpe-1.0.so.1
libwpe-1.0.so.1 -> libwpe-1.0.so.1.9.3
libwpe-1.0.so.1.9.3 (共享库)

# 头文件
ls /storage/Users/currentUser/test-install-libwpe-1.16.0/storage/Users/currentUser/usr/local/include/wpe-1.0/wpe/
export.h, gamepad.h, input.h, input-xkb.h, keysyms.h, libwpe-version.h,
loader.h, pasteboard.h, process.h, renderer-backend-egl.h, renderer-host.h,
version.h, version-deprecated.h, view-backend.h, wpe-egl.h, wpe.h

# pkg-config 文件
/storage/Users/currentUser/test-install-libwpe-1.16.0/storage/Users/currentUser/usr/local/lib/pkgconfig/wpe-1.0.pc
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libwpe-1.0.so.1.9.3 | ~XX KB | 共享库（主库） |
| wpe-1.0.pc | ~XX KB | pkg-config 文件 |
| 头文件（16 个） | ~XX KB | include/wpe-1.0/wpe/*.h |

## 注意事项

1. **EGL 缺失影响**：编译时禁用了 EGL 检查，生成的库可能无法使用 renderer-backend-egl 功能
2. **xkbcommon 缺失影响**：禁用了 xkbcommon，键盘输入功能可能受限
3. **构建系统切换**：从 CMake 切换到 meson，因为 meson 中 EGL 是可选的（required: false）
4. **适用场景**：适用于不需要完整图形栈的环境，如果需要完整功能，需先编译 EGL 和 xkbcommon
---

**编译结束**: 2026-06-15 18:14
**最终状态**: built
