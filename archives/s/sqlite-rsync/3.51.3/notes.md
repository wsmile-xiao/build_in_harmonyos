# sqlite-rsync 3.51.3 适配笔记

## 编译环境
- 构建系统: autotools（autosetup）
- 编译日期: 2026-06-05
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

由于 SQLite 完整源码包的 configure 依赖 autosetup，autosetup 在鸿蒙系统上因临时文件路径问题无法正常工作，采用手动编译方式：

1. **准备源码**：
   - 下载 SQLite amalgamation 版本（sqlite-amalgamation-3510300.zip）
   - 下载 SQLite src 版本（sqlite-src-3510300.zip），提取 tool/sqlite3_rsync.c

2. **编译 SQLite 库**：
   ```bash
   clang -c -fPIC -O2 -DSQLITE_THREADSAFE=0 -DSQLITE_OMIT_LOAD_EXTENSION sqlite3.c -o sqlite3.o
   ```

3. **编译 sqlite3_rsync 工具**：
   ```bash
   clang -c -fPIC -O2 -I sqlite-amalgamation-3510300 -DSQLITE_THREADSAFE=0 -DSQLITE_OMIT_LOAD_EXTENSION sqlite3_rsync.c -o sqlite3_rsync.o
   clang sqlite3_rsync.o sqlite3.o -o sqlite3_rsync -lpthread -ldl -lm
   ```

4. **ELF 签名**：
   ```bash
   ohc-run.py sign-elf sqlite3_rsync
   ```

5. **安装和打包**：
   - 安装到 staging 目录：`$TEST_PREFIX/bin/sqlite3_rsync`
   - 质量门禁验证通过
   - 制作预编译包：sqlite-rsync-3.51.3-ohos-aarch64.tar.gz

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败（Permission denied） | unzip 解压后 autosetup-find-tclsh 缺少执行权限 | `chmod +x autosetup-find-tclsh configure` |
| 2 | configure 失败（ccache 问题） | autosetup 默认使用 ccache | 设置 `CCACHE=none` 禁用 ccache |
| 3 | configure 失败（stdlib.h not found） | autosetup 临时文件创建失败（/tmp 只读） | 采用手动编译方式，使用 amalgamation 版本 |
| 4 | 源码下载速度慢 | sqlite.org 服务器连接慢（10KB/s） | 耗时约 22 分钟，等待下载完成 |

## 源码修改

无补丁文件。sqlite3_rsync.c 可直接编译，无需修改。

## 依赖版本

- clang: 15.0.4
- SQLite: 3.51.3（amalgamation 版本）
- 无外部依赖（sqlite3 内嵌）

## 验证结果

```bash
$ sqlite3_rsync --version
2026-03-13 10:38:09 737ae4a34738ffa0c3ff7f9bb18df914dd1cad163f28fd6b6e114a344fe6d618
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sqlite-rsync-3.51.3-ohos-aarch64.tar.gz | 1180KB | 预编译包（包含 sqlite3_rsync 可执行文件） |

## 注意事项

1. **临时文件路径问题**：autosetup 在鸿蒙系统上无法正常工作，因为 `/tmp` 是只读文件系统。手动编译是替代方案。
2. **ccache 禁用**：如果使用 autosetup，需要设置 `CCACHE=none` 环境变量。
3. **手动编译依赖**：需要同时下载 amalgamation 版本（sqlite3.c/sqlite3.h）和 src 版本（tool/sqlite3_rsync.c）。

## 知识提取记录

### 问题1: autosetup 临时文件路径问题
- **分类**: L1 平台真理（所有使用 autosetup 的项目）
- **错误模式**: E-TMPDIR-001（未记录，建议添加）
- **方案**: 使用 amalgamation 版本 + 手动编译
- **影响**: 所有 SQLite 工具（sqlite3_analyzer, sqlite3_rsync 等）
---

**编译结束**: 2026-06-06 10:07
**最终状态**: published
