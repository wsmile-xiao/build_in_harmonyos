# libgnt 2.14.0 编译笔记

## 版本信息

**版本**: 2.14.0
**来源**: GitHub 镜像 dylex/libgnt (v2.14.0 tag)
**说明**: libgnt 自 Pidgin 项目分离后的里程碑版本，首次使用 Meson 构建系统

## 依赖安装

### 预编译包安装记录

**日期**: 2026-06-15

依赖包通过 cmd-pkgs 预编译包安装：

1. **GLib 2.88.0** ✅
   ```bash
   curl -k -fsSL https://gitcode.com/.../install.sh | sh -s -- glib 2.88.0
   ```
   安装成功，pkg-config 可检测

2. **ncurses 6.4** ✅
   ```bash
   curl -k -fsSL https://gitcode.com/.../install.sh | sh -s -- ncurses 6.4
   ```
   手动复制文件到 ~/usr/local（安装脚本超时）
   设置 PKG_CONFIG_PATH 后可检测

3. **libxml2 2.15.3** ✅
   ```bash
   curl -k -fsSL https://gitcode.com/.../install.sh | sh -s -- libxml2 2.15.3
   ```
   安装成功

### SSL 证书问题

**问题**: HarmonyOS 系统上 curl/wget 无法验证 GitCode/GitHub SSL 证书
**错误**: `SSL certificate verify failed: unable to get local issuer certificate`
**解决方案**: 使用 `-k` 参数禁用 SSL 验证

### PKG_CONFIG_PATH 配置

```bash
export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
```

验证：
```bash
pkg-config --modversion glib-2.0  # 2.88.0
pkg-config --modversion ncurses    # 6.4
pkg-config --modversion libxml-2.0 # 2.15.3
```

## 构建系统

libgnt 使用 Meson 构建系统（自 2.14.0 开始）：
- meson.build 文件存在
- 需要 Meson ≥0.37.0（系统已安装 Meson 1.11.1 ✅）

## 源码下载

**URL**: https://github.com/dylex/libgnt/archive/refs/tags/v2.14.0.tar.gz
**方式**: 手动下载（init-build 自动下载失败）
**命令**: `curl -k -L -o libgnt-2.14.0.tar.gz <URL>`
**解压**: tarball 包含 libgnt-2.14.0/ 目录

---

**编译开始**: 2026-06-15 14:48

## 编译过程

### Meson 配置

**成功**: ✅

配置命令：
```bash
meson setup build --prefix=$DEFAULT_PREFIX
```

关键依赖验证：
- GLib 2.88.0 ✅
- ncursesw ✅（需要修改 meson.build 添加本地搜索路径）
- libxml2 2.15.3 ✅

### 编译

**成功**: ✅

遇到的问题：
1. **ncurses 搜索路径问题**: Meson 默认在 `/usr/include` 搜索 ncurses.h，但我们的安装在 `~/usr/local/include`
   - 解决方案: 修改 meson.build 第 89-90 行，添加 local_prefix 到搜索路径
   - 补丁: 0001-meson-add-local-prefix-search-path.patch

2. **gtkdoc-scan 缺失**: 文档生成工具不可用
   - 解决方案: 注释掉 meson.build 第 234 行的 `subdir('doc')`
   - 补丁: 0001-meson-add-local-prefix-search-path.patch

3. **NCURSES_OPAQUE_PANEL 问题**: ncurses 定义了 `NCURSES_OPAQUE_PANEL 1`，导致无法直接访问 `panel->win`
   - 错误: incomplete definition of type 'struct panel'
   - 解决方案: 修改 gntwm.c，将所有 `panel->win` 替换为 `panel_window(panel)`，`below->win` 替换为 `panel_window(below)`
   - 涉及 15 处修改（第 170-200 行）
   - 补丁: 0002-gntwm-fix-ncurses-opaque-panel.patch

编译命令：
```bash
ninja -C build -j1
```

### 安装

**成功**: ✅

Staging 安装（DESTDIR 模式）：
```bash
DESTDIR=$TEST_PREFIX ninja -C build install
```

本地安装（不带 DESTDIR）：
```bash
ninja -C build install
```

安装产物：
- libgnt.so.0.14.0 (5.6MB)
- 头文件: gnt/*.h (26 个文件)
- pkg-config: gnt.pc
- 插件: irssi.so, s.so

### 测试

**无测试定义**: Meson 项目未定义测试套件

### 预编译包制作

**成功**: ✅

产物: libgnt-2.14.0-ohos-aarch64.tar.gz (9858KB)

---

**编译结束**: 2026-06-15 14:58
**最终状态**: built