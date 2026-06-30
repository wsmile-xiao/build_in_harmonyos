# temporal_tables

Temporal Tables PostgreSQL Extension — 为 PostgreSQL 提供时态表（temporal tables）功能支持。

## 软件信息

| 项目 | 值 |
|------|------|
| 软件名 | temporal_tables |
| 描述 | Temporal Tables PostgreSQL Extension |
| 许可证 | BSD-2-Clause |
| 主页 | https://github.com/arkhipov/temporal_tables |
| 语言 | C |
| 构建系统 | PGXS (PostgreSQL Extension Build System) / GNUmakefile |

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.2.2 | published | 2026-06-30 |

## 依赖

- PostgreSQL 开发头文件（postgres.h, fmgr.h 等）
- clang 编译器
- llvm-ar（静态库创建）

## 构建说明

temporal_tables 使用 PGXS 构建系统，需要 `pg_config` 命令。在鸿蒙平台上，pg_config 不支持 `--pkgincludedir` 选项，需要通过 wrapper 脚本或直接编译 C 源文件绕过 PGXS。

详见各版本目录下的 `notes.md` 和 `manifest.yaml`。
