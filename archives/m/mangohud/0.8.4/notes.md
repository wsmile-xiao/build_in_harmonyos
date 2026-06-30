# MangoHud 0.8.4 — OpenHarmony 编译记录

## 编译信息
- 软件: MangoHud 0.8.4
- 构建系统: meson (非 autotools)
- 编译日期: 2026-06-04
- 目标平台: aarch64-harmonyos (OpenHarmony)
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 编译状态: ✅ 成功

## 配置选项
```
meson setup builddir --prefix=/storage/Users/currentUser/usr/local
  -Dwith_wayland=disabled
  -Dtests=disabled
  -Dmangoapp=false
  -Dmangohudctl=false
  -Dmangoplot=disabled
  -Dwith_nvml=disabled
  -Dwith_xnvctrl=disabled
```

## 关键问题与解决

### 1. meson host_machine.system() 返回 'harmonyos' (E034 草稿)
- **问题**: meson 在 OpenHarmony 检测 host_machine.system() 为 'harmonyos'（不是 'linux'），导致 `is_unixy=false`、`_GNU_SOURCE` 不被设置、X11/Wayland/dbus 被设为 null_dep
- **症状**: `ssize_t` 未定义、`CLOCK_MONOTONIC` 未声明、`clock_gettime` 未声明
- **解决**: 修改 meson.build，在平台检查列表中添加 'harmonyos'
- **补丁**: 0001-meson-add-harmonyos-to-platform-checks.patch

### 2. ssize_t 在 musl 上未定义
- **问题**: os_socket.h 使用 ssize_t 但未 include <sys/types.h>
- **解决**: 在 os_socket.h 中添加 `#include <sys/types.h>`
- **补丁**: 0002-os_socket-add-sys-types-header-for-ssizet.patch

### 3. libintl.so.8 加载失败
- **问题**: python3 的 RUNPATH 不包含 libintl.so.8 所在目录
- **解决**: 设置 `LD_LIBRARY_PATH=/data/service/hnp/python.org/python_3.12/lib:` 为最高优先级

### 4. Vulkan-Utility-Libraries 子项目
- **问题**: meson wrap 文件需要手动处理
- **解决**: 手动下载并构建 Vulkan-Utility-Libraries-1.4.346

## 已安装产物
- lib/mangohud/libMangoHud.so (9.8MB, ELF 64-bit aarch64)
- lib/mangohud/libMangoHud_opengl.so (9.5MB)
- lib/mangohud/libMangoHud_shim.so (43KB)
- bin/mangohud
- share/vulkan/implicit_layer.d/MangoHud.aarch64.json
- share/doc/mangohud/MangoHud.conf
- share/doc/mangohud/presets.conf
- share/man/man1/mangohud.1

## 预编译依赖包
- libx11/6.4.0
- vulkan-headers/1.3.295
- vulkan-loader/1.3.295
- dbus/1.14.10
- libdrm/2.4.133
- xkbcommon/1.7.0
- meson/1.11.1
- ninja/1.12.1
- python-mako/1.3.12

## 知识图谱草稿
- E034-draft-02FD: meson host_machine.system() 返回 'harmonyos' 而非 'linux'