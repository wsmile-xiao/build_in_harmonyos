# sqlite-rsync 3.51.3 适配笔记

## 编译环境
- 构建系统: custom（autosetup 不可用，手动编译；与上游 main.mk RSYNC_OPT 标志一致）
- 编译日期: 2026-06-05（conan 配方 2026-09-04 建立，2026-09-17 修复检视意见后复验）
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

由于 SQLite 完整源码包的 configure 依赖 autosetup，autosetup 在鸿蒙系统上因临时文件路径问题无法正常工作，采用手动编译方式：

1. **准备源码**：
   - 下载 SQLite amalgamation 版本（sqlite-amalgamation-3510300.zip）
   - 下载 SQLite src 版本（sqlite-src-3510300.zip），提取 tool/sqlite3_rsync.c

2. **应用补丁**：`patches/0001-backport-upstream-argv-hardening.patch`（上游 check-in c84d596b6da2 回补，详见下文）

3. **编译 SQLite 库**：
   ```bash
   clang -c -fPIC -O2 -DSQLITE_ENABLE_DBPAGE_VTAB -DSQLITE_THREADSAFE=0 -DSQLITE_OMIT_LOAD_EXTENSION -DSQLITE_OMIT_DEPRECATED sqlite3.c -o sqlite3.o
   ```
   ⚠️ `-DSQLITE_ENABLE_DBPAGE_VTAB` **必需**：sqlite3_rsync 的协议基于 sqlite_dbpage 虚拟表
   （`INSERT INTO sqlite_dbpage(...)` / `FROM sqlite_dbpage('main')`），缺此宏时同步必然运行时报
   `no such table: sqlite_dbpage`。编译标志与上游 main.mk 的 RSYNC_OPT 完全一致。

4. **编译 sqlite3_rsync 工具**：
   ```bash
   clang -c -fPIC -O2 -I sqlite-amalgamation-3510300 -DSQLITE_ENABLE_DBPAGE_VTAB -DSQLITE_THREADSAFE=0 -DSQLITE_OMIT_LOAD_EXTENSION -DSQLITE_OMIT_DEPRECATED sqlite3_rsync.c -o sqlite3_rsync.o
   clang sqlite3_rsync.o sqlite3.o -o sqlite3_rsync -lpthread -ldl -lm
   ```

5. **ELF 签名**：
   ```bash
   ohc-run.py sign-elf sqlite3_rsync
   ```
   （conanfile.py 的 package() 中通过 binary-sign-tool 自动执行）

6. **安装和打包**：
   - conan create 全流程验证（含 test_package 功能测试）

## 补丁说明

### 0001-backport-upstream-argv-hardening.patch

上游 check-in `c84d596b6da2`（2026-05-26，晚于 3.51.3 release）的回补：

1. **main() argv 解析越界读修复**：原代码 `if( z[i]=='-' )` 中 `z` 指向当前参数（`argv[i]`，可能已跳过 `--` 前缀），`i` 是 argv 循环下标，`z[i]` 实际是 `argv[i][i]`——检测"参数第 i 个字符是否为 '-'"而非"参数是否以 '-' 开头"。后果：短参数越界读（未定义行为）、未知选项被当作数据库路径、含 '-' 文件名被误报。修复为 `z[0]=='-'`。
2. **ssh 命令构造加固**：origin/replica 参数的 `append_escaped_arg` 标志 0→1，防止远程路径中的 shell 元字符注入。

上游引用：
- https://sqlite.org/src/info/c84d596b6da22061627282d444913c88dc2f9bd82e86957183f7e732f2713b33
- https://github.com/sqlite/sqlite/commit/ce2f503c1c3b

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败（Permission denied） | unzip 解压后 autosetup-find-tclsh 缺少执行权限 | `chmod +x autosetup-find-tclsh configure` |
| 2 | configure 失败（ccache 问题） | autosetup 默认使用 ccache | 设置 `CCACHE=none` 禁用 ccache |
| 3 | configure 失败（stdlib.h not found） | autosetup 临时文件创建失败（/tmp 只读） | 采用手动编译方式，使用 amalgamation 版本 |
| 4 | 源码下载速度慢 | sqlite.org 服务器连接慢（10KB/s） | 耗时约 22 分钟，等待下载完成 |
| 5 | 同步功能运行时报 `no such table: sqlite_dbpage` | 编译时未启用 `SQLITE_ENABLE_DBPAGE_VTAB`（AI 检视意见指出） | 补齐上游 main.mk RSYNC_OPT 全部 4 个 -D 宏 |
| 6 | argv 解析 `z[i]=='-'` 越界读/误判 | 上游 3.51.3 代码缺陷（AI 检视意见指出） | 回补上游 c84d596b6da2 修复（补丁 0001） |

## 源码修改

- `patches/0001-backport-upstream-argv-hardening.patch`（上游修复回补，见上节）
- 其余源码未修改，sqlite3_rsync.c 可直接编译

## 依赖版本

- clang: 15.0.4
- SQLite: 3.51.3（amalgamation 版本）
- 无外部依赖（sqlite3 内嵌）

## 上游测试清点（R51 三步法）

- 上游 main.mk 无 sqlite3_rsync 专用测试目标（grep rsync main.mk 无 test/check 条目）；该工具上游验证方式即实际运行（sqlite.org/rsync.html）
- 实测环境：HarmonyOS PC（aarch64，本机）+ CI（build_and_test.sh L1）

## 验证结果

```bash
$ sqlite3_rsync --version
2026-03-13 10:38:09 737ae4a34738ffa0c3ff7f9bb18df914dd1cad163f28fd6b6e114a344fe6d618

$ sqlite3_rsync src.db dst.db && python3 -c "...assert count(*)..."
replica verified: 100 rows, spot-check OK

$ sqlite3_rsync -bogus-option src.db dst.db
unknown option: "-bogus-option". Use --help for more detail.   # exit 1（补丁回归验证）
```

test_package（test_sqlite_rsync.sh）为 fail-able 功能测试：--version 执行 + 本地同步
round-trip（含 /bin/sh 子进程派生路径）+ 副本数据断言（行数 + 抽样行）+ argv 加固回归。
任何一步失败即退出非零，无 WARN 降级。

## 注意事项

1. **临时文件路径问题**：autosetup 在鸿蒙系统上无法正常工作，因为 `/tmp` 是只读文件系统。手动编译是替代方案。
2. **ccache 禁用**：如果使用 autosetup，需要设置 `CCACHE=none` 环境变量。
3. **手动编译依赖**：需要同时下载 amalgamation 版本（sqlite3.c/sqlite3.h）和 src 版本（tool/sqlite3_rsync.c）。
4. **SQLITE_ENABLE_DBPAGE_VTAB 必需**：见问题 #5，缺宏时工具可编译但同步功能全损。
5. **本地同步实测可用**：此前"mksh 无法 exec ELF 子进程"的判断有误（真正缺的是 DBPAGE 宏）；
   已签名的 sqlite3_rsync 在 OHOS 上本地 round-trip 正常。
---

**编译结束**: 2026-09-17 12:01
**最终状态**: built
