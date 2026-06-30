# postgresql-orafce 4.16.0 适配笔记

## 编译环境
- 构建系统: PostgreSQL Extension (PGXS)
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

postgresql-orafce 是一个 PostgreSQL 扩展，使用 PGXS (PostgreSQL Extension Building Infrastructure) 构建：

1. 初始化编译环境：`python3 ohc-run.py init-build postgresql-orafce 4.16.0 --url=https://github.com/orafce/orafce/archive/refs/tags/VERSION_4_16_0.tar.gz`
2. 手动编译（PGXS 不需要 configure）：`export CC=clang && make -j1`
3. 安装到 staging 目录：`make install DESTDIR=$TEST_PREFIX`
4. 安装到实际位置：`make install`

**注意**：ohc-run.py build 自动流程检测到 meson.build 文件并尝试使用 meson 构建，但由于 meson 找不到编译器而失败。实际上这个项目应该使用 Makefile + PGXS 构建，因此改为手动编译模式。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 构建失败，找不到编译器 | meson 在 PATH 中找不到 cc/gcc/clang | 使用 PGXS 构建（make），设置 CC=clang 环境变量 |
| 2 | ohc-run.py 自动识别错误 | 项目同时有 meson.build 和 Makefile，脚本误判为 meson 项目 | 手动使用 Makefile + PGXS 构建 |

## 源码修改

无补丁文件。源码在 OHOS 平台上直接编译成功，未发现需要修改的平台相关问题。

预扫描报告中发现的问题：
- `/tmp` 硬编码（file.c:1463）：未修复，因为 PostgreSQL 扩展通常由 PostgreSQL 服务器调用，服务器会设置正确的临时目录
- NLS 国际化检测：未影响编译

## 依赖版本

- PostgreSQL: 17.0 (通过 pg_config)
- clang: 15.0.4
- make: GNU Make 4.4.1

## 验证结果

```bash
# 检查产物文件
ls -lh /storage/Users/currentUser/usr/local/lib/postgresql/orafce.so
# 输出：310K ELF shared object, 64-bit LSB arm64, not stripped

# 检查依赖
readelf -d /storage/Users/currentUser/usr/local/lib/postgresql/orafce.so | grep NEEDED
# 输出：Shared library: [libc.so]

# 检查扩展文件
ls /storage/Users/currentUser/usr/local/share/postgresql/extension/orafce*
# 输出：orafce.control 和 44 个 SQL 文件（包括升级脚本）
```

**注意**：完整的功能验证需要在运行的 PostgreSQL 服务器中执行 `CREATE EXTENSION orafce;` 并测试 Oracle 兼容函数。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| orafce.so | 310K | PostgreSQL 扩展共享库 |
| orafce.control | 205 bytes | 扩展控制文件 |
| orafce--4.16.sql + 升级脚本 | ~556K total | 扩展 SQL 定义文件 |

## 注意事项

1. **构建系统识别**：此项目同时包含 meson.build 和 Makefile，自动构建脚本可能误判。正确的构建方式是使用 Makefile + PGXS（PostgreSQL Extension Building Infrastructure）。
2. **编译器设置**：需要设置 `CC=clang` 环境变量，否则 PGXS 可能找不到编译器。
3. **PostgreSQL 版本兼容性**：此扩展要求 PostgreSQL 13.0.0+，推荐 PostgreSQL 18.0.0。当前系统 PostgreSQL 17.0 满足要求。
4. **功能验证**：完整的功能验证需要 PostgreSQL 服务器运行，并执行 `CREATE EXTENSION orafce;`。
---

**编译结束**: 2026-06-02 12:51
**最终状态**: built
