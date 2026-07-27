# sqlite 3.53.3 适配笔记

## 编译环境
- 构建系统: manual (autosetup configure fails on HMDFS)
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4 / llvm-ar
- 状态: built

## 编译步骤

由于 HMDFS 文件系统限制，autosetup 的 configure 脚本无法正常运行（jimsh0 TCL 解释器无法 exec 子进程）。
采用手动 clang 编译，等效于 Makefile.fallback 方式：

1. 修改 autosetup/autosetup-config.guess 和 autosetup-config.sub 支持 HarmonyOS/OHOS
2. 手动编译:
   - clang -c sqlite3.c -o sqlite3.o (with SQLITE_ENABLE_RTREE, FTS5, etc.)
   - clang -o sqlite3 shell.c sqlite3.o
   - llvm-ar rcs libsqlite3.a sqlite3.o

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autosetup configure 失败 | jimsh0 bootstrap TCL 无法在 HMDFS 上 exec 子进程 | 使用手动 clang 编译替代 |
| 2 | config.guess 无法识别系统 | 不支持 HarmonyOS | 添加 HarmonyOS case 分支, 返回 aarch64-unknown-linux-ohos |
| 3 | config.sub 验证失败 | 不识别 ohos 操作系统 | 添加 ohos-linux 到 basic_os 映射 |

## 源码修改

- autosetup/autosetup-config.guess: 添加 __OHOS__ 宏检测和 HarmonyOS 平台识别
- autosetup/autosetup-config.sub: 添加 ohos-linux 操作系统支持

## 依赖版本

无外部依赖（自包含 amalgamation 源码）

## 验证结果

```bash
$ sqlite3 --version
3.53.3 2026-06-26 20:14:12 d4c0e51e4aeb96955b99185ab9cde75c339e2c29c3f3f12428d364a10d782c62 (64-bit)

$ sqlite3 :memory: "CREATE TABLE test (id INTEGER, name TEXT); INSERT INTO test VALUES (1, 'hello'); SELECT * FROM test;"
1|hello

$ sqlite3 :memory: "CREATE VIRTUAL TABLE ft USING fts5(content); INSERT INTO ft VALUES('test content here'); SELECT * FROM ft WHERE ft MATCH 'test';"
test content here

$ sqlite3 :memory: "CREATE VIRTUAL TABLE rt USING rtree(id, minx, maxx, miny, maxy); INSERT INTO rt VALUES(1,0,1,0,1); SELECT * FROM rt;"
1|0.0|1.0|0.0|1.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sqlite3 | 1.7M | CLI 可执行文件 |
| libsqlite3.a | 1.8M | 静态库 |
| sqlite3.h | 691K | 头文件 |
| sqlite3ext.h | 39K | 扩展头文件 |

## 注意事项

1. 使用手动 clang 编译，未生成共享库(.so)，仅生成静态库和可执行文件
2. 编译选项启用了 RTREE、FTS5、COLUMN_METADATA、UNLOCK_NOTIFY、SECURE_DELETE、DBSTAT_VTAB
3. 与 sqlite3 包区别：本包名为 sqlite，cpp_info.libs=["sqlite3"]
---

**编译结束**: 2026-07-15 22:21
**最终状态**: built
