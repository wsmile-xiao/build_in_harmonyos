# sqlite-rsync

## 软件简介

sqlite-rsync 是 SQLite 官方提供的远程数据库同步工具，类似于 `rsync`，但专门针对 SQLite 数据库文件优化。

**功能特点**:
- 增量同步：只传输差异部分，节省带宽
- WAL 模式支持：支持 WAL（Write-Ahead Logging）模式数据库
- 远程同步：通过 SSH 实现本地与远程数据库同步
- 安全可靠：保持数据库一致性，支持在线同步

**用途**:
- 远程备份 SQLite 数据库
- 数据库镜像和复制
- 低带宽环境下的数据库同步

## 版本信息

| 版本 | 状态 | 发布日期 | 备注 |
|------|------|---------|------|
| 3.51.3 | built | 2026-06-05 | 当前版本 |

## 依赖关系

- **编译依赖**: 无外部依赖（内嵌 SQLite 库）
- **运行依赖**: libc.so
- **可选依赖**: SSH（用于远程同步）

## 构建系统

- **类型**: autotools（autosetup）
- **编译器**: clang 15.0.4
- **特殊说明**: autosetup 在鸿蒙系统上因 `/tmp` 只读问题无法工作，采用手动编译方式

## 使用方法

### 基本语法

```bash
sqlite3_rsync ORIGIN REPLICA [OPTIONS]
```

**参数说明**:
- `ORIGIN`: 源数据库路径（本地路径或 `USER@HOST:PATH`）
- `REPLICA`: 目标数据库路径（本地路径或 `USER@HOST:PATH`）

### 常用选项

```bash
--version          显示版本信息
--help             显示帮助信息
--exe PATH         远程端 sqlite3_rsync 程序路径
--ssh PATH         SSH 程序路径
-v                 详细输出（多个 v 增加详细度）
--wal-only         仅在 WAL 模式下同步
--protocol N       使用协议版本 N
```

### 使用示例

#### 1. 本地到远程同步

```bash
sqlite3_rsync /local/path/db.sqlite user@remote:/path/db.sqlite
```

#### 2. 远程到本地同步

```bash
sqlite3_rsync user@remote:/path/db.sqlite /local/path/db.sqlite
```

#### 3. 详细模式同步

```bash
sqlite3_rsync -vvv /local/db.sqlite user@remote:/remote/db.sqlite
```

#### 4. WAL 模式强制同步

```bash
sqlite3_rsync --wal-only /local/db.sqlite user@remote:/remote/db.sqlite
```

## 注意事项

1. **SSH 要求**: 远程同步需要 SSH 服务可用
2. **数据库一致性**: 同步过程中数据库可能被锁定
3. **WAL 模式**: `--wal-only` 要求两端数据库都在 WAL 模式
4. **带宽优化**: 增量同步显著减少传输数据量

## 相关工具

- **sqlite3**: SQLite 命令行工具
- **sqldiff**: SQLite 数据库差异工具
- **sqlite3_analyzer**: SQLite 数据库分析工具

## 参考资料

- [SQLite 官方文档](https://sqlite.org/sqlite3_rsync.html)
- [SQLite 源码](https://sqlite.org/download.html)

## 编译说明

### 鸿蒙系统编译特殊性

由于 autosetup 在鸿蒙系统上因 `/tmp` 只读文件系统问题无法正常工作，sqlite-rsync 采用手动编译方式：

**编译步骤**:
1. 下载 SQLite amalgamation 版本（sqlite3.c/sqlite3.h）
2. 下载 SQLite src 版本（提取 tool/sqlite3_rsync.c）
3. 手动编译 sqlite3.o
4. 手动编译 sqlite3_rsync.o
5. 链接生成 sqlite3_rsync 可执行文件
6. ELF 签名

**详细编译笔记**: 见 `3.51.3/notes.md`

---

**最后更新**: 2026-06-06