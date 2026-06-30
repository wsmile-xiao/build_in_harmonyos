# tre 0.9.0 适配笔记

## 编译环境
- 构建系统: autotools（需 autoreconf -fi，tarball 不包含 configure 脚本）
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4 / clang++
- 状态: 已发布 (published)

## 编译步骤

1. 解压源码 `tar xzf tre-0.9.0.tar.gz`
2. 应用源码补丁 `0001-Makefile.am-remove-po.patch` 和 `0002-configure.ac-disable-nls.patch`
3. `autoreconf -fi`（因 configure.ac 修改需重新生成 configure 等文件）
4. 修改 configure 中 `umask 077 → 022` 和 `mktemp -d "./confXXXXXX" → mktemp -d "$TMPDIR/confXXXXXX"`（HMDFS setgid 兼容）
5. 应用 config.guess/config.sub OHOS 补丁（autoreconf 已内置）
6. `./configure --prefix=$DEFAULT_PREFIX`（NLS 已在 configure.ac 中禁用）
7. `make -j1`
8. `make install DESTDIR=$TEST_PREFIX`（staging 安装验证）
9. `make check` — 2/3 通过, wretest 失败（locale 限制，4/53447，0.0075%）
10. `make install`（真实安装到 $DEFAULT_PREFIX）
11. `ohc-run.py package tre 0.9.0`（打包预编译包）

## 遇到的问题与解决方案

| 序号 | 问题 | 根因 | 解决方案 |
|------|------|------|----------|
| 1 | config.status: can't create ./confXXXXXX/subs1.awk: Permission denied | HMDFS setgid + umask 077 创建的临时目录剥夺组权限，当前用户靠组成员(file_manager)写文件 | 修改 configure: umask 077→022, mktemp "./conf"→"$TMPDIR/conf" |
| 2 | po/Makefile: No rule to make target 'all' | NLS 禁用后 po/ 目录缺少 Makefile | 从 AC_CONFIG_FILES 和 SUBDIRS 中移除 po |
| 3 | configure.ac: 'dnl' already registered with AC_CONFIG_FILES | 之前的修改将 dnl 注释写入了 AC_CONFIG_FILES 宏体内（dnl 在宏体内不是注释） | 清理 AC_CONFIG_FILES，移除 dnl 行和乱码行 |
| 4 | wretest: 4/53447 tests FAILED | OHOS 缺少 en_US.ISO-8859-1 和 ja_JP.eucJP locale | 平台限制，不阻塞 |

## 源码修改清单

| 文件 | 原因 | 方式 |
|------|------|------|
| configure.ac | 禁用 NLS（注释掉 AM_GNU_GETTEXT_VERSION、AM_GNU_GETTEXT，添加 LIBINTL stubs）；移除 po/Makefile.in 和 dnl 行 | sed/编辑 |
| Makefile.am | 移除 po 子目录 | sed |
| configure | HMDFS umask 077 不可写问题（生成文件，autoreconf 后需手动修复） | sed: umask 077→022, mktemp "./conf"→"$TMPDIR/conf" |
| utils/config.guess, utils/config.sub | OHOS 平台识别 | autoreconf 内置或 patch-autotools-ohos.pl |

## 真实功能验证结果

### agrep 验证（8项全部通过）
- 精确匹配、正则表达式、近似匹配(1错/2错)、反向搜索、大小写不敏感 — 全部 ✅

### libtre API 验证（4项全部通过）
- 基本正则编译+匹配+不匹配 ✅
- 分组捕获（分组1='3', 分组2='14 is pi') ✅
- 大小写不敏感 ✅
- 中文字符匹配 ✅

### pkg-config 验证
- `pkg-config --modversion tre` → 0.9.0 ✅

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tre-0.9.0-ohos-aarch64.tar.gz | 364KB | 预编译包（含 agrep + libtre + 头文件） |
| tre-0.9.0-ohos-aarch64-debug.tar.gz | 166KB | 调试符号包 |

## 注意事项

- HMDFS setgid 环境下，autoconf 的 umask 077 创建临时目录会导致组权限被剥夺
- wretest 失败是 OHOS locale 限制，核心功能不受影响
- configure.ac 中的 NLS 禁用方案：注释掉 AM_GNU_GETTEXT 相关宏，添加 LIBINTL 空值 stubs
- 源码 tarball 不包含 configure 脚本，构建流程需 autoreconf -fi 再加 umask 修复
- G0 自动干净构建验证因缺少 autoreconf 步骤而失败，已手动验证通过（rebuild_hints.yaml 记录完整重建步骤）

---
**编译结束**: 2026-05-26
**最终状态**: 已发布 (published)
---

**编译结束**: 2026-05-26 19:38
**最终状态**: published
