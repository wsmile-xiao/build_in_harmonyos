# Draft: `DRAFT-XMILL-08-MSC-ONLY-UPSTREAM-POSIX-HEADER-SURFACE`
> Stem: `xmill-0.8-msvc-only-upstream-posix-header-surface` — pairs with the same-stem `.kv`

# 上游只有 MSVC 工程（无任何构建系统）时的 POSIX 移植清单

## 基本信息

- **ID**: DRAFT-XMILL-08-MSC-ONLY-UPSTREAM-POSIX-HEADER-SURFACE
- **严重度**: 2
- **类别**: portability | headers | msvc | posix | libc | musl | build-system
- **触发工具**: clang | ld | cmake | conan
- **阶段**: configuration → compilation → linking
- **来源**: xmill 0.8 适配（2026-10-01，上游仅 `xmill.sln` + `xmill/xmill.vcproj`）

## 错误特征（4 类，独立潜伏，不会一次全暴露）

| # | 错误原文 | 触发点 |
|---|---------|--------|
| 1 | `ld.lld: error: undefined symbol: errno` | 链接期（第 1 个真实构建错误） |
| 2 | `error: unknown type name 'FILE'` / `use of undeclared identifier 'stdout'` | 编译期 |
| 3 | `fatal error: '..\zlib\zlib.h' file not found` | 编译期 |
| 4 | `error: ISO C++17 does not allow 'register' storage class specifier` | 编译期 |
| 4b | `cannot initialize a parameter of type 'char *' with an rvalue of type 'const char *'` | 编译期（三元表达式里字面量转换不再被当作扩展） |

## 根因（一类）

MSVC 语境下"能编过"的前提在 POSIX 上不成立：

1. `extern int errno;`：MSVC CRT 导出同名全局符号；POSIX/musl/glibc 的 `errno` 是宏
   `(*__errno_location())`，没有全局符号 → 链接失败。**修法**：删声明，改 `#include <errno.h>`。
2. `<stdio.h>` 只写在 `#ifdef WIN32` 那一支（Win32 上 `<io.h>`/`<fcntl.h>` 顺带引入）→
   POSIX 分支下 `FILE`/`stdout`/`fopen` 全部未声明。**修法**：POSIX 分支补 `<stdio.h>`。
3. `"..\zlib\zlib.h"`：反斜杠不是 POSIX 路径分隔符。**修法**：改逻辑名 `<zlib.h>`，
   并顺势把树内 vendored zlib 换成 Conan 的 `zlib/1.3.2`（不再编译 vendored 副本）。
4. C++17 删除了 `register`；字符串字面量转 `char*` 在**多数组三元表达式**里会硬报错
   （clang 不再施加扩展）。**修法**：删 `register`；`(cond ? x : "")` 写 `(cond ? x : (char *)"")`。

另有两处**构建面**坑（同样属于"只有 MSVC 工程"这一类）：

5. 新增文件补丁的头部必须是 `--- /dev/null`；写成 `--- a/<file>` 时 conan 的
   `apply_conandata_patches` 会报 `source/target file does not exist`。
6. URL 无 `.tar.gz` 后缀（如 codeload 直链 `.../tar.gz/refs/heads/master`）时 `conan get()`
   误判为 zip → `BadZipFile: File is not a zip file`；改用
   `https://github.com/<o>/<r>/archive/refs/heads/<b>.tar.gz`（302 到 codeload，sha256 一致）。

## 推荐流程

1. **先语法普查**，别急着构建：

   ```bash
   clang++ -std=c++17 -fsyntax-only -I <src> -I <zlib-inc> <src>/*.cpp 2>syntax.log
   grep -c "error:" syntax.log     # 本例 26 处，归为上表 4 类
   ```

2. 逐类修完 → 真实构建 → 拿到链接/运行期首错（本例即 `undefined symbol: errno`）。
3. **验收必须落到运行期往返**（`conan create` 通过 ≠ 可用）。

## 适用面

上游只提供 MSVC 工程 / 只在 Windows 上维护的老 C/C++ 包（1990s–2000s 的工具、压缩器、
图形、科学计算），且没有任何 Makefile/CMake/configure —— 首次搬到 OHOS/POSIX 时，
第一波问题几乎总落在这一组头文件/构建面上。

## 关联

- `notes.md` §3.1（语法普查表）、§3.2（首个真实构建错误 errno）、§3.6（补丁管线手动模式）
- 同类：`xmill-0.8-lp64-literal-pointer-mask-truncation`（同源的"老代码上 64 位"问题）
