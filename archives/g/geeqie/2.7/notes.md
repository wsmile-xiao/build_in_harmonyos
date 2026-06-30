# geeqie 2.7 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-25
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

1. 下载 geeqie 2.7 源码 tar.xz（通过 gh-proxy.com 镜像下载）
2. 安装依赖：
   - 重新编译 cairo 1.18.4（启用 glib/gobject 选项以提供 cairo-gobject）
   - 编译安装 GTK3 3.24.49（仅启用 Broadway 后端，禁用 X11/Wayland）
   - 创建缺失的库符号链接：libpng.so → libpng16.so, libfribidi.so → libfribidi.so.0.4.0, libepoxy.so → libepoxy.so.0.0.0
3. meson setup 配置 geeqie（禁用大部分可选功能）
4. ninja 编译 + ninja install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载失败（HTML内容） | 未指定版本号和下载URL | 使用正确的release下载URL + --no-download |
| 2 | GTK3 缺失 | 系统未安装GTK3 | 从GitHub下载GTK3 3.24.49源码并编译（Broadway backend） |
| 3 | cairo-gobject 缺失 | cairo编译时未启用glib选项 | 重新编译cairo启用-Dglib=enabled |
| 4 | GTK3链接失败 -lfribidi/-lepoxy | 缺少.so符号链接 | 创建 libfribidi.so/libepoxy.so 符号链接 |
| 5 | gdk-pixbuf运行时找不到libpng | NEEDED引用绝对路径/libpng.so但文件不存在 | 创建 libpng.so → libpng16.so 符号链接 |
| 6 | GTK3 meson No backends enabled | 禁用了所有显示后端 | 启用Broadway backend（HTML5渲染） |
| 7 | verify-build G4失败 | manifest缺少build_system字段 | 更新manifest.yaml: build_system: meson |

## 源码修改

无需源码修改。geeqie 2.7 源码本身可在OHOS上编译，仅需安装GTK3等依赖。

## 依赖版本

- GTK3: 3.24.49 (Broadway backend only)
- cairo: 1.18.4 (with gobject)
- glib: 2.88.0
- pango: 1.50.14
- harfbuzz: 14.2.0
- gdk-pixbuf: 2.42.12
- atk: 2.58.3
- epoxy: 1.5.10
- libjpeg: 3.1.4.1
- libtiff-4: 4.6.0
- libopenjp2: 2.5.0

## 验证结果

```bash
# 质量门禁 PASS
# packaging 目录包含两个 tar.gz:
#   geeqie-2.7-ohos-aarch64.tar.gz (31MB)
#   geeqie-2.7-ohos-aarch64-debug.tar.gz (34MB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| geeqie-2.7-ohos-aarch64.tar.gz | 31MB | 预编译包（stripped） |
| geeqie-2.7-ohos-aarch64-debug.tar.gz | 34MB | 预编译包（含debug symbols） |

## 注意事项

- geeqie 使用 Broadway (HTML5) 后端，不依赖 X11/Wayland 显示服务器
- 大部分可选功能（exiv2, heif, webp, pdf, lua等）已禁用，可按需启用
- /tmp路径硬编码问题（PSCAN-FS-001）仅影响插件脚本，不影响核心功能
- 需要确保 GTK3 运行时库可访问（LD_LIBRARY_PATH 或 RPATH）
---

**编译结束**: 2026-05-25 22:47
**最终状态**: built
