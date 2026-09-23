# libgarmin 0-svn320 适配笔记

## 编译环境
- 构建系统: custom（配方内手写 Makefile + clang 直接编译静态库；上游 autotools 但 SVN 快照无预生成 configure）
- 编译日期: 2026-09-18
- 编译器: clang 15 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. 用 `conan.tools.files.get` 解压 `libgarmin_0~svn320.orig.tar.gz`（`strip_root=True`，顶层目录 `libgarmin-0~svn320`）。
2. 在 `src/` 写入最小 `config.h`（仅 include 标准头：sys/types, stdint, stdlib, string, stdio, unistd, fcntl）——源码不使用任何 `HAVE_*`，仅需标准类型（`u_int32_t`/`ssize_t` 来自 `<sys/types.h>`）。
3. 在 `src/` 写入 `version.h`（`LIBVERSION`/`PACKAGE_VERSION`），因 `garmin.c` 无条件 `#include "version.h"` 而 SVN 快照无 `.svn` 无法由 Makefile 生成。
4. 在 `src/` 写入手写 `Makefile`：`clang` 编译全部 `src/*.c`（`-I. -include config.h -fPIC -DDEBUG`），`llvm-ar rcs` 打包为 `libgarmin.a`。
5. `build()` 运行 `make -j1`；`package()` 安装 `libgarmin.a` → `lib/`、`libgarmin.h` → `include/`、`data/garmintypes.txt` → `share/libgarmin/`，并生成 `libgarmin.pc` → `lib/pkgconfig/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `autoreconf` 失败：`Can't exec "aclocal"` | 上游 SVN 快照无预生成 `configure`；OHOS 构建环境无 `automake`/`aclocal` | 放弃 autotools 引导，改用最小 `config.h` + clang 直接编译静态库（CI 同样无 automake，避免依赖） |
| 2 | `array.c` 报 `use of undeclared identifier 'NULL'` | OHOS sysroot 的 `<malloc.h>` 不定义 `NULL`，而部分文件不 include 提供 `NULL` 的头 | `config.h` include `<stdlib.h>`/`<stddef.h>`，并用 `-include config.h` 全局强制包含 |
| 3 | `struct gpoint`/`gpoly` 无 `source`/`slen` 成员 | 这两个成员由 `#ifdef DEBUG` 守卫，上游 `configure.ac` 默认 `debug=true` 加 `-DDEBUG` | 编译加 `-DDEBUG`（与上游默认一致） |
| 4 | `make` 用 `cc` 而非 clang（环境 CC=cc 不存在） | 工作/CI 环境 `CC` 误设为 `cc` | Makefile 用 `CC ?= clang`，并由 `AutotoolsToolchain` 注入 OHOS clang 覆盖 |

## 源码修改

无源码级补丁（`patches: []`）。所有移植处理均在构建层（config.h / version.h / Makefile / 编译宏），未改动上游 `.c/.h`。

## 依赖版本

- 无 conan 依赖；仅依赖 OHOS sysroot 的 libc（glibc 兼容层）。

## 验证结果

```bash
# conan create 通过（含 test_package）：clang 编译 18 个 .c 为 libgarmin.a，
# test_libgarmin 链接静态库并调用 gar_init()/gar_free() 成功。
# test_package 输出：OK: libgarmin linked and gar_init/gar_free work on OHOS
```

## 交付物

| 文件 | 说明 |
|------|------|
| libgarmin.a | 静态库（libs=["garmin"]） |
| libgarmin.h | 公共头文件 |
| share/libgarmin/garmintypes.txt | Garmin 类型描述数据 |
| lib/pkgconfig/libgarmin.pc | pkg-config 文件 |

## 注意事项

- 纯静态库，无可执行文件，无需 `commands.json`（R38）。
- 上游 `utils/` 为示例程序（bsptest/garroute/gartest 等），本次仅适配库本身，未构建。
- `dataprefix` 仅在 `Makefile.am` 出现，源码未使用，未定义不影响功能。

## 结束标记

- 最终状态：编译结束，conan create（含 test_package）在 OHOS aarch64 上通过。
- 适配完成，已生成 manifest.yaml / notes.md / 测试报告，提交 `feat/libgarmin-0-svn320`。
- COMPLETED
---

**编译结束**: 2026-09-19 07:44
**最终状态**: built
