# hypopg 1.4.2 适配笔记

## 编译环境
- 构建系统: PGXS (PostgreSQL Extension Building Infrastructure)
- 编译日期: 2026-06-13
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: published

## 编译步骤

hypopg 是 PostgreSQL 扩展，使用 PGXS 构建系统（通过 pg_config 获取编译参数），而非传统 autotools configure。

1. **无 configure 步骤** — PGXS 扩展直接使用 `make` 编译，通过 pg_config 获取所有路径和编译参数
2. `make pkgincludedir=/storage/Users/currentUser/usr/local/include` — 编译 .so 文件
3. `make install DESTDIR=$TEST_PREFIX pkgincludedir=/storage/Users/currentUser/usr/local/include` — staging 安装

注意：需要传递 `pkgincludedir` 参数，因为本地 pg_config 不支持 `--pkgincludedir` 选项，导致 Makefile.global 中该变量解析失败。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make 时 clang 报错 "unsupported option '--pkgincludedir/server'" | pg_config 不支持 `--pkgincludedir` 选项，Makefile.global 解析 `pkgincludedir` 变量时得到错误字符串 | 1) 创建 symlink: `$DEFAULT_PREFIX/include/server` → postgresql src/include; 2) make 时传递 `pkgincludedir=$DEFAULT_PREFIX/include` |
| 2 | SSL 下载超时 | GitHub 网络不稳定 | 手动 curl 下载源码包到 `~/tmp/builds/` 目录，init-build 检测到已存在跳过下载 |

## 源码修改

无需修改源码，仅在编译时传递 pkgincludedir 参数。

## 依赖版本

- PostgreSQL 16.4 (pg_config, server headers, pgxs.mk)
- clang 15.0.4

## 验证结果

```bash
# 编译产物: hypopg.so (ELF64 arm64 shared object, 59712 bytes)
file hypopg.so → ELF shared object, 64-bit LSB arm64, not stripped
# 安装产物: lib/hypopg.so + share/extension/hypopg.control + share/extension/hypopg--*.sql
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| hypopg.so | 59712 bytes | PostgreSQL 扩展共享库 |
| hypopg.control | 148 bytes | 扩展控制文件 |
| hypopg--*.sql | 7个文件 | SQL 迁移脚本 |

## 注意事项

- hypopg 是 PostgreSQL 扩展，不是独立可执行程序，无法通过 `--version` 验证
- 需要运行 PostgreSQL 服务并通过 `CREATE EXTENSION hypopg` 验证
- pg_config 缺少 `--pkgincludedir` 支持是 PostgreSQL 16.4 在鸿蒙平台的已知问题
- 编译时必须传递 `pkgincludedir=$DEFAULT_PREFIX/include` 参数
---

**编译结束**: 2026-06-13 04:20
**最终状态**: published
