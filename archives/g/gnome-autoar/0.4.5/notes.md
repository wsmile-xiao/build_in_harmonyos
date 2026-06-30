# gnome-autoar 0.4.5 编译笔记

## 编译信息
- **编译日期**: 2026-06-04
- **编译器**: clang 15.0.4
- **构建系统**: meson 1.11.1 + ninja 1.13.1
- **平台**: HarmonyOS (OpenHarmony)
- **架构**: aarch64

## 主要问题及解决方案

### 问题1: GLib 版本不匹配
- **问题**: pkg-config 显示 GLib 2.88.0，但实际库文件是 2.76.0，导致链接时找不到 `g_once_init_enter_pointer` 和 `g_once_init_leave_pointer` 符号
- **解决**: 从之前编译的 GLib 2.76.0 staging 目录复制头文件和 pkg-config 文件到系统目录，确保版本一致

### 问题2: 源码下载失败
- **问题**: GNOME 官方源和 Savannah 源因 SSL 证书和连接问题无法下载
- **解决**: 使用 GitLab 源下载（https://gitlab.gnome.org/GNOME/gnome-autoar/-/archive/0.4.5/gnome-autoar-0.4.5.tar.bz2）

## 编译命令总结

```bash
# 配置
export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:~/usr/local/share/pkgconfig:$PKG_CONFIG_PATH
meson setup build --prefix=$HOME/usr/local -Dgtk=false -Dintrospection=disabled -Dtests=false

# 编译
meson compile -C build -j2

# 安装到 staging（DESTDIR 模式）
meson install -C build --destdir=$TEST_PREFIX
```

## 功能验证
- libgnome-autoar-0.so ✅
- gnome-autoar-0.pc ✅
- 头文件完整 ✅

---
*编译者: OpenDesk Compile Agent*
*日期: 2026-06-04*
---

**编译结束**: 2026-06-04 15:45
**最终状态**: built
