# mac-robber 1.02 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-31
- 编译器: clang (OHOS aarch64, tools.build:compiler_executables)
- 状态: success

## 上游核实
- 上游主页: https://sleuthkit.org/mac-robber/
- 官方源码: https://downloads.sourceforge.net/project/mac-robber/mac-robber/1.02/mac-robber-1.02.tar.gz
- 版本: 1.02 (CHANGES: "Feb 12, 2010: Fixed bug in previous update..." / 源码 `#define VER "1.02"`)
- SHA256: 5895d332ec8d87e15f21441c61545b7f68830a2ee2c967d381773bd08504806d
- 许可证: GPL-2.0 (COPYING: GNU GPL v2 June 1991; mac-robber.c: "version 2 of the License")
- 上游作者: Brian Carrier <carrier@sleuthkit.org> (The Sleuth Kit 项目)
- 优先使用官方 SourceForge release tarball（2010-02-12 原始发布），非 GitHub fork/第三方镜像
  - GitHub sleuthkit/mac-robber tag 1.02 是作者后来迁移的 autotools 重构版（含 configure.ac/Makefile.am，结构与原始 release 不同），仅作交叉核实用途

## Conan 适配
- 版本: 1.02
- package_type: application
- 构建目标: `make CC=<ohos-clang> linux_notstatic`（非静态 + 大文件支持）
- 依赖: 无（单文件 C 程序，仅依赖 POSIX 标准库）
- 补丁: 0001-maxnamlen-musl.patch (3 行 MAXNAMLEN fallback)

## 平台依赖分析
| API/字段 | 类型 | OHOS musl 兼容性 |
|----------|------|-------------------|
| lstat, opendir, readdir, closedir | POSIX 标准 | ✅ 兼容 |
| readlink | POSIX 标准 | ✅ 兼容 |
| getopt, gethostname | POSIX 标准 | ✅ 兼容 |
| struct stat (st_mode/st_uid/st_gid/st_size/st_atime/st_mtime/st_ctime) | POSIX 标准 | ✅ 兼容 |
| st_atim/st_mtim/st_ctim (nanosecond) | 未使用 | N/A |
| S_IFREG/S_IFDIR/S_IFLNK/S_ISUID 等文件类型/权限宏 | POSIX 标准 | ✅ 兼容 |
| major()/minor() 设备号 | 未使用 | N/A |
| PATH_MAX | 未使用 | N/A |
| MAXNAMLEN | BSD/glibc 扩展 | ❌ musl 未定义 → 补丁 fallback |
| getpwuid/getgrgid | 未使用 | N/A |

## 补丁说明
| 补丁 | 原因 | 改动 |
|------|------|------|
| 0001-maxnamlen-musl.patch | musl `<dirent.h>` 不定义 MAXNAMLEN（BSD/glibc 扩展宏），do_dir() 第 241 行 `path_len = dir_len + MAXNAMLEN + 2` 编译失败 | 添加 `#ifndef MAXNAMLEN` / `#define MAXNAMLEN 256` / `#endif`（与 glibc 定义一致，不改动任何逻辑） |

## 上游测试核查
mac-robber 1.02 上游正式测试为 0。

### 证据
1. **SourceForge release tarball**（archives/m/mac-robber/1.02 使用的官方源码）：
   - 文件清单: `.indent.pro`, `CHANGES`, `COPYING`, `Makefile`, `README`, `mac-robber.c`（共 6 个文件）
   - 无 `tests/`、`test/`、`regress/` 目录
   - Makefile 目标: `all`, `linux`, `linux_notstatic`, `sun`, `simple`, `clean`, `indent` — 无 `check`/`test` 目标
   - 全文件搜索 `make check`/`make test`/`TESTS`/`check_PROGRAMS`/`check-local`/`ctest`/`pytest` 无匹配
2. **GitHub autotools 版**（交叉核实）：
   - `configure.ac`: 无 `AC_CONFIG_TESTDIR`，无测试相关宏
   - `Makefile.am`: 无 `check_PROGRAMS`，无 `TESTS`，无 `check-local`；仅有 `clean-local`
   - `Makefile.in`: 仅有 automake 默认的空 `check: check-am`（无 check_PROGRAMS 则不执行任何测试）
   - `.github/workflows/build.yml`: CI 仅 `./configure && make`，无 `make check`/`make test`
3. 上游不在 `no_official_test.txt` 白名单中（该白名单仅用于已知不兼容场景）

---

**最终状态**: built
