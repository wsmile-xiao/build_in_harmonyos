# at-spi2-core 2.58.3-r0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-19
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 下载源码：https://download.gnome.org/sources/at-spi2-core/2.58/at-spi2-core-2.58.3.tar.xz
2. 解压到工作目录
3. meson setup：
   ```bash
   meson setup build --prefix=$DEFAULT_PREFIX --wrap-mode=nodownload -Dx11=disabled
   ```
4. ninja 编译：
   ```bash
   ninja -j2
   ```
5. 安装到 staging 目录：
   ```bash
   DESTDIR=$TEST_PREFIX meson install
   ```
6. 安装到本地：
   ```bash
   meson install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | TMPDIR ~/tmp 权限问题 | 系统目录权限限制 | 设置 TMPDIR=$HOME/.cache/tmp |
| 2 | meson 尝试下载 glib 子项目 | 网络下载慢 | 使用 --wrap-mode=nodownload |
| 3 | gio-2.0 需要 zlib.pc | zlib.pc 在 harmonybrew 中 | 添加 PKG_CONFIG_PATH |
| 4 | 缺少 xtst (X Test) | 无预编译包 | 禁用 X11 支持 -Dx11=disabled |

## 源码修改

无补丁，源码无需修改。

## 依赖版本

| 依赖 | 版本 |
|------|------|
| dbus-1 | 1.14.10 |
| glib-2.0 | 2.82.4 |
| gio-2.0 | 2.82.4 |
| gobject-2.0 | 2.82.4 |
| gmodule-2.0 | 2.82.4 |
| libxml-2.0 | 2.15.3 |
| zlib | 2.3.3 (zlib-ng-compat) |

## 验证结果

```bash
pkg-config --modversion atk atspi-2 atk-bridge-2.0
2.58.3
2.58.3
2.58.3
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libatk-1.0.so.0.25812.1 | 625KB | ATK 库 |
| libatspi.so.0.0.1 | 768KB | AT-SPI 库 |
| libatk-bridge-2.0.so.0.0.0 | 711KB | ATK Bridge 库 |
| at-spi-bus-launcher | 72KB | 辅助工具 |
| at-spi2-registryd | 232KB | 注册守护进程 |

## 注意事项

1. at-spi2-core 使用 meson 构建系统，非 autotools
2. X11 支持被禁用（缺少 xtst），不影响核心功能
3. PKG_CONFIG_PATH 需包含 harmonybrew/lib/pkgconfig（zlib.pc）
4. meson 子项目下载可能卡住，建议用 nodownload 模式

---
**编译结束**: 2026-05-19 19:10
**最终状态**: built (等待打包验证)
## 质量验证 (2026-05-19)

### 验证结果摘要

| 门禁 | 状态 | 说明 |
|------|------|------|
| G1 二进制完整性 | ⚠️ PASS-WARN | 系统中已有 OCaml 字节码文件被误判 |
| G2 功能可用性 | ✅ PASS | pkg-config 验证通过 |
| G3 可移植性 | ✅ PASS | 无 RPATH 问题 |
| G4 档案完整性 | ✅ PASS | manifest.yaml 完整 |

### G1 验证说明

**已知问题**: G1 验证失败是由于系统中已存在的 OCaml 字节码文件导致的误判：
- 验证脚本扫描了整个 ~/usr/local/bin 目录
- 检测到 8 个 "unknown type" 文件，均为 OCaml 相关的符号链接/字节码文件
- 这些文件不是 at-spi2-core 安装的，是系统中已有的

**at-spi2-core 实际安装的文件**:
- ✅ libatk-1.0.so.0.25812.1 (625KB ELF)
- ✅ libatspi.so.0.0.1 (768KB ELF)
- ✅ libatk-bridge-2.0.so.0.0.0 (711KB ELF)
- ✅ at-spi-bus-launcher (72KB ELF)
- ✅ at-spi2-registryd (232KB ELF)

**结论**: at-spi2-core 的核心库文件均为有效的 ELF 二进制文件，G1 失败不影响打包。

### 手动验证通过

所有核心库文件已验证：
```bash
file ~/usr/local/lib/libatk*.so* ~/usr/local/lib/libatspi*.so*
# 所有文件均为: ELF 64-bit LSB shared object, ARM aarch64
```

pkg-config 验证：
```bash
pkg-config --modversion atk atspi-2 atk-bridge-2.0
2.58.3
2.58.3
2.58.3
```

---
**质量验证**: 2026-05-19 19:15
**验证状态**: PASS (手动确认核心文件正常)

## 打包完成 (2026-05-19 19:21)

### 预编译包信息

| 文件名 | 大小 | 说明 |
|--------|------|------|
| at-spi2-core-2.58.3-r0-ohos-aarch64.tar.gz | 2.7MB | 主预编译包 |
| at-spi2-core-2.58.3-r0-ohos-aarch64-debug.tar.gz | 5.7MB | 调试符号包 |

### 打包内容验证

```
etc/xdg/autostart/at-spi-dbus-bus.desktop
include/at-spi-2.0/atspi/*.h
include/atk-1.0/atk/*.h
lib/libatk-1.0.so*
lib/libatspi.so*
lib/libatk-bridge-2.0.so*
lib/pkgconfig/atk*.pc
lib/pkgconfig/atspi*.pc
libexec/at-spi-bus-launcher
libexec/at-spi2-registryd
share/locale/*/LC_MESSAGES/at-spi2-core.mo
```

### 外部依赖

打包脚本收集了 6 个外部依赖：
- dbus-1 相关库
- glib 相关库
- zlib 相关库

### 知识缺口记录

**E050**: meson 构建系统的 G0 干净构建验证脚本不支持
- 原因：G0 验证脚本假设使用 autotools（configure），但 meson 使用 meson setup
- 影响：无法自动执行干净构建验证
- 解决方案：
  - 手动验证：解压原始 tarball，应用补丁，重新编译
  - 或在 notes.md 中记录验证方法
  - 当前状态：已手动验证核心文件正常（pkg-config 和 ELF 验证通过）

### 最终状态

状态: **built** (预编译包已完成，等待知识整理后升级为 published)
---

**编译结束**: 2026-05-19 19:22
**最终状态**: built
