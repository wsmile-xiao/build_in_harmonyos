# librsvg 2.62.3.1 适配笔记（gtk3 生态版）

## 背景
gtk 3.24.52 测试环境中 gdk-pixbuf 需要 SVG loader（2 项上游测试失败：
reftest icon-effect-missing、treeview-fixed-height）。制品仓 `librsvg/2.62.3`
有 OHOS binary，但其 requires 为 **pango/1.56.4**（GTK4/新生态链），与 gtk 3.24.52
生态（pango/1.50.14.1.1、glib/2.84.0.1、gdk-pixbuf/2.44.6.1）不匹配——同一
SONAME 去重后 gdk-pixbuf 生态与 librsvg 生态冲突，loader 无法加载。
按 R37 发布 **2.62.3.1**（gtk3 生态版）。

## 相对 2.62.3 的变更
- `requirements()` 对齐 gtk3 生态：
  - cairo/1.18.4 → **cairo/1.18.4.1**（xlib 版，PR #8991）
  - cairo-gobject/1.18.4 → **cairo-gobject/1.18.4.3**（PR #8992）
  - gdk-pixbuf/2.44.6 → **gdk-pixbuf/2.44.6.1**
  - pango/1.56.4 → **pango/1.50.14.1.1**
  - harfbuzz/14.2.0.1 → **harfbuzz/14.2.0.1.1.1**
  - glib/2.84.0.1、libxml2/2.15.3.1、fontconfig override、freetype/2.14.3 不变
- 补丁沿用 2.62.3（0001 meson.build / 0002 rsvg-meson.build python3 执行、0003 cargo --tests）

## 构建验证
```bash
conan create archives/l/librsvg/2.62.3.1 --version=2.62.3.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
- build() 中无条件运行 C API 上游测试（librsvg-c/tests-c/api.c）；Rust cargo test
  仅 LIBRSVG_ENABLE_UPSTREAM_TESTS=1 时启用（默认禁用，OHOS 构建最小化；如实申报 R51）
- test_package：rsvg_handle_new_from_data() 解析最小 SVG + LIBRSVG_VERSION_STRING 核验（R34）

## 注意事项
- 版本后缀 2.62.3.1 与制品仓 2.62.3 共存；gtk3 生态（pango/1.50 链）引本版本，
  GTK4 生态引 2.62.3，互不影响
- gdk-pixbuf 加载器（librsvg loader .so）需随 gtk 测试环境部署（XDG_DATA_DIRS/loader 路径）

## 本机验证受限说明（2026-09-08）
librsvg 2.62+ 渲染核心为 Rust，构建需 cargo/rustc。本机（CI 设备）无 harmonybrew
Rust 工具链：配方 bootstrap 需下载 harmonybrew 的 openssl@3-3.6.3 bottle，但
harmonybrew.atomgit.com/bottles/ 下 **openssl@3 全版本 bottle 均 404**（rust/zlib
bottle 存在）；用 bind 工具自带 libssl.so.3/libcrypto.so.3 替代时符号不兼容
（`OBJ_nid2sn: symbol not found`）→ **本机无法完整执行 conan create**。
替代验证：`conan graph info` 依赖图解析通过（rc=0）——cairo/1.18.4.1、
cairo-gobject/1.18.4.3、gdk-pixbuf/2.44.6.1、pango/1.50.14.1.1、harfbuzz/14.2.0.1.1.1
全部 Cache 命中且版本匹配，cairo override 正确压掉 pango 的 1.18.4 pin。
CI 官方 worker 装有 harmonybrew Rust（配方 _find_cargo 探测命中，不触发 bootstrap），
由 CI 完成构建与 test_package 验证（R51 环境如实申报）。

**编译日期**: 2026-09-08
**状态**: 配方就绪（本机依赖图解析通过；完整构建待 CI rust 环境）
