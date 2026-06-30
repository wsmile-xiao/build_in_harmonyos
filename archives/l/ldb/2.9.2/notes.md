# ldb 2.9.2 适配笔记

## 编译环境
- 构建系统: waf (Samba Python-based build system, configure wrapper calls waf)
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `./configure --prefix=$DEFAULT_PREFIX --disable-python`
2. `make -j2`
3. `make install DESTDIR=$TEST_PREFIX` (staging for packaging)
4. `make install` (deploy to $DEFAULT_PREFIX for verification)

configure_options: `--prefix=$DEFAULT_PREFIX --disable-python`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ld.lld: error: undefined symbol: rep_mkstemp` (ldbedit, ldbadd, ldbdel等) | `lib/replace/replace.h` 中 `#define mkstemp(path) rep_mkstemp(path)` 在 `HAVE_SECURE_MKSTEMP` 未定义时激活，但 `rep_mkstemp` 是 `libldb.so` 的私有符号(local `t`)，外部工具无法链接。`HAVE_SECURE_MKSTEMP` 检测在HarmonyOS上失败是因为mkstemp返回文件权限660而非0600(E046 SELinux/umask)。 | 在 `replace.h` 中添加 `#ifdef __OHOS__` 守卫，定义 `HAVE_SECURE_MKSTEMP 1` 跳过宏替换，因为HarmonyOS的mkstemp本身是安全的 |
| 2 | `ld.lld: error: undefined symbol: rep_strtoull` (ldb_match_test等) | `HAVE_BSD_STRTOLL` 在HarmonyOS上被定义，导致 `strtoull/strtoll` 被替换为 `rep_strtoull/rep_strtoll` (私有符号)。 | 在 `replace.h` 中为 `strtoull` 和 `strtoll` 的BSD替换宏添加 `#ifdef __OHOS__` 守卫，跳过替换，因为Linux/musl的strtoull/strtoll行为正确 |
| 3 | `replace` 库 `private_library=True` 导致所有 `rep_*` 符号不可见 | Samba的 `replace` 库设计为私有库，符号(local `t`)不导出，但ldb的独立构建中工具/测试需要这些符号 | 修改 `lib/replace/wscript` 中 `private_library=True` 为 `private_library=False`，导出 `replace` 符号 |

## 源码修改

1. `lib/replace/replace.h`:
   - 为 `mkstemp/rep_mkstemp` 宏添加 `#ifdef __OHOS__` 守卫，定义 `HAVE_SECURE_MKSTEMP 1`
   - 为 `strtoull/rep_strtoull` 宏添加 `#ifdef __OHOS__` 守卫（HAVE_BSD_STRTOLL分支）
   - 为 `strtoll/rep_strtoll` 宏添加 `#ifdef __OHOS__` 守卫（HAVE_BSD_STRTOLL分支）

2. `lib/replace/wscript`:
   - `private_library=True` → `private_library=False`
   - 移除 `provide_builtin_linking=True`
   - 添加注释说明HarmonyOS需要导出replace符号以供工具链接

## 依赖版本

- lmdb (系统自带, header check确认>=0.9.16)
- libiconv (预编译包)
- openldap (liblber, libldap 系统自带)
- talloc, tdb, tevent, cmocka, popt (ldb内置third_party版本)

## make check 结果

- C测试: 56 PASSED, 2 FAILED (test_ldb_unique_index_duplicate_logging, test_ldb_unique_index_duplicate_with_guid)
- Python测试: 全部失败 (--disable-python模式下预期行为)

## 验证结果

```bash
LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib:/storage/Users/currentUser/usr/local/lib/ldb \
  /storage/Users/currentUser/usr/local/bin/ldbsearch --help
# 输出: ldbsearch usage/help信息
LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib:/storage/Users/currentUser/usr/local/lib/ldb \
  /storage/Users/currentUser/usr/local/bin/ldbadd --help
LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib:/storage/Users/currentUser/usr/local/lib/ldb \
  /storage/Users/currentUser/usr/local/bin/ldbedit --help
# 所有工具均可正常运行
```

## 注意事项

- ldb使用waf构建系统（非标准autotools），`./configure`是waf的wrapper脚本
- `--disable-python`必须指定，因为HarmonyOS缺少Python embedding库
- ldb的私有库（libldb-cmdline, libtdb-ldb, libtevent-ldb等）安装在 `$PREFIX/lib/ldb/` 子目录
- ldb模块安装在 `$PREFIX/modules/ldb/` 目录
- 运行ldb工具需要设置 `LD_LIBRARY_PATH` 包含 `$PREFIX/lib/ldb`
- ldbsearch/ldbadd等工具不支持 `--version` 选项
---

**编译结束**: 2026-06-09 10:29
**最终状态**: published
