# peek 1.5.1 适配笔记

## 编译环境
- 构建系统: meson (Vala/C project)
- 编译日期: 2026-06-04
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built ✅

## 编译步骤

1. **init-build**: Successfully initialized peek 1.5.1 source directory
2. **CMakeLists.txt rename**: Renamed CMakeLists.txt → CMakeLists.txt.disabled to force meson detection (peek has both cmake and meson build files; ohc-run.py detects cmake first)
3. **meson setup**: Successfully configured with `meson setup builddir --prefix=/storage/Users/currentUser/usr/local`
4. **ninja build**: Successfully built 96/96 targets
5. **DESTDIR install**: Successfully installed with `DESTDIR=/storage/Users/currentUser/tmp/test-install-peek-1.5.1 ninja -C builddir install`

### Key environment settings
```bash
export PKG_CONFIG_PATH="/storage/Users/currentUser/usr/local/lib/pkgconfig:/storage/Users/currentUser/usr/local/share/pkgconfig"
export LD_LIBRARY_PATH="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:/storage/Users/currentUser/usr/local/lib:/storage/Users/currentUser/usr/local/lib/external:/storage/Users/currentUser/usr/local/lib/vala-0.56:/data/service/hnp/python.org/python_3.12/lib:/storage/Users/currentUser/usr/local/lib:/data/service/hnp/magic-cli.org/magic-cli_1.0.0/lib:/data/service/hnp/libxml2.org/libxml2_2.11.9/lib"
```

### Meson configure output
```
Run-time dependency gtk+-3.0 found: YES 3.24.38
Run-time dependency keybinder-3.0 found: NO (optional, correctly disabled)
Run-time dependency cairo found: YES 1.18.2
Run-time dependency gio-2.0 found: YES 2.88.0
Run-time dependency glib-2.0 found: YES 2.88.0
Run-time dependency gmodule-2.0 found: YES 2.88.0
Message: Compiling with features for GTK >= 3.20
Message: Compiling with features for GTK >= 3.22
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 状态 |
|---|------|------|----------|------|
| 1 | Build driver detected cmake instead of meson | peek source has both CMakeLists.txt and meson.build; _detect_build_system() checks CMakeLists.txt first | Rename CMakeLists.txt → CMakeLists.txt.disabled to force meson detection | ✅ 已解决 |
| 2 | meson linker detection failed (lld can't find libxml2.so.16) | OHOS SDK's lld requires libxml2.so.16 which wasn't in LD_LIBRARY_PATH | Add `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib` and `/data/service/hnp/libxml2.org/libxml2_2.11.9/lib` to LD_LIBRARY_PATH | ✅ 已解决 |
| 3 | Previous build failed: GTK3 not available | GTK3 was not installed on OpenHarmony | GTK3 (3.24.38) is now installed with pkg-config files | ✅ 已解决 |
| 4 | Vala compiler binary requires ELF signing | Precompiled Vala binaries need ELF signatures | Already signed from previous attempt; valac symlink already present | ✅ 已解决 |

## 源码修改

- Renamed `CMakeLists.txt` → `CMakeLists.txt.disabled` (and all subdirectory CMakeLists.txt files)
- Reason: Force meson build system detection (build driver prioritizes cmake when both exist)
- No actual source code modifications required

## 依赖版本

| 依赖 | 版本 | 状态 |
|------|------|------|
| GTK3 (gtk+-3.0) | 3.24.38 | ✅ 已安装 |
| glib-2.0 | 2.88.0 | ✅ 已安装 |
| gio-2.0 | 2.88.0 | ✅ 已安装 |
| gmodule-2.0 | 2.88.0 | ✅ 已安装 |
| cairo | 1.18.2 | ✅ 已安装 |
| pango | 1.56.0 | ✅ 已安装 |
| atk | 2.38.0 | ✅ 已安装 |
| gdk-pixbuf | 2.42.12 | ✅ 已安装 |
| epoxy | 1.5.10 | ✅ 已安装 |
| harfbuzz | ✅ | ✅ 已安装 |
| Vala (valac) | 0.56.18 | ✅ 已安装 |
| keybinder-3.0 | — | ❌ 不可用 (optional, correctly disabled) |

## 验证结果

```bash
# Binary details
file /storage/Users/currentUser/tmp/test-install-peek-1.5.1/storage/Users/currentUser/usr/local/bin/peek
# ELF shared object, 64-bit LSB arm64, dynamic, not stripped
# Size: 1,190,464 bytes (1.19 MB)

# 36 files installed total
```

## 交付物

- Binary: peek (1.19 MB, aarch64 ELF)
- Desktop file, icons, translations, dbus service, GSettings schema

## 注意事项

1. **CMakeLists.txt must be disabled**: peek has dual cmake/meson support; the build driver always detects cmake first. The .disabled rename must be preserved in patches.
2. **LD_LIBRARY_PATH must include OHOS SDK lib**: The linker (lld) from the OHOS SDK needs libxml2.so.16, which is in `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib`.
3. **keybinder-3.0 is optional**: Not available on OpenHarmony, but meson correctly handles `required: false`.
4. **Build warnings are benign**: Deprecation warnings in Vala-generated C code (g_once_init_enter, g_spawn_check_exit_status, Gdk.Screen.get_width/height) are expected with newer glib/GTK versions.

## 知识图谱

- **Build system detection priority**: When a project has both CMakeLists.txt and meson.build, ohc-run.py detects cmake first. Workaround: rename CMakeLists.txt to force meson detection.
- **OHOS SDK linker dependency**: lld requires libxml2.so.16 in LD_LIBRARY_PATH; add `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib` to LD_LIBRARY_PATH.
- **GTK3 availability**: GTK3 (3.24.38) is now available on OpenHarmony with full pkg-config and development headers.

---

**编译结束**: 2026-06-04
**最终状态**: built ✅