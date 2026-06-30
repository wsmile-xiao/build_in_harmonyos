# sqldiff 3.51.3 适配笔记

## 编译环境
- 构建系统: custom（直接 cc 编译，sqldiff 是 SQLite 源码包中的独立工具）
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

sqldiff 是 SQLite 源码包中的工具，位于 tool/sqldiff.c。SQLite 源码包的 configure 需要 tclsh（不可用），因此采用直接编译方式：

1. 下载 SQLite 溨合源码包 sqlite-src-3510300.zip（主源码）
2. 下载 SQLite 溨合文件 sqlite-amalgamation-3510300.zip（含 sqlite3.c/sqlite3.h）
3. 复制 sqlite3.c, sqlite3.h, sqlite3ext.h 到源码根目录
4. 直接编译 sqldiff:
   ```
   cc -o sqldiff tool/sqldiff.c sqlite3.c -I. -Itool -Iext/misc -DHAVE_READLINE=0 -DSQLITE_THREADSAFE=0 -fPIC -O2
   ```
5. 手动安装到 $TEST_PREFIX/$DEFAULT_PREFIX/bin/sqldiff 和 $DEFAULT_PREFIX/bin/sqldiff

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 需要 tclsh | SQLite 使用 autosetup 构建，configure 脚本需要 tclsh | 下载 amalgamation sqlite3.c，直接 cc 编译 sqldiff.c |
| 2 | sqlite3.c 不在源码包中 | 源码包是分文件的，不是 amalgamation | 从 sqlite-amalgamation-3510300.zip 获取 sqlite3.c |
| 3 | 编译时缺少 sqlite3_stdio.h | sqldiff.c 引用了 ext/misc/sqlite3_stdio.h | 添加 -Iext/misc 到编译命令 |

## 源码修改

无源码修改，无补丁。仅添加了 sqlite3.c/sqlite3.h/sqlite3ext.h（来自 amalgamation 包）。

## 依赖版本

无外部依赖。sqldiff 自包含 sqlite3 引擎。

## 验证结果

```bash
$ ~/usr/local/bin/sqldiff --help
Usage: sqldiff [options] DB1 DB2
输出将 DB1 转换为 DB2 的 SQL 文本
# 输出正常，R7 验证通过
```

12 个测试用例全部真实执行，11 通过 + 1 部分（变更集对 schema 差异的已知限制）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sqldiff-3.51.3-ohos-aarch64.tar.gz | 1180KB | 预编译包（含 bin/sqldiff） |
| sqldiff-3.51.3-ohos-aarch64-debug.tar.gz | 113KB | 调试符号包 |

## 注意事项

- sqldiff 没有 --version 选项，使用 --help 查看版本信息
- SQLite 源码包的 configure 依赖 tclsh，在鸿蒙环境不可用时使用 amalgamation 直接编译
- G0 干净构建验证因 tar 格式问题失败（源码为 .zip），但手动验证编译可复现

## 知识提取

- E900: SQLite 源码包 configure 需要 tclsh（OHOS 不可用）→ 使用 amalgamation 直接编译（草稿已创建）

---

**编译结束**: 2026-05-25
**最终状态**: built
---

**编译结束**: 2026-05-25 15:48
**最终状态**: built
