# libmbim 1.30.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. **初始化编译环境**
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build libmbim 1.30.0 --url="https://gitlab.freedesktop.org/mobile-broadband/libmbim/-/archive/1.30.0/libmbim-1.30.0.tar.gz"
   ```

2. **安装依赖**
   - glib 2.84.0（从归档安装预编译包）

3. **配置 meson**
   ```bash
   export CC=/data/service/hnp/bin/clang
   export CXX=/data/service/hnp/bin/clang++
   export AR=/data/service/hnp/bin/llvm-ar
   export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig
   meson setup builddir --prefix=/storage/Users/currentUser/usr/local -Dbash_completion=false -Dintrospection=false -Dman=false
   ```

4. **编译**
   ```bash
   cd builddir && ninja -j2
   ```

5. **安装**
   ```bash
   DESTDIR=/storage/Users/currentUser/test-install-libmbim-1.30.0 ninja install
   ninja install  # 本地安装
   ```

6. **打包**
   ```bash
   tar czf libmbim-1.30.0-ohos-aarch64.tar.gz bin lib include libexec
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到编译器 | CC/CXX/AR 环境变量未设置 | 设置环境变量 export CC=/data/service/hnp/bin/clang 等 |
| 2 | 缺少 glib-2.0 依赖 | 运行时依赖未发现 | 从归档安装 glib 2.84.0 预编译包 |
| 3 | sockaddr_storage 重定义（E091） | OHOS 内核头文件 linux/socket.h 与 musl sys/socket.h 冲突 | 使用宏守卫 `#define sockaddr_storage __linux_sockaddr_storage` |

## 源码修改

4 个补丁文件，修复 E091 sockaddr_storage 重定义：

1. `0001-src-libmbim-glib-mbim-helpers-netlink.c.patch`
   - 在 linux/netlink.h 包含前添加宏守卫

2. `0002-src-libmbim-glib-mbim-net-port-manager-wdm.c.patch`
   - 同上

3. `0003-src-libmbim-glib-mbim-net-port-manager-wwan.c.patch`
   - 同上

4. `0004-src-libmbim-glib-mbim-net-port-manager.c.patch`
   - 同上

## 依赖版本

- glib: 2.84.0 (meson 需要 glib-2.0, gio-2.0, gobject-2.0, gio-unix-2.0)

## 验证结果

```bash
pkg-config --modversion mbim-glib
# 1.30.0

pkg-config --cflags mbim-glib
# -DG_INTL_STATIC_COMPILATION -pthread -I/storage/Users/currentUser/usr/local/include/libmbim-glib ...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmbim-1.30.0-ohos-aarch64.tar.gz | 3.7M | 预编译包 |
| 0001-E091-mbim-helpers-netlink.patch | 10行 | sockaddr_storage 宏守卫 |
| 0002-E091-mbim-net-port-manager-wdm.patch | 11行 | sockaddr_storage 宏守卫 |
| 0003-E091-mbim-net-port-manager-wwan.patch | 10行 | sockaddr_storage 宏守卫 |
| 0004-E091-mbim-net-port-manager.patch | 11行 | sockaddr_storage 宏守卫 |

## 注意事项

- libmbim 使用 meson 构建系统，非 autotools
- 需要显式设置 CC/CXX/AR 环境变量，否则 meson 找不到编译器
- E091 错误模式：所有包含 linux/netlink.h 的文件都需要宏守卫
---

**编译结束**: 2026-06-02 10:12
**最终状态**: built
