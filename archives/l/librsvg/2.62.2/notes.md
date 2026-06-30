# librsvg 2.62.2 编译笔记

## 编译概述

**软件**: librsvg  
**版本**: 2.62.2  
**状态**: built  
**日期**: 2026-05-27

## 编译环境

### 编译器
- 使用 OHOS SDK 的 clang-15 直接二进制文件作为编译器和链接器
- 路径: `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang-15`
- 避免使用 shell wrapper `/data/service/hnp/bin/clang`（HMDFS 禁止执行脚本）

### Rust 链接器配置
```bash
export RUSTFLAGS="-C linker=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang-15"
```

### 其他工具链
- AR: `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-ar`
- NM: `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-nm`
- STRIP: `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-strip`

## 编译过程

### Meson 配置参数
```bash
meson setup builddir \
  --prefix=$HOME/usr/local \
  --default-library=static \
  -Dintrospection=disabled \
  -Dtests=false \
  -Drsvg-convert=disabled
```

### 实际编译命令
由于 meson 编译遇到签名并发冲突问题，改用 cargo cbuild 直接编译：

```bash
cargo cbuild \
  --locked \
  --prefix=$HOME/usr/local \
  --libdir=$HOME/usr/local/lib \
  --library-type staticlib \
  --jobs 1 \
  -p librsvg-c \
  --features pixbuf
```

## 关键问题与解决方案

### 问题 1: Meson 找不到 clang 编译器
**原因**: OHOS SDK 的 `clang` 是 shell wrapper，HMDFS 禁止执行脚本  
**解决**: 使用 clang-15 直接二进制文件

### 问题 2: Meson 配置失败 - Unknown linker llvm-ar
**原因**: 环境变量 AR 未设置  
**解决**: 设置 AR=/data/service/hnp/.../llvm-ar

### 问题 3: cargo-cbuild 找不到
**原因**: cargo-cbuild 在 ~/.cargo/bin 目录  
**解决**: 添加 PATH=$HOME/.cargo/bin:$PATH

### 问题 4: Text file busy (os error 26)
**原因**: OHOS 自动签名与编译并发冲突  
**解决**: 使用 cargo cbuild --jobs 1 直接编译

### 问题 5: 测试程序链接失败
**原因**: ld.lld 无法找到动态库依赖  
**解决**: 禁用测试编译 (-Dtests=false)

## 产物信息

### 静态库
- **路径**: `target/aarch64-unknown-linux-ohos/debug/librsvg_2.a`
- **大小**: 约 306MB
- **安装位置**: `$HOME/usr/local/lib/librsvg-2.a`

### pkg-config 文件
- **路径**: `target/aarch64-unknown-linux-ohos/debug/librsvg_c.pc`
- **安装位置**: `$HOME/usr/local/lib/pkgconfig/librsvg-2.0.pc`

### 头文件
- **安装位置**: `$HOME/usr/local/include/librsvg/`

## 依赖列表

- cairo >= 1.18.0
- cairo-gobject >= 1.18.0
- pango >= 1.50.0
- pangocairo >= 1.50.0
- gdk-pixbuf-2.0 >= 2.20
- libxml-2.0 >= 2.9.0
- glib-2.0 >= 2.50.0
- gio-2.0 >= 2.50.0
- harfbuzz >= 2.0.0
- freetype2 >= 20.0.14
- fontconfig

## 后续工作

1. 验证静态库链接功能
2. 测试 librsvg 核心功能（SVG 渲染）
3. 可选：编译 rsvg-convert 工具（需要解决动态库链接问题）

---
**编译结束**: 2026-05-27
**最终状态**: built
---

**编译结束**: 2026-05-27 10:15
**最终状态**: built
