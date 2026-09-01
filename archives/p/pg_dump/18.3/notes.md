# pg_dump 18.3 构建笔记

## 概述
pg_dump 是 PostgreSQL 数据库的转储工具，从 PostgreSQL 18.3 源码树构建。
基于 PostgreSQL 历史适配经验（archives/p/postgresql/18.3），转为 Conan 配方。

## 构建流程
- 源码: GitHub 官方镜像 postgres/postgres REL_18_3 tag
- Configure: --without-icu --without-readline --without-zlib --without-openssl --build=aarch64-unknown-linux-ohos
- Build: make -j$(nproc) 成功
- 产物: pg_dump, pg_dumpall, pg_restore, pg_config, libpq.so.5.18

## OHOS 适配要点
1. System V IPC 不可用 (SIGSYS) → 全面跳过 SysV 共享内存
2. config.guess 无法自动检测 → 显式传递 --build
3. shm_open 检测成功但运行时 SIGSYS → 强制 DSM_IMPL_MMAP
4. hmdfs 文件系统限制 → 放宽权限检查
5. getpwuid 可能失败 → 数字 UID fallback
6. Unix-domain socket 不支持 → 禁用，使用 TCP/IP
7. umask 077 问题 → patch 修改为 umask 067
