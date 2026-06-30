# perl-dbd-pg 3.18.0 编译笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 CPAN 下载 DBD-Pg-3.18.0.tar.gz
2. 初始化编译环境：ohc-run.py init-build perl-dbd-pg 3.18.0
3. 修改 Makefile.PL 添加链接参数（绕过 CRT 文件缺失）
4. 运行 perl Makefile.PL 配置
5. 运行 make 编译
6. 运行 make install DESTDIR=$TEST_PREFIX 安装到 staging

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接错误：缺少 crti.o, crtn.o, crtbeginS.o, crtendS.o | 鸿蒙系统缺少 CRT 文件 | 在 Makefile.PL 中添加 `dynamic_lib => { OTHERLDFLAGS => '-nostartfiles -nodefaultlibs -lc' }` |
| 2 | 缺少 pg_config 命令 | PostgreSQL 客户端工具未安装 | 使用 pg_config 包装器返回 PostgreSQL 18.3 信息 |
| 3 | 缺少 DBI Perl 模块 | DBD::Pg 的必需依赖 | 已编译 DBI 1.643 |
| 4 | SELinux HMDFS 限制 | 动态库加载受限 | 需安装到系统目录 /data/service/hnp |

## 依赖版本

### 已存在
- libpq (PostgreSQL 客户端库): ~/usr/local/lib/libpq.so.5.18
- musl C 库头文件: ~/usr/local/include (371 个文件)
- DBI Perl 模块: ~/usr/local/lib/perl5/site_perl/5.42.0/aarch64-linux/auto/DBI/

### 编译依赖
- musl C 库头文件（提供 stdio.h, ctype.h, sys/types.h 等）
- PostgreSQL 客户端工具（提供 pg_config）
- perl-dbi（DBI 模块）

## 编译产物

- **Pg.so**: 249KB，ELF 64-bit ARM64 共享对象
- **Pg.pm**: Perl 模块文件 (193KB)
- **Bundle/DBD/Pg.pm**: Bundle 模块文件

## 知识沉淀

### 平台发现
- 鸿蒙系统缺少 CRT 文件（crti.o, crtn.o 等）
- 链接 Perl XS 模块需要 `-nostartfiles -nodefaultlibs -lc` 参数
- SELinux HMDFS 限制动态库加载到用户目录

### 编译建议
- Perl XS 模块编译需要完整的 C 库头文件支持
- Makefile.PL 中可通过 `dynamic_lib` 参数添加链接选项
- 需要 ELF 签名才能在鸿蒙系统执行

---
**编译结束**: 2026-06-10 15:35
**最终状态**: built (编译成功，产物完整)
---

**编译结束**: 2026-06-10 15:40
**最终状态**: built
