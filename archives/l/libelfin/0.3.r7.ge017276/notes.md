# libelfin 0.3.r7.ge017276 适配笔记

## 编译环境

- 构建系统: makefile（上游为 elf/、dwarf/、examples/ 三个子目录的递归 Makefile，无 configure）
- 编译日期: 2026-09-16
- 编译器: clang / clang++ 15.0.4（OHOS aarch64）
- 状态: built

## 源码

- URL: https://github.com/aclements/libelfin/archive/e0172767b79b76373044118ef0272b49b02a0894.tar.gz
- SHA256: `0fb80f8a36b9b2563bd193ace5866972e739af306955e539310dc9dd870aef6c`
- 版本命名: 上游 `git describe` 形式（tag v0.3 + 7 个提交），pin 到 Arch Linux
  `libelfin 0.3.r7.ge017276`（pkgrel 2）所用的同一 commit `e0172767b79b76373044118ef0272b49b02a0894`。

## 依赖（W0）

本包**无外部依赖**，理由：

- `elf/Makefile`、`dwarf/Makefile`、`examples/Makefile` 均无 `-l<lib>`，只用 libc / libc++；
- 源码 include 全部为系统头（`<cstddef>`、`<memory>`、`<map>`、`<string>`、`<vector>`、`<fcntl.h>` 等）；
- `elf/Makefile` / `dwarf/Makefile` 用 `python3 enum-print.py` 生成 `to_string.cc`，python3 与 make 属基础构建环境，不是库依赖。

因此 `w0-deps.txt` 记为 `none`。

## 编译步骤

```bash
# 配方按 commits/tarball 下载并解压（conan source），随后：
make CC=clang CXX=clang++ VER=0.3.r7.ge017276 -j1          # 构建 libelf++ / libdwarf++
cd test && bash ./test.sh                                   # 上游测试（见下）
```

配方内 `CC`/`CXX` 取自 `tools.build:compiler_executables`（R33），`VER` 供被补丁改写过的
`.pc` 规则使用（见补丁 0001/0004）。上游 Makefile 是递归 make，统一 `-j1`（R9）。

## 源码修改（4 个补丁，均为可移植性修复，不含平台宏）

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001 | `dwarf/Makefile` | `.pc` 规则改用传入的 `$(VER)`，不再调用 `git describe` |
| 0002 | `dwarf/dwarf.cc` | `move(entry.second)` → `std::move(...)`（1 处） |
| 0003 | `dwarf/line.cc` | `move(incdir)`、`move(file_name)` → `std::move(...)`（2 处） |
| 0004 | `elf/Makefile` | `.pc` 规则改用传入的 `$(VER)`，不再调用 `git describe` |

**0001/0004 的必要性**：上游 `.pc` 规则用 `git describe --match 'v*'` 取版本。release tarball
没有 `.git`，`git describe` 失败后 `Version:` 为空、`libdwarf++.pc` 还留下
`Requires: libelf++ = `；`examples/Makefile` 用 `pkg-config --cflags libelf++ libdwarf++`
构建 dump 工具，pkg-config 直接报
`Comparison operator but no version after package name 'libelf++'` 而失败 →
上游测试无法运行。

**0002/0003 的必要性**：clang 15 新增 `-Wunqualified-std-cast-call`，未限定的 `move()`
即告警；上游 Makefile 自带 `-Werror`，因此这三处告警直接变成编译错误。改动只是补
`std::` 限定，行为不变。

`test/test.sh` **未修改**：它是 `#!/bin/bash` 脚本，OHOS 上无 `/bin/bash`，因此配方用显式
解释器执行（候选顺序 `$CONFIG_SHELL` → `/data/service/hnp/bin/bash` → `/bin/bash` →
`/usr/bin/bash` → `PATH` 上的 `bash`），而不是依赖 `make check`（`make check` 用
`./test.sh` 直接 exec，shebang 找不到解释器会报 `No such file or directory`）。

## 测试

### 上游测试（recipe `build()` 内执行，10 例）

上游入口 `make check` → `test/test.sh`：先用 `pkg-config` 构建 `examples/` 下 5 个工具，
再对 2 个仓库自带 golden fixture 做输出对比：

- 工具: `dump-sections`、`dump-segments`、`dump-lines`、`dump-syms`、`dump-tree`
- fixture: `test/golden-gcc-4.9.2/example`（小端、DWARFv4）、`test/golden-gcc-6.2.1-s390x/example`（大端、DWARFv4）
- 计 5 × 2 = **10 例**，恰好覆盖 elf++ 与 dwarf++（DIE 树、行表）解析路径。

实测：10 PASS / 0 FAIL / 0 SKIP / 0 NOT_RUN（`conan create` 日志中逐行可见）。

### 消费测试（`test_package/`，15 项断言）

`test_libelfin.cc` 通过已安装的头文件与两个库解析自身镜像，断言 ELF 头类型/机器、
节表（`>10` 节、`.text` 非空）、符号表（`main` 为全局 FUNC）、dwarf++ 的
`section_type_to_name()` 映射与 section loader 对 `.debug_info`/`.debug_abbrev`/
`.debug_line`/`.debug_str` 的解析（13 项）；`test_package/conanfile.py` 另断言
随包安装的 `lib/pkgconfig/*.pc` 版本与 `Requires: libelf++ =` 依赖关系（2 项）。

> 仅用 section loader 而非完整 DWARF 解析的原因：libdwarf++ 只支持 DWARFv4，而
> clang 15 与 OHOS 系统库（musl crt 目标文件）产出 DWARF5（`DW_FORM_strx1` = 0x25），
> 解析自身镜像会抛 `format_error: unknown attribute form 0x25`。完整 DWARF 解析由
> 上游 golden fixture 用例覆盖（两者都是 DWARFv4）。

## 验证结果

```bash
conan create . --build=missing -c tools.build:jobs=2      # W3 / conan-verify 干净轮
# 上游测试：10 PASS / 0 FAIL；test_package：15/15 checks passed
```

打包产物（静态，默认 `shared=False`）：`lib/libelf++.a`、`lib/libdwarf++.a`、
`lib/pkgconfig/{libelf++,libdwarf++}.pc`、`include/libelfin/{elf,dwarf}/*.hh`、
`licenses/LICENSE`。

## 注意事项

- `shared=True` 时追加打包 `.so.0` 与 `.so`（上游 Makefile 总是同时产出静态与动态库）。
- `.pc` 文件由配方生成（`prefix=${pcfiledir}/../..`，可重定位），内容与上游 build tree
  中生成的两份一致；未使用 `make install`（其 `PREFIX=/` 形态会写出 `libdir=//lib`）。
- `libdwarf++` 的 `.pc` 带 `Requires: libelf++ = <version>`，两份 `.pc` 必须同装。
