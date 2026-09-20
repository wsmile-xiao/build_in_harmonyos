# gst-libav 1.28.3 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-27
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# Meson 构建 (conan create)
# 1. conan source 下载 gst-libav + gst-plugins-base (subproject)
# 2. PkgConfigDeps 生成 .pc files
# 3. build() 中修正 .pc files + 创建 gettext stub
# 4. meson setup --wrap-mode=default (启用 subproject fallback)
# 5. ninja 编译
# 6. meson install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | gst-plugins-base 未发布 | 制品仓无 gst-plugins-base conan 包 | 下载源码作为 meson subproject 构建 |
| 2 | FFmpeg .pc 版本错误 | conan PkgConfigDeps 用项目版本(7.1.5)而非库ABI版本 | build() 中从头文件读取真实版本修正 .pc |
| 3 | bindtextdomain 未定义 | glib2 libintl.a 提供 g_ 前缀版本 | 创建 gettext_compat stub 库提供标准名称 |
| 4 | meson subproject fallback 被禁 | conan native file 禁用 fallback | meson setup --wrap-mode=default |
| 5 | subproject 选项放在 [project options] | MesonToolchain 不支持 subproject 选项 | 命令行 -Dgst-plugins-base:xxx=disabled |
| 6 | glib2/gstreamer sub-package .pc 缺失 | PkgConfigDeps 只生成单个 .pc | build() 中手动创建 gobject/gio/gmodule 等 .pc |
| 7 | gstreamer .pc prefix=/ 错误 | meson install 时 prefix=/ | 创建 wrapper .pc 指向 conan 包路径 |

## 源码修改

无补丁。源码未做任何修改。

## 依赖版本

- gstreamer 1.28.3 (conan)
- ffmpeg 7.1.5 (conan)
- glib2 2.88.0 (conan, indirect via gstreamer)
- gst-plugins-base 1.28.3 (vendored as meson subproject)

## 交付物

| 文件 | 说明 |
|------|------|
| lib/gstreamer-1.0/libgstlibav.so | GStreamer FFmpeg wrapper plugin |
---

**编译结束**: 2026-08-27 11:36
**最终状态**: published
