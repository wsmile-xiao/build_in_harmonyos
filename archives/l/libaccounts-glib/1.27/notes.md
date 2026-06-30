# libaccounts-glib 1.27 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. 初始化编译环境，下载源码
2. 安装依赖预编译包：glib 2.88.0, libxml2 2.11.9, sqlite3 3.49.1, check 0.15.2
3. 配置 meson 构建：
   ```bash
   export CC=/storage/Users/currentUser/usr/local/bin/clang
   export CXX=/storage/Users/currentUser/usr/local/bin/clang++
   export AR=/storage/Users/currentUser/usr/local/bin/llvm-ar
   export RANLIB=/storage/Users/currentUser/usr/local/bin/llvm-ranlib
   export STRIP=/storage/Users/currentUser/usr/local/bin/llvm-strip
   export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig
   meson setup builddir --prefix=$DEFAULT_PREFIX
   ```
4. 编译：ninja -C builddir
5. 安装：meson install -C builddir --destdir=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到编译器 clang | CC 环境变量需要完整路径 | 设置 CC=/storage/Users/currentUser/usr/local/bin/clang |
| 2 | 缺少 gobject-introspection-1.0 | 预编译包中无此依赖 | 修改 libaccounts-glib/meson.build 使其可选 (required: false) |
| 3 | 缺少 gtkdoc-scan | 文档生成工具未预装 | 禁用 docs/reference 子目录 |
| 4 | 缺少 check 测试库 | 测试依赖未安装 | 安装 check 0.15.2 预编译包 |
| 5 | 链接失败：g_libintl_* 符号未定义 | libintl.so 缺少 g_ 前缀符号，但 libintl.a 有 | 临时使用静态库 libintl.a |
| 6 | 测试失败：无法创建临时文件 | /tmp 只读（R10 Gotcha） | 记录为平台限制，不影响核心功能 |

## 源码修改

### 0001-docs-meson.build.patch
- 禁用 gtkdoc 文档生成（gtkdoc-scan 未预装）
- 平台适配补丁

### 0002-libaccounts-glib-meson.build.patch
- 使 gobject-introspection 可选（required: false）
- 禁用 pygobject 子目录
- 平台适配补丁

### 0003-tools-meson.build.patch
- 禁用 ag-backup 和 ag-tool 工具编译
- 原因：链接问题（libintl 符号）
- 平台适配补丁

## 依赖版本

- glib: 2.88.0
- gio-2.0: 2.88.0
- gio-unix-2.0: 2.88.0
- gobject-2.0: 2.88.0
- libxml-2.0: 2.11.9
- sqlite3: 3.49.1
- check: 0.15.2

## 验证结果

```bash
# 编译成功
ninja -C builddir
# 输出: Build targets in project: 7

# 安装成功
meson install -C builddir --destdir=$TEST_PREFIX
# 安装了 libaccounts-glib.so.1.27 和头文件

# 测试结果
meson test -C builddir
# Ok: 7, Fail: 1
# 失败原因: /tmp 只读导致 check 库无法创建临时文件
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libaccounts-glib.so.1.27 | ~KB | 动态库 |
| libaccounts-glib.pc | - | pkg-config 文件 |
| 头文件 (ag-*.h) | - | 12 个头文件 |

## 注意事项

1. **libintl 链接问题**：当前需要临时使用静态 libintl.a，这是 glib 预编译包使用 G_INTL_STATIC_COMPILATION 的副作用
2. **工具未编译**：ag-backup 和 ag-tool 因链接问题暂未编译，核心库功能完整
3. **测试限制**：测试套件因 /tmp 只读导致部分失败，这是已知平台限制（R10）

---
**编译结束**: 2026-06-02 10:17
**最终状态**: built