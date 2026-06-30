# zathura-pdf-poppler 0.3.4 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-06-02
- 编译器: clang/clang++
- 状态: built

## 编译步骤

zathura-pdf-poppler 是 zathura 的 Poppler PDF 插件，使用 meson 构建系统。由于需要 zathura 和 girara-gtk3 作为依赖，必须先编译安装这些依赖。

### 前置依赖编译

1. **girara-gtk3 0.4.5**: 从 pwmt.org 下载源码，meson 构建
   ```bash
   meson setup builddir --prefix=$DEFAULT_PREFIX -Djson=disabled
   meson compile -C builddir
   DESTDIR=$TEST_PREFIX meson install -C builddir  # staging
   meson install -C builddir  # 系统安装
   ```

2. **zathura 0.5.14**: 从 pwmt.org 下载源码，meson 构建
   ```bash
   meson setup builddir --prefix=$DEFAULT_PREFIX
   meson compile -C builddir
   DESTDIR=$TEST_PREFIX meson install -C builddir  # staging
   meson install -C builddir  # 系统安装
   ```
   注意：zathura 编译时遇到 sqlite3.h 头文件缺少 sqlite3_mprintf 等声明的问题，需手动补充。

### zathura-pdf-poppler 编译

```bash
meson setup builddir --prefix=$DEFAULT_PREFIX
meson compile -C builddir
DESTDIR=$TEST_PREFIX meson install -C builddir  # staging
meson install -C builddir  # 系统安装
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | zathura 编译失败：sqlite3_mprintf 未声明 | 系统 sqlite3.h 头文件被精简，缺少部分 API 声明 | 手动补充 sqlite3_mprintf、sqlite3_compileoption_used 等声明到 sqlite3.h |
| 2 | girara-gtk3 和 zathura 未安装 | zathura-pdf-poppler 依赖 girara-gtk3 和 zathura，但系统中未安装 | 先编译安装 girara 0.4.5 和 zathura 0.5.14 |
| 3 | init-build 系统猜测为 autotools | URL 中不含 meson 关键字 | 手动修正 manifest.yaml 中的 build_system 为 meson |

## 源码修改

无补丁。zathura-pdf-poppler 源码无需修改，所有问题均为系统依赖层面。

## 依赖版本

- zathura/0.5.14（本编译环境自建）
- girara-gtk3/0.4.5（本编译环境自建）
- poppler-glib/23.12.0（系统已有）
- glib-2.0/2.88.0（系统已有）
- gtk+-3.0/3.24.43（系统已有）

## 验证结果

```bash
# 插件文件检查
file /storage/Users/currentUser/usr/local/lib/zathura/libpdf-poppler.so
# ELF 64-bit LSB shared object, ARM aarch64

# pkg-config 验证
pkg-config --modversion zathura  # 0.5.14
pkg-config --modversion girara-gtk3  # 0.4.5
pkg-config --modversion poppler-glib  # 23.12.0

# 质量门禁
ohc-run.py verify-build zathura-pdf-poppler 0.3.4  # PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| zathura-pdf-poppler-0.3.4-ohos-aarch64.tar.gz | 27.4MB | 运行时包 |
| zathura-pdf-poppler-0.3.4-ohos-aarch64-debug.tar.gz | 24.5MB | 调试符号包 |

## 注意事项

- zathura-pdf-poppler 是 zathura 插件，不是独立可执行程序，G2 功能验证无二进制可执行文件
- 需先安装 girara-gtk3 和 zathura 才能编译此插件
- sqlite3.h 系统头文件被精简，缺少部分 API（如 sqlite3_mprintf），其他依赖 zathura 的软件编译时也可能遇到此问题
- pwmt.org 项目已改用日期版本号（如 2026.05.10），0.3.4 是最后一个数字版本号
---

**编译结束**: 2026-06-02 10:51
**最终状态**: built
