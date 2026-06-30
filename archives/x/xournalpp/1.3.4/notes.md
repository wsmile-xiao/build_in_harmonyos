# xournalpp 1.3.4 — 编译笔记

## 编译环境
- OpenHarmony SDK 26.0.0.18 (aarch64)
- 编译器: clang++ (ohos-sdk)
- 目标架构: aarch64

## 依赖安装
- 预编译包安装: gtk+-3.0/3.24.43, glib-2.0/2.88.0, pango/1.50.14, gdk-pixbuf-2.42.12, atk/2.58.3, harfbuzz/14.2.0, libzip/1.10.1, libxml-2.0/2.15.3
- 源码编译安装: cairo-1.18.4 (meson+ninja), poppler-23.12.0-glib (cmake+make)
- poppler 手动安装: 复制 .so + 头文件到 ~/usr/local，补齐 generated headers (poppler-macros.h, poppler-enums.h, poppler-features.h)

## C++20 兼容性修复（6个补丁）
1. **CMakeLists.txt**: librsvg-2.0 从 REQUIRED 改为可选 ENABLE_RSVG option
2. **config-features.h.in**: 添加 ENABLE_RSVG cmakedefine
3. **PointerContainerView.h**: 移除 std::ranges::random_access_range/static_assert（ohos libcxx incomplete）
4. **ViewIteratorBase.h**:
   - typename keyword for dependent types
   - operator== 从成员函数改为 hidden friend（C++20 reversed-argument ambiguity）
   - 移除 operator!=（C++20 auto-generated from ==）
5. **utf8_view.h**: 完整重写，移除 std::ranges::view_interface 继承（ohos libcxx incomplete），添加 requires(!is_pointer_v) 约束避免 pointer type 误匹配
6. **xoj-preview-extractor/CMakeLists.txt**: 条件跳过 thumbnailer（需要 librsvg）

## CMake 配置选项
- ENABLE_RSVG=OFF, ENABLE_AUDIO=OFF, ENABLE_CPPTRACE=OFF
- ENABLE_QPDF=OFF, ENABLE_PLUGINS=OFF, ENABLE_GTK_SOURCEVIEW=OFF
- CMAKE_DISABLE_FIND_PACKAGE_X11=ON, WITH_MAN=OFF
- CMAKE_BUILD_TYPE=RelWithDebInfo

## 已知问题
- poppler DESTDIR make install 失败（png undefined symbols: libfreetype.a 引用 libpng 但链接时缺少）
- poppler-glib.so 只产生未版本化的 .so 文件
- poppler cpp/poppler/*.h 头文件不存在于源码中
- libzip.so symlink 需手动创建（预编译包只有 .so.5.5）
---

**编译结束**: 2026-05-30 15:00
**最终状态**: built
