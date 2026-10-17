# lrs 073.a 适配笔记（HarmonyOS PC · 上游 7.3a bug-fix · 手写 makefile + Conan）

## 任务信息

| 项 | 值 |
|---|---|
| 平台任务 | `lrs` `073.a`（智能任务平台 id 8566，分支 `feat/lrs-073.a`） |
| 上游项目 | lrslib（David Avis，McGill 大学） |
| 本包 Conan 名 | `lrs/073.a`（平台任务名即 `lrs`；上游项目/源码包名为 `lrslib`） |
| 上游发布 | 7.3a（`lrslib-073a.tar.gz`，2025-10-10） |
| 上一版适配 | `lrslib/0.73`（已合入 main，PR !11595，路径 B）——本包是该配方的 7.3a 升级重打包 |

## 编译环境
- 构建系统: makefile（上游手写 `makefile`，**没有** configure / CMake / meson / autotools）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4（Harmonybrew ohos-sdk@26.0.0.18；target `aarch64-unknown-linux-ohos`）
- 状态: built

## 上游形态

| 项 | 值 |
|---|---|
| 上游版本串 | `VERSION "v.7.3_2024.5.30"`（`lrslib.h:3`，073a 未改版本串），README 写 Version 7.3a |
| 源码包 | `lrslib-073a.tar.gz`（sha256 `7fb16ad5…`，顶层目录 `lrslib-073a/`） |
| 与 073 的差异 | 仅 `README`（版本 7.3a + "2025.10.10 Minor patch to fix errors when compiling with gcc 15"）与 `lrslib.c`（`timecheck`/`checkpoint`/`die_gracefully` 原型与定义补 `int` 形参，gcc 15 需要）；其余 327 个文件逐字节相同 |
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

`package()` 里用 `copy()` + `os.symlink()` 复刻上游 install 布局（**不调用 `make install`**），
并补 `redund`/`minrep`/`fel` 三个 argv[0] 别名符号链接（`redund(1)` 明写
「redund and minrep are aliases to lrs」）。

## 遇到的问题与解决方案

本包是 `lrslib/0.73` 的 7.3a 升级；0.73 适配中定位的四类确定性缺陷在 073a 中**全部原样存在**
（逐项复核：`mkstemp` 模板仍在 `lrslib.c:1423`、`lrslib.c:6976`；`makefile` 链接规则仍无
RUNPATH；`lrs.c`/`lrsnash.c` 仍不认 `--version`/`--help`），故沿用同一组修复。

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | **`ine/test/` 上游回归输入在只读 `/tmp` 上崩溃（rc=139）** | 溢出重启的临时文件模板写死 `/tmp/lrs_restartXXXXXX`，`mkstemp()` 在只读 `/tmp` 上失败；随后 stage-2 清理仍带着 `P == NULL` 进 `lrsv2_main` 解引用 | 补丁把两处模板改为 `$TMPDIR` 优先、`/tmp` 兜底；并在 stage 0 返回 `-1` 时 `exit(1)` 而不是继续清理 |
| 2 | **裸环境下 `bin/lrs` / `bin/lrsnash` 报 `Error loading shared library liblrs.so.1`（rc=127）** | 上游两条可执行文件链接规则完全没有 RUNPATH 挂钩，install 后 `bin/` 找不到 `lib/` 里的库；而 `test_package` 在 `conanrun` 下跑是**假绿**（conanrun 注入 `LD_LIBRARY_PATH`） | makefile 加 `RUNPATHFLAGS ?= -Wl,-rpath,'$$ORIGIN/../lib'` 并挂到 `lrs-shared` / `lrsnash-shared` 两条链接规则 |
| 3 | **`bin/lrs --version` / `--help` 退出码非 0**，L2 会因此对全部 5 个交付可执行文件判红 | `lrs` 把每个参数当输入文件名；`redund`/`minrep`/`fel` 又是同一二进制的 argv[0] 别名，一次缺陷波及 5 个产物 | 补丁在 `lrs.c` / `lrsnash.c` 的 `main()` 开头处理 `--version`/`--help` 并 `return 0`（横幅按本版更新为 `lrslib 7.3a`） |
| 4 | 本包自建全绿、**消费者**编译报 `'gmp.h' file not found` | `lrslib.h → ARITH("lrsgmp.h") → <gmp.h>`，`gmp.h` 属公开头链 | `self.requires("gmp/6.3.0", transitive_headers=True)` |
| 5 | `make all-shared` / `lrsnash-shared` 报 `ld.lld: error: unable to find library -lgmp` | 两条规则都不带 `-L${LIBDIR}`；`-L` 只能从 `SHLIBFLAGS` / `CFLAGS` 进 | 配方传 `SHLIBFLAGS=-L<gmp>/lib`，并把 lib 目录一并放进 `CFLAGS` |
| 6 | `make install` 报 `install: inaccessible or not found` | 平台没有 `install` 命令（toybox/HNP 都没有），上游 install 规则依赖 `install -t` | 不调用 `make install`，`package()` 里复刻布局 |
| 7 | conan 默认 `tools.build:jobs = os.cpu_count()` = 20，手写 makefile 无自限 | 设备多核共享 | 配方从 `tools.build:jobs` 取 jobs（默认 2）并显式 `make -j{jobs}` |
| 8 | `mit.ine` 单例耗时约 210 s | 上游最大回归题 | 逐用例超时预算 900 s；在 `_UPSTREAM_NO_TOTALS` / `_UPSTREAM_REFERENCE` 里显式登记每例的判据 |

## 源码修改

4 个补丁（`refresh-patch --auto` 从 `.orig`/`.work` 生成，**不含任何平台宏**）：

| 文件 | 修改 |
|---|---|
| `patches/0001-lrs.c.patch` | `main()` 增加 `--version`/`-V` 与 `--help`/`-h` 处理（`return 0`）；stage 0 返回 `-1` 时 `exit(1)`，不再解引用 NULL |
| `patches/0002-lrslib.c.patch` | 两处 `mkstemp` 模板改为 `$TMPDIR` 优先 / `/tmp` 兜底（并补 `#include <stdlib.h>`） |
| `patches/0003-lrsnash.c.patch` | `main()` 增加 `--version`/`-V` 处理（`return 0`） |
| `patches/0004-makefile.patch` | 新增 `RUNPATHFLAGS ?= -Wl,-rpath,'$$ORIGIN/../lib'`，挂到 `lrs-shared` 与 `lrsnash-shared` 两条链接规则 |

相对 `lrslib/0.73` 的补丁，仅把新增横幅的版本串由 `7.3` 更新为 `7.3a`；其余 hunk 原样
适用（073a 的改动离补丁区域很远）。

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
   天然无 `Totals` 行，已在配方里显式登记），
3. `cube`/`tsp5` 额外与上游参考输出的行数比对。

实测结果见 `reports/test-report.md` 与 PR 正文（N / N′ / 通过率同源同单位）。

## 验证结果

```sh
# 裸环境（不 source conanrun），证明 RUNPATH 与 CLI 补丁
<put>/bin/lrs --version        # lrs (lrslib 7.3a)
<put>/bin/lrsnash --version    # lrsnash (lrslib 7.3a)
<put>/bin/lrs <cube.ine>       # *Totals: vertices=8 ...
```

（本地 conan-verify / W3 本地 CI 的完整读数与日志见 `reports/test-report.md` 与
`reports/conan-verify-report.md`。）

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/liblrs.so.1.0.0` + `liblrs.so.1`/`liblrs.so` | C 库（三套算术后端，SONAME `liblrs.so.1`） |
| `bin/lrs`, `bin/lrsnash` | 命令行工具（`lrs` 另以 argv[0] 提供 `redund`/`minrep`/`fel`） |
| `include/lrslib/*.h` | 公开头 |

## 注意事项

- 运行时让 `TMPDIR` 指向可写目录（`lrs` 的 stdin 暂存与 64/128bit 溢出重启都用 `mkstemp`）。
- `lrs` 的选项写在输入文件里（`begin` 行之前），命令行只接输入/输出文件名与
  `--version`/`--help`。

**编译结束**: 2026-09-26
---

**编译结束**: 2026-09-26 14:19
**最终状态**: built
