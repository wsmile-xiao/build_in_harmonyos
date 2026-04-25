# glib latest 编译进度

**日期**: 2026-04-21
**版本**: 2.88.0
**构建系统**: meson
**状态**: ✅ 编译完成

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | URL: download.gnome.org |
| Step 2 patches | ✅ | 4 files modified |
| Step 3 configure | ✅ | meson setup, static build |
| Step 4 make | ✅ | ninja -j$(nproc), 596/596 targets |
| Step 5 install | ✅ | DESTDIR staging |
| Step 6 safety | ⏭️ | 静态库无需安全弹窗验证 |
| Step 7 check | ⏭️ | tests=false（避免构建期运行时依赖） |
| Step 8 staging | ✅ | 验证 pkg-config, headers, libs |
| Step 9 package | ✅ | 63606KB tar.gz |
| Step 10 deploy | ✅ | 安装到 ~/usr/local, pkg-config --modversion = 2.88.0 |
| Step 11 finish | ⏳ | |

## 构建选项

```bash
meson setup builddir --prefix=$HOME/usr/local \
  -Dnls=disabled -Dlibmount=disabled -Dselinux=disabled \
  -Dtests=false -Ddefault_library=static -Doss_fuzz=disabled \
  -Dxattr=false -Ddtrace=disabled -Dsystemtap=disabled \
  -Dintrospection=disabled
```

## 依赖

- libffi ✅ (已安装)
- zlib ✅ (已安装)
- pcre2 ✅ (已安装)

## 源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| meson.build | host_system == 'linux' 不匹配 harmonyos | sed: linux → ['linux', 'harmonyos'] | ⏳ 待 refresh-patch |
| glib/meson.build | gjournal-private.c 未编译导致链接失败 | sed: linux → ['linux', 'harmonyos'] | ⏳ 待 refresh-patch |
| gio/meson.build | 同上, gio-launch-desktop 也需要 gjournal | sed: linux → ['linux', 'harmonyos'] | ⏳ 待 refresh-patch |
| gio/gnetworkmonitornetlink.c | OHOS linux/socket.h 重定义 sockaddr_storage | #define 宏保护 | ⏳ 待 refresh-patch |

## 关键问题

### 1. host_system == 'linux' 检查不包含 harmonyos
- **根因**: Meson 识别 OHOS 平台为 'harmonyos' 而非 'linux'
- **影响**: gjournal-private.c 未编译, 导致 _g_fd_is_journal undefined symbol
- **方案**: 将 `host_system == 'linux'` 改为 `host_system in ['linux', 'harmonyos']`

### 2. linux/socket.h 重定义 sockaddr_storage
- **根因**: OHOS 内核头文件 linux/socket.h 定义了与 sys/socket.h 冲突的 sockaddr_storage
- **方案**: 在 include linux/netlink.h 前用 #define 宏重命名冲突符号

### 3. 共享库运行时加载失败
- **根因**: OHOS 上 musl ldso 无法加载构建目录中的未签名 .so 文件
- **方案**: 使用 default_library=static 构建静态库, 避免 .so 运行时加载问题

## 发现与知识

- ✅ [E081] Meson 在 HarmonyOS 上检测 host_system 为 'harmonyos', 不是 'linux' → draft/E081
- ✅ [E082] OHOS 内核头文件 linux/socket.h 与 musl sys/socket.h 有 struct sockaddr_storage 冲突 → draft/E082
- ✅ [L2] 静态构建 glib 可避免共享库运行时加载签名问题 (default_library=static) → manifest.yaml
---

**编译结束**: 2026-04-25 05:49
**最终状态**: partial
