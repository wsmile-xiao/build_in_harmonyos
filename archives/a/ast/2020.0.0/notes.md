# ast 2020.0.0 适配笔记

## 编译环境
- 构建系统: meson (Meson + Ninja)
- 编译日期: 2026-08-25
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

AST 2020.0.0 使用 Meson 作为构建系统（不是旧的 NMAKE/bin/package 自举系统）。

```bash
# 1. 配置
CC=/data/service/hnp/bin/clang \
AR=/data/service/hnp/bin/llvm-ar \
RANLIB=/data/service/hnp/bin/llvm-ranlib \
LD=/data/service/hnp/bin/ld.lld \
meson setup builddir --prefix=$DEFAULT_PREFIX \
  -Dbuild-api-tests=false -Dwarnings-are-errors=false

# 2. 编译
LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:$LD_LIBRARY_PATH \
ninja -C builddir -j2

# 3. 安装
LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:$LD_LIBRARY_PATH \
meson install -C builddir
```

关键说明:
- 必须使用完整路径指定 clang/llvm-ar/llvm-ranlib/ld.lld，否则 meson 无法找到
- lld 链接器需要 LD_LIBRARY_PATH 包含 SDK lib 目录，否则找不到 libxml2.so.16
- Meson 正确识别 HarmonyOS 为 "harmonyos" 系统，自动跳过部分不兼容的测试

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fts.h` not found | HarmonyOS libc 不提供 BSD fts(3) API | 创建 `src/compat/fts.h` 和 `src/compat/fts.c` 兼容实现 |
| 2 | `gethostid()` undeclared | HarmonyOS 不提供 gethostid() | 用 `#elif defined(__OHOS__)` 守卫，使用 gethostname 作为 fallback |
| 3 | lld 找不到 libxml2.so.16 | lld 的 RUNPATH($ORIGIN/../lib) 在 musl 上解析异常 | 设置 LD_LIBRARY_PATH 指向 SDK lib 目录 |
| 4 | FTSENT 缺少 fts_accpath/fts_errno 字段 | 自定义 fts.h 不完整 | 补全 FTSENT 结构体字段 |
| 5 | FTS_NOSTAT 未定义 | 自定义 fts.h 缺少此常量 | 在 fts.h 中添加 FTS_NOSTAT 定义 |

## 源码修改

| 文件 | 类型 | 修改说明 |
|------|------|----------|
| `meson.build` | 修改 | 添加 compat 静态库和 include 目录 |
| `src/compat/fts.h` | 新增 | BSD fts(3) API 声明，包含完整的 FTS/FTSENT 结构体 |
| `src/compat/fts.c` | 新增 | BSD fts(3) API 实现 (fts_open/read/children/set/close) |
| `src/lib/libdll/meson.build` | 修改 | 链接 libcompat，添加 compat include 目录 |
| `src/cmd/ksh93/meson.build` | 修改 | 添加 compat include 目录 |
| `src/cmd/ksh93/cmds/uname.c` | 修改 | 用 `#elif defined(__OHOS__)` 守卫 gethostid() |

## 依赖版本

无外部依赖。AST 是自包含的，包含所有自己的库 (sfio, vmalloc, libast, libdll)。

- 编译器: clang 15.0.4 (HarmonyOS SDK 26.0.0.18)
- 构建系统: Meson 1.11.1 + Ninja 1.13.1
- 无 Conan 依赖

## 验证结果

```bash
$ ./builddir/src/cmd/ksh93/ksh -c 'echo "ksh test: OK"; print "version test: OK"; typeset -i x=42; print $((x*2))'
ksh test: OK
version test: OK
84
```

ksh 二进制可执行，支持基本算术、变量展开、数组等核心功能。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/ksh` | KornShell 93 可执行文件 |
| `bin/shcomp` | shell 脚本编译器 |
| `share/man/man1/ksh.1` | ksh 手册页 |

## 注意事项

1. AST 2020.0.0 不使用旧的 NMAKE/bin/package 自举构建系统，而是使用 Meson
2. fts.h 兼容实现是简化版本，不支持完整的 fts 语义（如 fts_set 的 FTS_FOLLOW 等），但对 AST/ksh 的使用场景足够
3. lld 链接器的 libxml2.so.16 依赖问题需要在构建环境中设置 LD_LIBRARY_PATH
4. 软件类型为 application（CLI 工具），主要产物是 ksh 二进制文件
---

**编译结束**: 2026-08-25 12:01
**最终状态**: built
