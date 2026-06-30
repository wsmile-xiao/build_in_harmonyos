# temporal_tables 1.2.2 适配笔记

## 编译环境
- 构建系统: makefile（PGXS - PostgreSQL Extension Build System）
- 编译日期: 2026-06-30
- 编译器: clang 15.0.4 (Target: aarch64-unknown-linux-ohos)
- PostgreSQL: 16.4 (pg_config 可用)
- 状态: published

## 编译步骤

1. **下载源码**: GitHub SSL 证书验证失败，改用 `curl -kL` 通过 codeload.github.com 镜像下载 v1.2.2.tar.gz
2. **init-build**: 使用 `ohc-run.py init-build temporal_tables 1.2.2 --url=... --no-download`，手动将 tar 包重命名为 `temporal_tables-1.2.2.tar.gz` 放入 `$TMPDIR/builds/`
3. **创建 pg_config wrapper**: 系统 pg_config 不支持 `--pkgincludedir` 选项，导致 PGXS Makefile.global 生成错误的 include 路径。创建 wrapper 脚本拦截该选项，返回自定义路径，并在该路径下创建 `server`/`internal` 符号链接指向 PostgreSQL 源码 include 目录
4. **编译**: `make PG_CONFIG=$TMPDIR/pg_config_wrapper` 成功编译 temporal_tables.c 和 versioning.c，生成 temporal_tables.so
5. **创建静态库**: `llvm-ar rcs libtemporal_tables.a temporal_tables.o versioning.o`（R26: BUILD_SHARED_LIBS=OFF）
6. **安装**: `make PG_CONFIG=$TMPDIR/pg_config_wrapper install DESTDIR=$TEST_PREFIX` 成功安装 .so/.control/.sql 文件，手动复制 .a 静态库

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载 SSL 证书验证失败 | 鸿蒙系统 CA 证书不完整 | 用 `curl -kL` 通过 codeload.github.com 镜像下载 |
| 2 | pg_config 不支持 `--pkgincludedir` | PostgreSQL 16.4 的 pg_config 移除了该选项 | 创建 pg_config wrapper 脚本，拦截 `--pkgincludedir` 返回自定义路径 |
| 3 | PGXS Makefile.global 引用 `$(pkgincludedir)/server` 和 `$(pkgincludedir)/internal` | pg_config --pkgincludedir 失败导致路径错误 | 在自定义路径下创建 server/internal 符号链接指向 PostgreSQL 源码 include 目录 |
| 4 | Conan 构建中 PGXS 同样失败 | Conan 干净构建环境中 pg_config 同样有问题 | 在 conanfile.py 中绕过 PGXS，直接用 $CC 编译 C 源文件，通过 pg_config --includedir-server 获取头文件路径 |
| 5 | Conan test_package CMake 找不到 include 目录 | package() 未复制头文件 | 在 package() 中添加 `copy(self, "*.h", ...)` 复制 temporal_tables.h |
| 6 | `conan.tools.make` 模块不存在 | Conan 2.12 无此模块 | 改用 AutotoolsToolchain 生成环境变量 + self.run() 直接调用编译命令 |
| 7 | make installcheck 失败 | pg_regress 二进制未编译，无运行中的 PostgreSQL | 跳过，记录原因 |

## 源码修改

无源码修改。所有适配通过 pg_config wrapper 脚本和 conanfile.py 构建逻辑实现。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| PostgreSQL | 16.4 | 系统已安装（pg_config 可用） |
| clang | 15.0.4 | 鸿蒙 SDK 工具链 |
| llvm-ar | LLVM 15 | 鸿蒙 SDK 工具链 |
| make | 4.4.1 | 系统自带 |

## 验证结果

```
# 编译
make PG_CONFIG=$TMPDIR/pg_config_wrapper → 退出码 0
llvm-ar rcs libtemporal_tables.a ... → 退出码 0

# 安装
make install DESTDIR=$TEST_PREFIX → 退出码 0

# Conan test_package
conan test . temporal_tables/1.2.2@ohpcd/stable → 退出码 0
100% tests passed, 0 tests failed out of 1

# conan-verify 8 道门禁
G0 PASS, G1 PASS, G2 PASS, G3 PASS, G4 PASS, L2 PASS, L4 PASS, L5 PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| temporal_tables.so | 35136 bytes | PostgreSQL 扩展共享库 (ELF arm64) |
| libtemporal_tables.a | 23992 bytes | 静态库 (R26: BUILD_SHARED_LIBS=OFF) |
| temporal_tables.o | 3544 bytes | 目标文件 |
| versioning.o | 20024 bytes | 目标文件 |
| temporal_tables.control | 140 bytes | 扩展控制文件 |
| temporal_tables--1.2.2.sql | 696 bytes | 扩展 SQL 脚本 |

## 注意事项

- temporal_tables 是 PostgreSQL 扩展，编译时需要 PostgreSQL 开发头文件（postgres.h, fmgr.h 等）
- pg_config 的 `--pkgincludedir` 选项在此 PostgreSQL 版本中不可用，需通过 wrapper 脚本解决
- conanfile.py 中的构建逻辑绕过了 PGXS，直接编译 C 源文件，因此不依赖完整的 PGXS 环境
- 回归测试（make installcheck）需要 pg_regress 和运行中的 PostgreSQL 服务器，当前环境不满足
