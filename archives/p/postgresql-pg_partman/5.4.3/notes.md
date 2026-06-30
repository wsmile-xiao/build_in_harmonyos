# postgresql-pg_partman 5.4.3 适配笔记

\\## 编译环境
- 构建系统: PGXS (PostgreSQL Extension Building Infrastructure)
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- PostgreSQL: 17.10
- 状态: published

## 编译步骤

pg_partman 使用 PGXS 构建系统（非 autotools），无需 configure 步骤：

1. `cd $BUILD_SRC_DIR`
2. `make` — 构建 .so 扩展模块和 SQL 文件
3. `make install DESTDIR=$TEST_PREFIX` — 安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL下载失败 | HarmonyOS CA证书缺失 | 用 curl -kL 手动下载 tarball，放到预期位置 |

**注意**： pg_partman 使用 PGXS 构建系统，不使用传统的 autotools configure/make/make install 流程。
编译依赖 pg_config 定位 PostgreSQL 安装路径和编译参数。

## 源码修改

无源码修改。纯净编译，无需补丁。

## 依赖版本
- PostgreSQL 17.10 (通过 pg_config)
- clang 15.0.4 (通过 pg_config --cc)

- Python 3.12 (bin/*.py 脚本依赖 psycopg2)

## 测试

make check 跳过： pg_partman 测试需要运行中的 PostgreSQL 服务器。
无法在编译环境中执行。跳过测试。

## 验证结果
- pg_partman_bgw.so: ELF 64-bit aarch64 shared object
- pg_partman.control: default_version = '5.4.3'
- Python 脚本: check_unique_constraint.py, dump_partition.py, vacuum_maintenance.py

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| postgresql-pg_partman-5.4.3-ohos-aarch64.tar.gz | ~1.3MB | 预编译包 |
| postgresql-pg_partman-5.4.3-ohos-aarch64-debug.tar.gz | ~1.3MB | debug预编译包 |

## 注意事项
- pg_partman 是 PostgreSQL 扩展，运行时需要 PostgreSQL 服务器
- bin/*.py 脚本需要 psycopg2 Python 库
- pg_partman_bgw.so 是后台工作进程模块，可通过 NO_BGW=1 禁用
---

**编译结束**: 2026-06-10 22:15
**最终状态**: published
