# sjaakii 1.4.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-24
- 编译器: clang/clang++ 15.0.4（OHOS SDK aarch64）
- 状态: built

## 编译步骤

```bash
# conan 层（配方注入，见 conanfile.py generate()）
#   -DWANT_SSE42=OFF                    # 任务卡明令：aarch64 无 SSE，上游 option 默认 on
#   -DCMAKE_POLICY_VERSION_MINIMUM=3.5  # CMake 4.1.2 拒绝 cmake_minimum_required(2.8.12)
#   CFLAGS/CXXFLAGS=-O3 -pipe -DNDEBUG  # 止损#4：挡环境 CFLAGS 泄漏
#   CMAKE_INSTALL_PREFIX=<conan 包目录>  # 上游把 DATADIR 烘进二进制，须指向包目录 variants.txt 才可达
conan create . -pr:h=<abs>/ci/conan/profiles/ohos-aarch64 -pr:b=<abs>/ci/conan/profiles/ohos-aarch64
# 上游测试面（test_package/test_sjaakii.py 驱动）：
printf 'test movegen\nquit\n' | sjaakii     # 7 变体 perft 参考计数，72/72 位点全等 → "Ok."
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 configure 首行即败："Compatibility with CMake < 3.5 has been removed" | 上游 `cmake_minimum_required(VERSION 2.8.12)` | `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"`（须 cache_variables；tc.variables 写 toolchain 文件在该宏之后加载不生效，E321/DRAFT-E321） |
| 2 | generate 阶段硬错：`M_LIB` 被 used but set to NOTFOUND | musl/HarmonyOS 把数学函数并入 libc，`find_library(M_LIB m)` 必落空 | 补丁 0001：`if (NOT M_LIB) set(M_LIB "")` 守卫（fcl-0001-libm-optional 同型先例）；设备实测无 -lm 亦可链 sin 等符号 |
| 3 | conan 包目录下 `readline.h` 找不到（HAVE_READLINE 分支编译失败） | 上游 `FindReadline.cmake` 只 `set` 单数 `READLINE_INCLUDE_DIR`，而 CMakeLists 消费复数 `READLINE_INCLUDE_DIRS`（系统前缀 /usr/include 下恒成立所以未暴露） | 补丁 0002：FindReadline 内补 `set(READLINE_INCLUDE_DIRS ${READLINE_INCLUDE_DIR})` |
| 4 | 链接期 `undefined reference to tgetent/tgetflag/tgoto/tputs/BC/PC/UP` | 静态 `libreadline.a` 的 terminfo 后端符号在 ncurses（nm 实证 libncursesw.a 提供 `T tgetent`） | 补丁 0001：READLINE_FOUND 分支内 `find_library(NCURSES_LIBRARY NAMES ncursesw ncurses)` 并链（conan toolchain 已把 ncurses 包目录前置进 CMAKE_LIBRARY_PATH） |
| 5 | aarch64 上 `-msse4.2` 不可用 | 上游 `WANT_SSE42` option 默认 `on`，直接注入 `-msse4.2` 到 C/CXX/LINKER FLAGS | 配方 `tc.cache_variables["WANT_SSE42"]=False`（任务卡明令；embree `-DEMBREE_ISA_SSE42=OFF` 同型先例）；源码零 `_mm_`/intrinsics，popcount 走 `__builtin_popcountll` 可移植 |
| 6 | 版本 banner 误报 `(x86_64)` | 上游 ARCHSTR 按 `__LP64__` 判架构（LP64≠x86_64） | 补丁 0003：`__aarch64__||__arm__` 前置判为 `(aarch64)`；test_package 断言 banner 含 `(aarch64)` |
| 7 | DATADIR（`share/games/sjaakii/variants.txt` 运行时查找路径）烘死在 configure 期 `CMAKE_INSTALL_PREFIX` | 上游把 `-DDATADIR="${CMAKE_INSTALL_PREFIX}/..."` 写进编译宏 | 配方 generate() 把 `CMAKE_INSTALL_PREFIX` 指向 conan 包目录（cmake.install 的 --prefix 同值，宏与实物一致） |
| 8 | `--version` 打 "Unknown option" 到 stderr | 上游 argv 以 `strstr(argv[n],"-")` 兜底分支 `exit(0)` | **无需修**：exit(0) → conan-verify L2 平台冒烟天然通过（#95 aa3d 补丁不需要；trinculo 先踩后修的反面） |

## 源码修改

- `patches/0001-CMakeLists.txt.patch` — M_LIB 守卫 + 静态 readline 并链 ncurses（portability）
- `patches/0002-cmake-FindReadline.cmake.patch` — 复数 include 变量补齐（portability）
- `patches/0003-src-xboard.cc.patch` — ARCHSTR aarch64 判定（portability）

## 依赖版本

- readline/8.3（conan ohpcd 在档；transitive: ncurses/6.6）
- pod2man：系统自带 `/data/service/hnp/bin/pod2man`（绝对 shebang perl5.42.0，实跑 rc=0；convmv 同型）
- CMake 4.1.2 / GNU Make 4.4.1（设备与 CI worker 同源）

## 验证结果

```bash
# 上游测试面：test movegen（7 变体 perft 参考计数，Release 72 位点）
$ printf 'test movegen\nquit\n' | sjaakii
...（72 个 '.'）
Ok.
# 断言：rc=0、无 "*** Failed"、"Ok." 存在、连续点串=72、banner 含 1.4.1 与 (aarch64)
# 详细统计见 reports/test-report.md
```

## 注意事项

- 上游无 ctest/add_test/make check（CMakeLists 零测试注册）；测试面即引擎内置 `test movegen`。
- 源码 perft 参考数组另有 12 个 `#ifdef DEBUGMODE` 位点（WANT_ASSERT=off 上游默认不编译），计数时单列差额、不混入 72。
- `sjef` 裁判器随 WANT_REFEREE=on 一并构建（未 install，上游 install 仅 sjaakii）。
