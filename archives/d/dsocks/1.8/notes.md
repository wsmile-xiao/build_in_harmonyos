# dsocks 1.8 适配笔记

## 编译环境

| 字段 | 值 |
|------|-----|
| 构建系统 | makefile（GNUMakefile，非 autotools） |
| 编译日期 | 2026-06-17 |
| 编译器 | clang 15.0.4 (aarch64-linux-ohos) |
| 平台 | OpenHarmony aarch64 (musl libc) |
| 状态 | built |

## 编译步骤

dsocks 没有 configure 脳本，使用 GNUMakefile 直接编译：

```bash
# Step 1: 初始化
python3 $SKILL_ROOT/scripts/ohc-run.py init-build dsocks 1.8 --url=<URL>

# Step 2: 编译（源码修改后）
cd $BUILD_SRC_DIR
make -f GNUMakefile clean
make -f GNUMakefile

# Step 3: DESTDIR 安装
make -f GNUMakefile install DESTDIR=$TEST_PREFIX

# Step 4: 本地安装验证
make -f GNUMakefile install   # 不带 DESTDIR
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| P1 | 编译报 `DSOCKS_PATH_LIBC` 硬编码 `libc.so.6` | OpenHarmony/musl 使用 `libc.so`，非 glibc 的 `libc.so.6` | dsocks.h 改用 `__GLIBC__` 守卫，OHOS 落入 else 分支定义 `"libc.so"` |
| P2 | `strlcpy()` 前置声明与 musl string.h 冲突 | musl 已提供 strlcpy()，`#ifdef __linux__` 下的声明重复 | dsocks.c 改为 `#if defined(__GLIBC__)` 仅 glibc 下声明 |
| P3 | 编译报 `NETDB_SUCCESS` 未定义 | musl netdb.h 不定义 `NETDB_SUCCESS`（glibc 定义为 0） | dsocks.c 添加 `#ifndef NETDB_SUCCESS` + `#define NETDB_SUCCESS 0` |
| P4 | 链接报 `--shared` 不识别 | GNU ld 用 `--shared`，clang/lld 用 `-shared` | GNUMakefile 改 `LDFLAGS = -shared` |
| P5 | OBJS 包含 `strlcpy.o` 但无 `strlcpy.c` | musl 已内建 strlcpy，上游源码缺 strlcpy.c | GNUMakefile OBJS 移除 `strlcpy.o` |
| P6 | 包装脚本硬编码 `/usr/local/lib` | OpenHarmony 安装路径为 `$DEFAULT_PREFIX/lib` | dsocks.sh/dsocks-torify.sh 添加 OHOS 分支 |

## 源码修改

5 个补丁（C 代码补丁使用 `__GLIBC__` 可移植守卫，Shell 脚本使用 `uname -s` 运行时检测）：

| 补丁 | 文件 | 修改摘要 |
|------|------|----------|
| 0001 | GNUMakefile | CC=clang, -shared, 移除 strlcpy.o, LIBDIR/BINDIR 适配, install 增加 OHOS 路径 |
| 0002 | dsocks-torify.sh | 添加 `elif uname -s = "OHOS"` 分支，使用 OHOS 库路径 |
| 0003 | dsocks.c | `#ifndef NETDB_SUCCESS` 守卫宏定义，`#if defined(__GLIBC__)` 守卫 strlcpy 声明 |
| 0004 | dsocks.h | `#elif defined(__GLIBC__)` 守卫 DSOCKS_PATH_LIBC，非 glibc 落入 else 分支为 "libc.so" |
| 0005 | dsocks.sh | 添加 `elif uname -s = "OHOS"` 分支，使用 OHOS 库路径 |

## 依赖版本

无外部依赖。系统内置依赖：
- libc.so (musl libc, /lib/ld-musl-aarch64.so.1)
- libdl (dlopen/dlsym, musl 内置)
- libresolv (resolver 函数, musl 内置)

## 验证结果

```bash
# 编译产物格式
file libdsocks.so.1.0 → ELF shared object, 64-bit LSB arm64

# 动态依赖
readelf -d libdsocks.so.1.0 | grep NEEDED → libc.so

# 核心导出符号
nm -D libdsocks.so.1.0 → _dsocks_init, connect, getaddrinfo, gethostbyname

# 符号链接
libdsocks.so → libdsocks.so.1 → libdsocks.so.1.0（三级链接有效）

# 包装脚本
bash -n dsocks → 语法OK
bash -n dsocks-torify → 语法OK

# 源码校验
sha256sum dsocks-1.8.tar.gz → 2b57fb487633f6d8b002f7fe1755480ae864c5e854e88b619329d9f51c980f1d
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| dsocks-1.8-ohos-aarch64.tar.gz | 241KB | 预编译主包（已 strip + ELF 签名） |
| dsocks-1.8-ohos-aarch64-debug.tar.gz | 140KB | 调试符号包 |

## 注意事项

1. dsocks 是 LD_PRELOAD 库，仅对动态链接二进制生效；静态链接程序不适用
2. 功能测试需要 SOCKS 代理服务器（ssh -D 或 Tor），构建环境无此条件
3. DSOCKS_PATH_LIBC 使用 `libc.so`（dlopen 查找路径），运行时由 ld-musl 解析
4. C 代码补丁使用 `__GLIBC__` 守卫（非 `__OHOS__`），更可移植且避免争议

---
**编译结束**: 2026-07-15
**最终状态**: built
---

**编译结束**: 2026-07-16 06:51
**最终状态**: built
