# libnice 0.1.21 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4
- 状态: built（第二次编译，依赖问题已解决）

## 编译步骤

1. **依赖解决**：安装 glib 2.84.0 动态链接版本（从 ~/tmp/test-install-glib-2.84.0）
2. **配置**：`meson setup builddir --prefix=$HOME/usr/local`
3. **编译**：`ninja -j2`
4. **安装**：`meson install --destdir=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | glib 链接错误 | glib 预编译包使用静态链接 libintl（G_INTL_STATIC_COMPILATION） | 安装 glib 2.84.0 动态链接版本（不定义 G_INTL_STATIC_COMPILATION） |
| 2 | meson 找不到编译器 | 未设置 CC/CXX 环境变量 | 设置 `CC=/data/service/hnp/bin/clang` 和 `CXX=/data/service/hnp/bin/clang++` |
| 3 | meson 找不到 ar | 未设置 AR 环境变量 | 设置 `AR=/data/service/hnp/bin/llvm-ar` |

## 依赖版本

- glib 2.84.0（动态链接版本）
- openssl 1.1.1w
- pcre2 10.40
- libffi 3.4.6
- gettext 0.22.5

## 验证结果

```bash
readelf -d ~/test-install-libnice-0.1.21/storage/Users/currentUser/usr/local/lib/libnice.so.10.13.1 | grep NEEDED
# 输出：
# NEEDED: libgio-2.0.so.0
# NEEDED: libgobject-2.0.so.0
# NEEDED: libglib-2.0.so.0
# NEEDED: libcrypto.so.1.1
# NEEDED: libc.so
```

**确认**：libnice 正确链接了 glib 动态库版本（libglib-2.0.so.0），不是静态库。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libnice.so.10.13.1 | 3.3M | 动态库（链接 glib 2.84.0 动态版本） |
| stund | - | STUN 服务器工具 |
| stunbdc | - | STUN 客户端工具 |

## 注意事项

1. **必须使用 glib 2.84.0 动态链接版本**：预编译的 glib 2.88.0 使用静态链接 libintl，会导致链接失败
2. **必须设置编译器环境变量**：meson 无法自动找到鸿蒙 SDK 的编译器
3. **必须设置 AR 环境变量**：meson 无法自动找到 llvm-ar
---

**编译结束**: 2026-05-26 11:58
**最终状态**: built
