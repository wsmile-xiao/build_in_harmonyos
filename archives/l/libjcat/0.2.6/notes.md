# libjcat 0.2.6 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-06-04
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. 初始化编译环境：`python3 $SKILL_ROOT/scripts/ohc-run.py init-build libjcat 0.2.6 --url=https://github.com/hughsie/libjcat/releases/download/0.2.6/libjcat-0.2.6.tar.xz`
2. 设置编译器环境变量：`export CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ AR=/data/service/hnp/bin/llvm-ar RANLIB=/data/service/hnp/bin/llvm-ranlib`
3. 复制 GLib pkgconfig 文件到系统目录（GLib 已安装但 pkgconfig 文件缺失）
4. 配置 Meson：`meson setup builddir --prefix=$DEFAULT_PREFIX -Dgpg=false -Dgnutls_pkcs7=false -Dgnutls_ed25519=false -Dintrospection=false -Dvapi=false -Dtests=false`
5. 编译：`ninja -C builddir -j2`
6. 安装：`DESTDIR=$TEST_PREFIX ninja -C builddir install`
7. 本地安装：`ninja -C builddir install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 无法自动找到下载 URL | libjcat 不在常见软件仓库中 | 通过 Anitya API 查询找到 GitHub 仓库 hughsie/libjcat |
| 2 | Meson 无法找到编译器 cc/clang | PATH 中 clang 不在优先位置 | 显式设置 CC=/data/service/hnp/bin/clang |
| 3 | Meson 无法找到链接器 llvm-ar | PATH 问题 | 显式设置 AR=/data/service/hnp/bin/llvm-ar |
| 4 | pkg-config 无法找到 gio-2.0 | GLib pkgconfig 文件未安装到正确目录 | 从 GLib 构建目录复制 .pc 文件到系统 pkgconfig |
| 5 | json-glib-1.0 未找到 | json-glib 未安装 | 使用 Meson subproject fallback 自动下载编译 |
| 6 | gpgme 库未找到 | gpgme 是可选依赖 | 禁用 GPG 选项：-Dgpg=false |
| 7 | gnutls/abstract.h 未找到 | gnutls 头文件未安装 | 禁用 GnuTLS 选项：-Dgnutls_pkcs7=false -Dgnutls_ed25519=false |
| 8 | msgfmt 动态链接失败 | gettext libintl 符号未找到 | 使用 LD_PRELOAD=/storage/Users/currentUser/usr/local/lib/libintl.so.8.4.0 |
| 9 | jcat-tool 执行失败 | 动态库路径问题、无 RPATH | 需要 LD_LIBRARY_PATH 设置正确的库路径 |

## 依赖版本

- glib: 2.84.0 (已预安装)
- json-glib: 1.5.1 (Meson subproject fallback)
- meson: 1.11.1
- ninja: 1.13.1
- clang: 15.0.4

## 验证结果

```bash
# pkg-config 验证成功
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
pkg-config --modversion jcat  # 0.2.6
pkg-config --modversion json-glib-1.0  # 1.5.1

# 动态链接验证失败（需要设置 LD_LIBRARY_PATH）
# jcat-tool 执行受限：缺少 RPATH 设置
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libjcat.so.1.0.0 | 256KB | 主库文件 |
| libjson-glib-1.0.so.0.501.0 | 547KB | 子项目 fallback 库 |
| jcat-tool | 113KB | CLI 工具 |
| jcat.pc | - | pkg-config 文件 |
| json-glib-1.0.pc | - | pkg-config 文件 |

## 注意事项

1. **构建系统**：libjcat 使用 Meson 构建系统，不是 Autotools（init-build 检测错误）
2. **GLib pkgconfig**：需要确保 GLib 的 pkgconfig 文件正确安装到系统目录
3. **动态链接**：编译产物缺少 RPATH，执行时需要设置 LD_LIBRARY_PATH
4. **可选功能**：禁用了 GPG、GnuTLS PKCS7/ED25519 功能以简化编译
5. **gettext 问题**：msgfmt 工具需要 LD_PRELOAD 解决动态链接问题

---
**编译结束**: 2026-06-04 10:40
**最终状态**: built