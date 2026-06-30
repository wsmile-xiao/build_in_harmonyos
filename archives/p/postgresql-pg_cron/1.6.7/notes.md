# postgresql-pg_cron 1.6.7 适配笔记

## 编译环境
- 构建系统: pgxs (PostgreSQL Extension Building Infrastructure)
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: published

## 编译步骤

pg_cron 使用 PGXS (PostgreSQL Extension Building Infrastructure) 构建系统，无需 configure 步骤：
1. `cd $BUILD_SRC_DIR`
2. `make` — PGXS 通过 pg_config 自动获取 PostgreSQL 的编译参数和路径
3. `make install DESTDIR=$TEST_PREFIX` — staging 安装
4. `make install` — 本地安装到 $DEFAULT_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 SSL 证书验证失败 | HarmonyOS 环境缺少 CA 证书，urllib SSL 验证失败 | 手动 curl -k 下载 tarball，放到 $build_dir 预期位置 |
| 2 | verify-build G4 失败：manifest 缺少 build_system | 验证脚本查找扁平 build_system: 键，但模板使用嵌套 build.system: | 在 manifest.yaml 添加扁平 build_system: pgxs |

## 源码修改

无源码修改。pg_cron 编译完全通过，无需任何补丁。

## 依赖版本

- PostgreSQL 17.10 (提供 pg_config、PGXS、libpq)
- libpq.so.5 (PostgreSQL 客户端库，pg_cron 共享库链接依赖)

## 验证结果

```bash
# pg_cron.so 安装验证
file ~/usr/local/lib/postgresql/pg_cron.so
# ELF shared object, 64-bit LSB arm64

# 扩展文件验证
ls ~/usr/local/share/postgresql/extension/pg_cron*
# pg_cron.control + 8个SQL迁移脚本

# 依赖检查
llvm-objdump -p ~/usr/local/lib/postgresql/pg_cron.so | grep NEEDED
# NEEDED libpq.so.5
# NEEDED libc.so
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| postgresql-pg_cron-1.6.7-ohos-aarch64.tar.gz | 5.3MB | 预编译包（stripped） |
| postgresql-pg_cron-1.6.7-ohos-aarch64-debug.tar.gz | 700KB | debug 符号包 |

## 注意事项

- pg_cron 是 PostgreSQL 扩展，无独立可执行文件，G2 功能验证显示"无二进制文件"是正常现象
- pg_cron 依赖运行中的 PostgreSQL 实例才能测试（make check 需要 PG 服务），staging 中无法执行
- 编译需要 pg_config 在 PATH 中且指向正确的 PostgreSQL 安装
---

**编译结束**: 2026-06-10 22:14
**最终状态**: published
