# gtk+ 3.24.38 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-27
- 编译器: clang 18.1.8
- 状态: published

## 编译步骤

1. **下载源码**
   ```bash
   wget -O ~/tmp/gtk+-3.24.38.tar.xz "https://repo.huaweicloud.com/gnome/sources/gtk+/3.24/gtk+-3.24.38.tar.xz"
   tar xf gtk+-3.24.38.tar.xz
   ```

2. **配置 meson**
   ```bash
   cd gtk+-3.24.38
   mkdir builddir && cd builddir
   meson setup .. --prefix=$HOME/usr/local \
     -Dx11_backend=false \
     -Dwayland_backend=false \
     -Dbroadway_backend=true \
     -Dintrospection=false
   ```

3. **编译**
   ```bash
   ninja -j2
   ```

4. **安装**（手动复制）
   ```bash
   cp libgtk-3.so.* ~/usr/local/lib/
   cp libgdk-3.so.* ~/usr/local/lib/
   cp libgailutil-3.so.* ~/usr/local/lib/
   # 头文件和 pkg-config 文件也复制
   ```

5. **签名**
   ```bash
   /data/service/hnp/bin/binary-sign-tool sign -selfSign 1 -inFile libgtk-3.so.0.2406.32 -outFile signed.so -signAlg SHA256withECDSA
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson build.ninja 路径问题 | build.ninja 硬编码 `${source_dir}/meson` | 创建符号链接 `ln -s ~/usr/local/bin/meson ./meson` |
| 2 | ninja install 失败 | meson 内部 python 无法加载 libintl.so.8 | 手动复制编译产物到安装目录 |
| 3 | 动态库无法加载 | OpenHarmony 要求共享库必须签名 | 使用 binary-sign-tool 签名 |
| 4 | 缺少 X11/Wayland 后端 | HarmonyOS 无原生图形系统 | 使用 broadway HTML5 后端 |

## 源码修改

无补丁，通过 meson 配置选项解决平台问题。

## 依赖版本

- glib-2.0: 2.88.0
- cairo: 1.18.2
- cairo-gobject: 1.18.2
- pango: 1.50.14
- gdk-pixbuf-2.0: 2.42.12
- atk: 2.38.0
- fribidi: 1.0.12
- epoxy: 1.5.10
- libpng16: 1.6.43
- fontconfig: 2.16.0
- freetype: 2.14.3
- harfbuzz: 14.2.0
- pixman: 0.46.4

## 验证结果

```bash
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig"
pkg-config --modversion gtk+-3.0
# 输出: 3.24.38 ✅

ls ~/usr/local/lib/libgtk-3.so.*
# libgtk-3.so.0.2406.32 (36 MB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| gtk+-3.24.38-ohos-aarch64.tar.gz | 117 MB | 预编译包 |
| libgtk-3.so.0.2406.32 | 36 MB | GTK+ 核心库 |
| libgdk-3.so.0.2406.32 | 1.7 MB | GDK 库 |
| libgailutil-3.so.0.0.0 | 114 KB | 辅助工具库 |

## 注意事项

1. **Broadway 后端**: GTK+ 在 HarmonyOS 上使用 broadway HTML5 后端，需要启动 broadwayd 服务
2. **动态库签名**: 所有共享库必须使用 binary-sign-tool 签名才能加载
3. **依赖链完整**: 需要 cairo-gobject（cairo 启用 glib 支持）才能编译 GTK+