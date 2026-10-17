# lrslib 0.73 适配笔记（HarmonyOS PC · 手写 makefile + Conan）

## 编译环境
- 构建系统: makefile（上游手写 `makefile`，**没有** configure / CMake / meson / autotools）
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，target `aarch64-unknown-linux-ohos`）
- 状态: built

## 上游形态

| 项 | 值 |
|---|---|
| 上游版本串 | `VERSION "v.7.3_2024.5.30"`（`lrslib.h:3`），Conan 版本目录用 `0.73` |
| 源码包 | `lrslib-073.tar.gz`（顶层目录 `lrslib-073/`，364 个成员） |
| 构建目标 | `all-shared` = `liblrs.so.1.0.0`（SONAME `liblrs.so.1`）+ `lrs-shared` + `lrsnash-shared` |
| 依赖 | gmp（`-lgmp`，`INCLUDEDIR`/`LIBDIR`/`SHLIBFLAGS` 三个 make 变量） |
| 上游 install | `install: all-shared install-common`，用 `install -t` 落 `bin/` 与 `lib/`，头落 `include/lrslib/` |

`liblrs.so` 里同时装着**三套算术后端**（64bit / 128bit / GMP），靠调用方编译宏经
`lrslib.h` 的 `suf()` 选出符号后缀。消费者必须显式选一套，本包的 test_package 选 GMP 后端
（`-DMA -DGMP`）。

## 编译步骤

```sh
make -j2 CC=<clang> \
  CFLAGS="-O3 -Wall -Ilrsarith-011/ -I<gmp>/include -L<gmp>/lib" \
  INCLUDEDIR=<gmp>/include LIBDIR=<gmp>/lib SHLIBFLAGS=-L<gmp>/lib \
  all-shared
```

`package()` 里用 `copy()` + `os.symlink()` 复刻上游 install 布局（**不调用 `make install`**，
理由见下），并补 `redund`/`minrep`/`fel` 三个 argv[0] 别名符号链接（`redund(1)` 明写
「redund and minrep are aliases to lrs」）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make all-shared` 在链 `liblrs.so.1.0.0` 时报 `ld.lld: error: unable to find library -lgmp` | 上游 `${SHLIB}` 规则是 `$(CC) -shared -Wl,-soname=$(SONAME) $(SHLIBFLAGS) -o $@ ${SHLIBOBJ} -lgmp`，**没有 `-L${LIBDIR}`**；`-L` 只能从 `SHLIBFLAGS` 进 | 配方传 `SHLIBFLAGS=-L<gmp>/lib` |
| 2 | `lrsnash-shared` 同样报找不到 `-lgmp` | 该规则是 `$(CC) ${CFLAGS} -DGMP -DMA ... -o $@ -L . -llrs -lgmp`，同样没有 `-L${LIBDIR}` | 依赖库目录一并放进 `CFLAGS`（`-L<gmp>/lib`；纯编译步骤会打 `argument unused during compilation` 噪声，属正常） |
| 3 | **`ine/test/` 30 个上游回归输入里 6 个 rc=139（SIGSEGV）** | 溢出重启的临时文件模板写死 `/tmp/lrs_restartXXXXXX`，`mkstemp()` 在只读 `/tmp` 上失败；随后 stage-2 清理仍带着 `P == NULL` 进 `lrsv2_main` 解引用 | 补丁把两处模板改为 `$TMPDIR` 优先、`/tmp` 兜底；并在 stage 0 返回 `-1` 时 `exit(1)` 而不是继续清理 |
| 4 | **裸环境下 `bin/lrs` / `bin/lrsnash` 报 `Error loading shared library liblrs.so.1`（rc=127）** | 上游两条可执行文件链接规则完全没有 RUNPATH 挂钩，install 后 `bin/` 找不到 `lib/` 里的库；而 `test_package` 在 `conanrun` 下跑是**假绿**（conanrun 注入 `LD_LIBRARY_PATH`） | makefile 加 `RUNPATHFLAGS ?= -Wl,-rpath,'$$ORIGIN/../lib'` 并挂到 `lrs-shared` / `lrsnash-shared` 两条链接规则 |
| 5 | **`bin/lrs --version` / `--help` 退出码非 0（修前 rc=139）**，L2 会因此对全部 5 个交付可执行文件判红 | `lrs` 把每个参数当输入文件名；`redund`/`minrep`/`fel` 又是同一二进制的 argv[0] 别名，一次缺陷波及 5 个产物 | 补丁在 `lrs.c` / `lrsnash.c` 的 `main()` 开头处理 `--version`/`--help` 并 `return 0` |
| 6 | 本包自建全绿、**消费者**编译报 `'gmp.h' file not found` | `lrslib.h → ARITH("lrsgmp.h") → <gmp.h>`，`gmp.h` 属公开头链 | `self.requires("gmp/6.3.0", transitive_headers=True)` |
| 7 | `make install` 报 `install: inaccessible or not found` | 平台没有 `install` 命令（toybox/HNP 都没有），上游 install 规则依赖 `install -t` | 不调用 `make install`，`package()` 里复刻布局 |
| 8 | conan 默认 `tools.build:jobs = os.cpu_count()` = 20，手写 makefile 无自限 | 设备 8–20 核共享 | 配方从 `tools.build:jobs` 取 jobs（默认 2）并显式 `make -j{jobs}` |
| 9 | `mit.ine` 单例耗时约 210 s | 上游最大回归题（4862 顶点 / 1375608 基） | 逐用例超时预算 900 s；在 `_UPSTREAM_NO_TOTALS` / `_UPSTREAM_REFERENCE` 里显式登记每例的判据 |

## 源码修改

`patches/0001-runtime-and-cli-conventions.patch`（单文件，改 4 个上游文件，**不含任何平台宏**）：

| 文件 | 修改 |
|---|---|
| `lrslib.c` | 两处 `mkstemp` 模板改为 `$TMPDIR` 优先 / `/tmp` 兜底（并补 `#include <stdlib.h>`） |
| `lrs.c` | `main()` 增加 `--version`/`-V` 与 `--help`/`-h` 处理（`return 0`）；stage 0 返回 `-1` 时 `exit(1)`，不再解引用 NULL |
| `lrsnash.c` | `main()` 增加 `--version`/`-V` 处理（`return 0`） |
| `makefile` | 新增 `RUNPATHFLAGS ?= -Wl,-rpath,'$$ORIGIN/../lib'`，挂到 `lrs-shared` 与 `lrsnash-shared` 两条链接规则 |

补丁对 `git apply -p1` 与 `patch -p1` 均 `--check` 通过（在原版解包树上实测）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|---|---|---|
| gmp | `gmp/6.3.0` | ohpcd 制品仓；该包**只提供 `libgmp.a`（静态）**，故 GMP 代码被静态并入 `liblrs.so`，`readelf -d` 里 `liblrs.so.1` 的 `NEEDED` 只有 `libc.so` |

## 上游测试

上游**没有任何测试框架**：`grep -nE '^(check|test|all|default):' makefile` 只命中
`default: lrs lrsgmp`，也没有 CTest / Meson / pytest 注册面。上游自带的回归面是
**数据驱动**的：`ine/test/` 目录下每个 `.ine` 文件就是一道完整枚举问题，配一次 `lrs` 运行。

清点（候选数法，单位互不混用）：

| 候选面 | 计数 | 是否采用 |
|---|---|---|
| `ine/test/*.ine` | **30** | ✅ 采用（目录名即 test，被审版本自带回归输入） |
| `ine/test-072/*.ine` | 7 | ❌ 7.2 版回归集（属上一版本）；抽测 4 例（bv7/fq48-19/m6/mit）各 180 s 均未跑完 |
| `ine/test-062/*.ine` | 9 | ❌ 6.2 版回归集（属上上版本） |
| `ine/test-062/normaliz/*.in`(10) + `porta/*`(10) | 20 | ❌ 第三方工具（Normaliz / PORTA）格式，`lrs` 不可运行 |
| `ext/test/*.ext` | 12 | ❌ 期望输出/对照产物，不是可运行用例 |
| `ine/redund/*`(23) / `ext/redund/*`(19) / `ine/project/*`(36) | 78 | ❌ 上游示例数据集，不在 `test` 目录下 |
| `ine/**/*.ine`(112) / `ext/**/*.ext`(33) | 145 | ❌ 示例数据集全量，不是测试注册面 |

**声明 N = 30**（单位：上游测试输入问题 = `ine/test/*.ine`，每个文件一次 `lrs` 运行）。
`ext/test/cube.ext`(8 行) 与 `ext/test/tsp5.ext`(12 行) 作为**独立 oracle** 参与断言
（`Mit.ext`/`mp5.ext` 来自另外的（更早的）问题文件，**不**用作 oracle——设备文件系统
大小写不敏感，盲目按 `mit` → `Mit.ext` 查表会静默比错文件）。

逐例判据：
1. 退出码 0，且
2. 输出里有该例的 `*Totals:` 行（`cp4`/`ep`/`inf`/`left`/`right` 五例属转换/无解模式，
   天然无 `Totals` 行，已在配方里显式登记，逐例在设备上核对过），
3. `cube`/`tsp5` 额外与上游参考输出的行数比对。

实测结果见 `reports/test-report.md` 与 PR 正文（N / N′ / 通过率同源同单位）。

## 验证结果

```sh
# RUNPATH / SONAME（每个交付 ELF 都查）
llvm-readelf -d <pkg>/lib/liblrs.so.1.0.0 | grep -E 'SONAME|NEEDED'
llvm-readelf -d <pkg>/bin/lrs           | grep -E 'RUNPATH|NEEDED'
# 裸环境冒烟（不带 conanrun —— 这是唯一能证 RUNPATH 的跑法）
env -u LD_LIBRARY_PATH <pkg>/bin/lrs --version
env -u LD_LIBRARY_PATH <pkg>/bin/redund --version
env -u LD_LIBRARY_PATH <pkg>/bin/lrs <src>/ine/test/cube.ine | grep Totals
```

## 注意事项

1. **不要用 `conanrun` 下的运行结果证明「可执行文件能跑」**：conanrun 注入
   `LD_LIBRARY_PATH`，RUNPATH 错成什么样都能装载成功。判据必须是
   `env -u LD_LIBRARY_PATH <pkg>/bin/<tool> ...`。
2. 本包**只出共享库**（`shared=False` 会抛 `ConanInvalidConfiguration`）：上游 makefile
   只有 `all-shared` 目标，没有静态库目标。
3. `mplrs` / `mplrsgmp`（MPI 并行版）**未构建**：需要 `mpicc` 与 OpenMPI，平台工具链不含。
   上游 `default: lrs lrsgmp` 同样不含它们；本包交付的 `lrs` 是非 OpenMP 的共享库版本
   （与上游 `install` 目标一致）。`plrs/lrs` 的 `-fopenmp` 变体需要 libomp，未纳入。
4. 消费者要自己选用哪套算术后端：`-DMA -DGMP`（GMP，本包 test_package 用）、
   `-DMA -DB128 -DLRSLONG`（128bit）或 `-DMA -DLRSLONG`（64bit）。
5. `lrs` 的选项写在**输入文件里**（`begin` 行之前的 `redund`/`minrep`/`fel`/`testlin` 等），
   不是命令行开关；`--version`/`--help` 是本包补丁新增的两个例外。
