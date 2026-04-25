# glib 2.88.0 — Release Note

## 编译信息

- **日期**: 2026-04-25
- **平台**: OpenHarmony (ohos-aarch64)
- **构建系统**: meson
- **状态**: ✅ 编译成功

## 依赖库

- libffi ✅ (已安装)
- zlib ✅ (已安装)
- pcre2 ✅ (已安装)

## 补丁列表（4 个）

- 0001-gio-gnetworkmonitornetlink.c.patch
- 0002-gio-meson.build.patch
- 0003-glib-meson.build.patch
- 0004-meson.build.patch

## 打包产物（2 个）

- glib-2.88.0-ohos-aarch64-debug.tar.gz
- glib-2.88.0-ohos-aarch64.tar.gz

## 编译步骤

| Step 1 init | ✅ | URL: download.gnome.org |
| Step 2 patches | ✅ | 4 files modified |
| Step 3 configure | ✅ | meson setup, static build |
| Step 4 make | ✅ | ninja -j$(nproc), 596/596 targets |
| Step 5 install | ✅ | DESTDIR staging |
| Step 8 staging | ✅ | 验证 pkg-config, headers, libs |
| Step 9 package | ✅ | 63606KB tar.gz |
| Step 10 deploy | ✅ | 安装到 ~/usr/local, pkg-config --modversion = 2.88.0 |

## 关键问题与解决方案

## 关键问题

### 1. host_system == 'linux' 检查不包含 harmonyos
- **根因**: Meson 识别 OHOS 平台为 'harmonyos' 而非 'linux'
- **影响**: gjournal-private.c 未编译, 导致 _g_fd_is_journal undefined symbol
- **方案**: 将 `host_system == 'linux'` 改为 `host_system in ['linux', 'harmonyos']`

### 2. linux/socket.h 重定义 sockaddr_storage
- **根因**: OHOS 内核头文件 linux/socket.h 定义了与 sys/socket.h 冲突的 sockaddr_storage
- **方案**: 在 include linux/netlink.h 前用 #define 宏重命名冲突符号
