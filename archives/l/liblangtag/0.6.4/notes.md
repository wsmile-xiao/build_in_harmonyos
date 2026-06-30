# liblangtag 0.6.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 源码下载：从 bitbucket 下载 tarball
2. 解压后需要运行 `autoreconf -fi` 生成 configure 脚本（原始 tarball 没有 configure）
3. 从 automake 安装目录复制辅助文件：config.guess、config.sub、install-sh、missing、compile、ar-lib
4. 创建空的 gtk-doc.make 文件（automake 需要）
5. 运行 configure：`./configure --prefix=$DEFAULT_PREFIX --disable-test`
6. 运行 make：`make -j4`
7. staging 安装：`make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 脚本不存在 | tarball 只包含 configure.ac | 运行 autoreconf -fi |
| 2 | 缺少辅助文件 | autoreconf 没有生成 | 从 automake share 目录复制 |
| 3 | gtk-doc.make 不存在 | automake 需要 | 创建空文件 |
| 4 | HMDFS umask 问题 | SELinux 权限限制 | `sed -i 's/umask 077/umask 022/g' configure` |
| 5 | 缺少 check 库 | 单元测试框架 | 使用 --disable-test 禁用 |
| 6 | GOBJECT_INTROSPECTION_CHECK 未展开 | 缺少 m4 宏 | 注释掉宏调用，设置 enable_introspection=no |
| 7 | docs/Makefile.am EXTRA_DIST += 错误 | automake 语法错误 | 改为 EXTRA_DIST = |
| 8 | HAVE_INTROSPECTION 条件未定义 | 禁用 introspection 后缺少定义 | 在 configure.ac 添加 AM_CONDITIONAL |

## 源码修改

### 补丁 0001-configure.ac.patch
- 禁用 GOBJECT_INTROSPECTION_CHECK 宏调用
- 设置 enable_introspection=no
- 添加 AM_CONDITIONAL([HAVE_INTROSPECTION], [false])

### 补丁 0002-docs-Makefile.am.patch
- 修复 EXTRA_DIST += 语法错误
- 改为 EXTRA_DIST =

### hints/post-apply.sh
- 补丁应用后运行 autoreconf -fi
- 修复 HMDFS umask 问题

## 依赖版本

| 软件 | 版本 |
|------|------|
| libxml2 | 2.15.3 |
| glib | 2.88.0 |

## 验证结果

```bash
# 库文件已生成
ls /storage/Users/currentUser/test-install-liblangtag-0.6.4/storage/Users/currentUser/usr/local/lib/
# liblangtag.so.1.4.1 (219520 bytes)
# liblangtag.la
# liblangtag.so -> liblangtag.so.1.4.1
# liblangtag.so.1 -> liblangtag.so.1.4.1
```

## 交付物

编译成功，但尚未制作预编译包。需要：
1. 通过 G0 干净构建验证
2. 通过质量门禁
3. 运行 ohc-run.py package

## 注意事项

1. 此软件需要 autoreconf 来生成 configure 脚本
2. 必须使用 --disable-test 禁用单元测试（缺少 check 库）
3. 需要设置 PKG_CONFIG_PATH 让 pkg-config 找到 libxml2

---
**编译结束**: 2026-06-03 10:17
**最终状态**: built
---

**编译结束**: 2026-06-03 10:18
**最终状态**: built
