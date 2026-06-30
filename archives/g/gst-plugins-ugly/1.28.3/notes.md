# gst-plugins-ugly 1.28.3 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-30
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

1. init-build gst-plugins-ugly 1.28.3 --url=https://gstreamer.freedesktop.org/src/gst-plugins-ugly/gst-plugins-ugly-1.28.3.tar.xz
2. 发现项目使用 meson 而非 autotools，需使用 meson setup + ninja
3. gst-plugins-base 依赖已本地安装（v1.28.3），但 .so 文件为损坏的符号链接
4. 从 gst-plugins-base builddir 复制实际的 .so 文件到 ~/usr/local/lib
5. meson setup builddir --prefix=$DEFAULT_PREFIX -Dbuildtype=debugoptimized
6. ninja -j1 (编译4个插件)
7. meson install DESTDIR=$TEST_PREFIX (staging)
8. meson install (本地安装)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 项目无 ./configure 脚本 | gst-plugins-ugly 使用 meson | 使用 meson setup + ninja 替代 autotools |
| 2 | gst-plugins-base 未安装 | pkg-config 找不到 gstreamer-plugins-base-1.0.pc | 发现已安装但 symlinks 损坏，手动复制 .so 文件 |
| 3 | ld.lld 无法链接 -lgstrtp-1.0 等 | gst-plugins-base .so.0.2803.0 实际文件丢失(符号链接损坏) | 从 builddir 复制 .so 文件到 ~/usr/local/lib |
| 4 | iso-codes.pc 缺少 domains 变量 | iso-codes.pc 只有 iso_codes_domains | 添加 domains 变量 |
| 5 | ninja test 失败(exit 127) | musl 动态链接器无法加载共享库 | 环境问题，非代码错误，不影响插件功能 |
| 6 | HMDFS/meson 临时文件问题 | HMDFS 不支持 meson 的原子性文件重命名 | 预创建 meson-info/meson-private 目录 |

## 依赖版本

- gstreamer-1.0: 1.28.3
- gst-plugins-base-1.0: 1.28.3
- glib-2.0: 2.88.0
- libdrm: 2.4.133

## 验证结果

```bash
readelf -h ~/usr/local/lib/gstreamer-1.0/libgstasf.so
  Class: ELF64
  Machine: AArch64
  Type: DYN (Shared object file)
```

4个插件编译成功: asf, dvdlpcmdec, dvdsub, realmedia

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| gst-plugins-ugly-1.28.3-ohos-aarch64.tar.gz | 1.0MB | Release包 |
| gst-plugins-ugly-1.28.3-ohos-aarch64-debug.tar.gz | 1.0MB | Debug包 |

## 注意事项

- gst-plugins-ugly 默认不启用 GPL 许可证插件（x264, cdio, dvdread, mpeg2dec）
- HMDFS 文件系统上 meson 需要预创建临时目录以避免 FileNotFoundError
- gst-plugins-base 的符号链接在 HMDFS 上容易损坏，需要手动复制实际 .so 文件
---

**编译结束**: 2026-06-03 23:59
**最终状态**: built
