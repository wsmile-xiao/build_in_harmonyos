# libgda 6.0.0 编译笔记

## 编译环境

- 平台: HarmonyOS (aarch64-unknown-ohos)
- 构建系统: meson 1.11.1
- 编译器: clang 15.0.4

## 依赖版本

- glib-2.0: 2.88.0
- libxml-2.0: 2.13.5
- sqlite3: 3.49.1
- iso-codes: 4.16.0
- valac: 0.56.17
- intltool: 0.51.0

## 编译过程

1. **下载源码**: 从 GNOME FTP 镜像下载 libgda-6.0.0.tar.xz
2. **配置**: 使用 meson setup，禁用可选功能以减少依赖
3. **修复**: libxml-2.0.pc Cflags 头文件路径修正
4. **编译**: ninja -C build，460 个目标全部成功
5. **安装**: DESTDIR staging + 本地安装

## 关键修复

### libxml-2.0.pc Cflags 修复

原始 pkg-config 返回 `-I${includedir}`，但头文件实际在 `libxml2/` 子目录下。
修改为 `-I${includedir}/libxml2`，解决 `'libxml/tree.h' file not found` 错误。

## 编译配置

```bash
meson setup build --prefix=$HOME/usr/local \
  -Dui=false -Dexperimental=false -Dtools=false \
  -Ddoc=false -Dexamples=false -Djson=false \
  -Dlibsoup=false -Dlibsecret=false
```

## 质量门禁

- G1: PASS (库大小 15.7MB)
- G2: PASS (pkg-config 版本 6.0.0)
- G3: PASS (71 个头文件)
- G4: PASS (SQLite provider 存在)

## 编译状态

**built** - 编译成功，可正常使用
