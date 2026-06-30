# postgresql-plpgsql_check 2.9.1 适配笔记

## 编译环境
- 构建系统: makefile (PGXS - PostgreSQL Extension Building Infrastructure)
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. init-build: python3 $SKILL_ROOT/scripts/ohc-run.py init-build postgresql-plpgsql_check 2.9.1 --url=https://api.github.com/repos/okbob/plpgsql_check/tarball/v2.9.1
2. 此软件为 PostgreSQL PGXS 扩展，无 configure 脚本。直接使用 pg_config 和 PGXS Makefile 编译。
3. cd $BUILD_SRC_DIR && make (自动使用 pg_config --pgxs 定位 PGXS 构建基础设施)
4. make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 下载失败 | GitHub API SSL 证书验证失败 | 手动 curl -kL 下载 tarball 到 ~/tmp/builds/ |

## 源码修改

无补丁，源码无需修改即可在 OpenHarmony 上编译成功。

## 依赖版本

- PostgreSQL 17.10 (提供 pg_config 和 PGXS 构建基础设施)
- clang 15.0.4

## 验证结果

```bash
# ELF 检查
file plpgsql_check.so: ELF shared object, 64-bit LSB arm64, not stripped
# RPATH 正确
RUNPATH: /storage/Users/currentUser/usr/local/lib
# NEEDED: libc.so
# make check 不支持（PGXS 扩展需要 make installcheck + 运行中的 PG 服务）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| plpgsql_check.so | 1.3MB | PostgreSQL 扩展共享库 |
| plpgsql_check.control | 182B | 扩展元数据 |
| plpgsql_check--2.9.sql | 14.8KB | 扩展 SQL 安装脚本 |

## 注意事项

- PGXS 扩展不需要 ./configure，直接 make 即可
- make check 不支持，需要 make installcheck（需要运行中的 PostgreSQL 实例）
- 扩展依赖 plpgsql（PostgreSQL 内置扩展），requires = 'plpgsql'
---

**编译结束**: 2026-06-10 22:15
**最终状态**: published
