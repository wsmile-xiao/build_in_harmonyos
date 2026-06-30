# postgresql-uint 0 适配笔记

## 编译环境
- 构建系统: PGXS (makefile)
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 GitHub (adjust/pguint) 克隆源码，打包为 tar.gz 供 init-build 使用
2. 运行 `python3 generate.py 16` 生成 operators.c, operators.sql, test/sql/operators.sql
3. `make USE_PGXS=1 PG_CONFIG=$DEFAULT_PREFIX/bin/pg_config` 编译
4. `make install DESTDIR=$TEST_PREFIX` staging 安装
5. `make install` 本地安装

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pguint 源码无法从 Savannah 下载 | Savannah 无 pguint 托管 | 从 GitHub (adjust/pguint) git clone 下载 |
| 2 | generate.py 报 IndexError | 缺少 PG 版本参数 | 传入 `python3 generate.py 16` |
| 3 | pguint 版本号为 0 | uint.control default_version=0 | 正常，这是 pguint 项目的设计 |

## 源码修改

无源码修改。

## 依赖版本

- PostgreSQL 16.14
- clang 15.0.4

## 验证结果

```bash
# Staging 安装产物
ls ~/tmp/test-install-postgresql-uint-0/storage/Users/currentUser/usr/local/lib/postgresql/uint.so
# uint.so
# 质量门禁: PASS
# 打包产物: postgresql-uint-0-ohos-aarch64.tar.gz (472KB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| postgresql-uint-0-ohos-aarch64.tar.gz | 472KB | 预编译包 |

## 注意事项

- pguint 版本号为 0，与常规软件不同
- 需要先运行 generate.py 生成操作符代码才能编译
- 此版本无 OpenSSL 依赖

---

**编译结束**: 2026-06-09
**最终状态**: built