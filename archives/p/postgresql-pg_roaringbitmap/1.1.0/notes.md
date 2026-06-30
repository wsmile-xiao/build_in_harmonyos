# postgresql-pg_roaringbitmap 1.1.0 适配笔记

## 编译环境
- 构建系统: pgxs (PostgreSQL Extension Building Infrastructure)
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: published

## 编译步骤

pg_roaringbitmap 是 PostgreSQL Roaring Bitmap 扩展，使用 PGXS 构建系统（非传统 autotools/configure）。

1. **无 configure 步骤** — PGXS 扩展直接使用 `make`，通过 `pg_config --pgxs` 获取构建规则
2. `make` — 编译 4 个 .c 文件为 .o，链接为 roaringbitmap.so
3. `make install DESTDIR=$TEST_PREFIX` — staging 安装
4. Staging 验证通过
5. `ohc-run.py package` — 打包预编译包
6. `make install` — 本地安装到 ~/usr/local

### 关键信息
- CRoaring 库已内嵌在源码中（roaring.c 1MB+ / roaring.h），无需外部 CRoaring 依赖
- PostgreSQL 17.10 已预装，pg_config 可用
- 编译器使用 clang，PGXS 自动从 pg_config 获取编译参数

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书下载失败 | Python SSL 验证失败 | 手动 curl 下载 tarball 到 ~/tmp/builds/ |
| 2 | G4 verify 缺少 build_system | manifest 未包含顶层 build_system 字段 | 添加 build_system: pgxs 到 manifest.yaml |

## 源码修改

无源码修改，编译零补丁。PGXS 扩展在 OpenHarmony 上原生可编译。

## 依赖版本

- PostgreSQL 17.10 (已预装，提供 pg_config 和 PGXS)

## 验证结果

```bash
# .so 文件验证
file ~/usr/local/lib/postgresql/roaringbitmap.so
# → ELF shared object, 64-bit LSB arm64, not stripped

readelf -h ~/usr/local/lib/postgresql/roaringbitmap.so
# → ELF64, aarch64

# 扩展控制文件验证
cat ~/usr/local/share/postgresql/extension/roaringbitmap.control
# → default_version = '1.1', relocatable = true
```

## 回归测试

`make check` 不可用（PGXS 扩展不支持），`make installcheck` 需要 PostgreSQL 服务器运行。测试跳过，通过 staging 验证确认安装产物完整。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| postgresql-pg_roaringbitmap-1.1.0-ohos-aarch64.tar.gz | 446KB | 预编译包（stripped） |
| postgresql-pg_roaringbitmap-1.1.0-ohos-aarch64-debug.tar.gz | 1090KB | 预编译包（含调试符号） |

## 注意事项

- 此扩展是 PostgreSQL server 扩展，需配合 PostgreSQL 17.x 使用
- 安装后需在 PostgreSQL 中执行 `CREATE EXTENSION roaringbitmap` 启用
- CRoaring 库内嵌，不需要单独安装
---

**编译结束**: 2026-06-10 22:15
**最终状态**: published
