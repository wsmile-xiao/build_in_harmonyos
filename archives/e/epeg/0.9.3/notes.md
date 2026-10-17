# epeg 0.9.3 adaptation notes

## 编译环境
- 构建系统: autotools (configure.ac + Makefile.am + autogen.sh)
- 编译日期: 2026-08-20
- 编译器: clang 15 (OHOS SDK)
- 状态: built
- 平台: OHOS 6.0 aarch64 (armv8)
- Profile: ci/conan/profiles/ohos-aarch64

## 软件概述
epeg 是 Enlightenment 项目的 JPEG 缩略图缩放库，基于 libjpeg-turbo 和 libexif，
以极快速度生成 JPEG 缩略图。源码为 C 语言，构建系统为 Autotools。

## 编译步骤

1. **源码获取**: 从 GitHub tag v0.9.3 下载 tarball (20900 bytes)，SHA256 已验证。
2. **Autotools 引导**: GitHub tag archive 不含预生成 configure 脚本。
   上游 `autogen.sh` 调用裸 `aclocal`/`automake`（二进制名而非 $ACLOCAL/$AUTOMAKE），
   会解析到系统 PATH 中的损坏 aclocal-1.16/1.17（无匹配 share/aclocal-1.18 目录）。
   改用 `autoreconf -fi`（遵守 ACLOCAL/AUTOMAKE 环境变量，由 automake/1.18
   tool_require 提供），执行相同的 aclocal → autoheader → autoconf → libtoolize
   → automake 序列。
3. **configure**: `Autotools.configure()` 调用生成的 configure 脚本，关键参数:
   - `--prefix=/` `--enable-static` `--disable-shared`（R26: 系统同名库静态编译）
   - `--build=aarch64-unknown-linux-gnu`（2003 年 config.guess 不认识 OHOS）
   - `SHELL=/data/service/hnp/bin/bash`（OHOS 拒绝通过 shebang 执行脚本）
4. **make**: `make -j1`（HMDFS 并行构建 jobserver fifo EPERM，E074）
5. **install**: `make install` + 复制 COPYING 到 licenses/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `aclocal: error: couldn't open directory '.../aclocal-1.18'` | autogen.sh 调用裸 `aclocal`，解析到系统损坏的 aclocal-1.16/1.17 | 改用 `autoreconf -fi`（遵守 $ACLOCAL/$AUTOMAKE 环境变量） |
| 2 | `configure: error: cannot run C compiled programs` | OHOS loader 无默认搜索路径，conftest 运行时找不到 libjpeg.so.62 | 在 generate() 中设置 LD_LIBRARY_PATH 指向依赖库目录 |
| 3 | config.status 临时目录 Permission denied | HMDFS 上 toybox mktemp -d 创建 drwx--S--- 目录 | mktemp wrapper 用 mkdir (umask 022) 替代 |
| 4 | configure umask 077 导致临时文件权限问题 | autotools 生成的 configure 默认 umask 077 | patch umask 077 → 022 |
| 5 | make 触发 aclocal.m4 重建规则调用 missing aclocal-1.16 | CI worker 无 aclocal | 设 ACLOCAL/AUTOMAKE/AUTOCONF 等为 `:` (no-op) |
| 6 | CMakeDeps: Component 'libjpeg-turbo::libjpeg' not found | libjpeg-turbo 无显式组件 | cpp_info.requires 用 `libjpeg-turbo::libjpeg-turbo`（隐式组件名=包名） |
| 7 | test_package.c: NULL undeclared | Epeg.h 未包含定义 NULL 的头文件 | 添加 `#include <stddef.h>` |

## 源码修改

无补丁。所有适配通过 conanfile.py 的环境变量和 configure 参数完成。
umask 077→022 的修改在 build() 中对生成的 configure 文件做 replace_in_file，
不作为补丁提交。

## 依赖版本

- libjpeg-turbo/3.2.0 (提供 libjpeg, libturbojpeg)
- libexif/0.6.26.1 (提供 libexif)
- automake/1.18 (build_require, 提供 aclocal/automake)
- libtool/2.5.4 (build_require, 提供 libtoolize)

## 验证结果

```bash
$ conan create archives/e/epeg/0.9.3/conanfile.py \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing
...
epeg/0.9.3: package(): Packaged 1 '.la' file: libepeg.la
epeg/0.9.3: package(): Packaged 1 '.a' file: libepeg.a
epeg/0.9.3: package(): Packaged 1 '.pc' file: epeg.pc
epeg/0.9.3: package(): Packaged 1 '.h' file: Epeg.h
epeg/0.9.3: package(): Packaged 2 files: epeg, COPYING
epeg/0.9.3: Created package revision b73da718f44b9b879912ab6afe02307b
...
[100%] Built target test_package
epeg/0.9.3 (test package): RUN: ./test_package
EXIT=0
```

test_package 验证:
- epeg_close(NULL) 安全无操作（库内 `if (!im) return;` 守卫）
- epeg_memory_open(NULL, 0) 返回 NULL（空数据触发 JPEG 错误处理 → setjmp/longjmp → NULL）
- "Premature end of JPEG file" 是 libjpeg 对空数据的预期警告，不影响测试通过

## 上游测试用例检查

**结论：epeg 0.9.3 无任何上游测试用例。**

检查记录（2026-08-20）：
- 源码树无 test/、tests/、spec/ 目录，无任何 *test*/*check* 命名的源文件。
- `configure.ac` 未定义 `TESTS`、`check_PROGRAMS`、`AM_TESTS` 等测试宏。
- `Makefile.am`（顶层及 src/bin、src/lib）无 `check` 目标。
- 实际运行 `make check` → `make: *** No rule to make target 'check'. Stop.`（确认无测试目标）。
- 源码仅含：库 (`src/lib/epeg_main.c`) + CLI 工具 (`src/bin/epeg_main.c`)，无示例/演示/回归测试。

因此无法执行上游 `make check`；本包测试覆盖仅依赖 test_package 烟雾测试（API 链接 + NULL 参数边界校验）。

## 注意事项

- configure.ac 中 AC_INIT 版本写死为 0.9.1.042，但 git tag 是 v0.9.3，这是上游已知行为。
- epeg 同时含 CMakeLists.txt，但上游 Nix/T2 等发行版均用 autotools，本配方遵循 autotools。
- 包含 epeg CLI 工具 (src/bin/) 和 libepeg 库 (src/lib/)，均编译安装。
---

**编译结束**: 2026-08-20 10:57
**最终状态**: built
