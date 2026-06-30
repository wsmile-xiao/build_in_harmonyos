# pgexportdoc 0.1.4 — 适配笔记

## 基本信息

- **软件**: pgexportdoc
- **版本**: 0.1.4
- **源码**: https://github.com/okbob/pgexportdoc/archive/refs/tags/0.1.4.tar.gz
- **构建系统**: PGXS (PostgreSQL Extension Building System)
- **编译日期**: 2026-06-09

## 编译过程

### 构建系统识别
- pgexportdoc 使用 PGXS 构建系统（PostgreSQL Extension Building System）
- 无 configure 脚本，Makefile 通过 `pg_config --pgxs` 定位 PGXS makefile
- 编译直接使用 `make`，链接 libpq、libpgcommon、libpgport

### 编译步骤
1. `make` — 编译成功，无错误
2. `make install DESTDIR=$TEST_PREFIX` — 安装到 staging 目录成功
3. `./pgexportdoc -V` — 二进制验证通过，输出 "pgexportdoc (PostgreSQL) 17.10"

### 编译依赖
- PostgreSQL 17.10（提供 pg_config、libpq、pgcommon、pgport）
- libpq.so.5（动态链接）
- clang 编译器

### make check 结果
- PGXS 项目不支持 `make check`，需要运行中的 PostgreSQL 服务器
- 使用 `./pgexportdoc -V` 替代验证
- 结果: PASS

## 源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| 无 | 编译无需修改源码 | - | 无需补丁 |

## 安装产物

- `$DEFAULT_PREFIX/bin/pgexportdoc` — 主二进制文件
- 动态链接: libpq.so.5, libc.so

## 注意事项

1. pgexportdoc 是 PostgreSQL 客户端工具，依赖 libpq
2. 运行时需要 PostgreSQL 服务器连接
3. 版本号输出为 PostgreSQL 版本（17.10），而非 pgexportdoc 自身版本
4. 编译使用了已安装的 PostgreSQL 17.10 开发文件
---

**编译结束**: 2026-06-09 20:13
**最终状态**: built
