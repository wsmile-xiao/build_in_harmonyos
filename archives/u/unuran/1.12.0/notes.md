# unuran 1.12.0 适配笔记

## 编译环境

- 目标：HarmonyOS PC / OHOS aarch64（clang 15，LP64，静态库）
- 构建系统：autotools（tarball 自带 `configure` 与全部 `Makefile.in`，**无需** autoconf/automake/perl）
- profile：`ci/conan/profiles/ohos-aarch64`
- 本地对照：WSL Ubuntu 22.04 + gcc 11.4（同样的目录布局与命令序列）

## 上游身份

- 名称/版本：UNU.RAN 1.12.0，`AC_INIT([unuran],[1.12.0],[unuran@statmath.wu.ac.at])`
- 主页：<https://statmath.wu.ac.at/unuran/>（**不在 GitHub 上托管**，发布在 statmath 的 SVN/快照）
- 许可：GPL-2.0-or-later（`COPYING` 随包发运）
- 形态：ANSI C 静态库，`libunuran.a` + 5 个公开头；ROOT 的非均匀抽样后端
- 测试：`tests/Makefile.am` 的 `check_PROGRAMS` 58 个自检程序，`TESTS = $(check_PROGRAMS)` 全量注册

## 编译步骤

```sh
./configure --enable-static --disable-shared          # E007 三元组 / E114 umask / shell_getcwd 已由配方改好
make -C scripts -j1                                   # 生成 src/utils/unur_fp_const_source.h（tarball 已有则为 no-op）
make -C src -j1
make -C tests check -j1                               # 上游 58/58
make -C src install -j1                               # DESTDIR=<package_folder>
```

顶层 `make` 与顶层 `make install` **都不能用**（见问题 3）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 报 `cannot guess build type; you must specify one` | OHOS 的 `uname -s` 是字面量 `HarmonyOS`，任何版本的原版 `config.guess` 都没有这个 case；同时 `config.guess` 的 libc 探测在 Linux 分支只会落到 `LIBC=gnu` 兜底，认不出 OHOS 的 libc | E007：配方内改写 `config.guess`，补 `#elif defined(__OHOS__) / LIBC=ohos` 与 `*:HarmonyOS:*:*)` case（见问题 2 的定位陷阱） |
| 2 | E007 补丁"打了等于没打" | unuran 用 `AC_CONFIG_AUX_DIR([autoconf])`，`config.guess` / `config.sub` 在 **`autoconf/`** 下，不在源码根。只往源码根找的补丁静默什么都没改，后续以问题 1 的表象失败 | 沿 `(".", "autoconf", "config", "build-aux", "scripts")` 依次探测；每处改写带 idempotent guard，anchor 未命中时 `output.warning` 而不是静默 |
| 3 | 顶层 `make` 在 `doc/` 上崩：`makeinfo: not found` | 顶层 `SUBDIRS = . scripts src examples experiments tests doc`，而 `doc/Makefile` 要用 texinfo 的 `makeinfo`；CI worker 的干净 PATH 里没有它，本包也不消费手册 | 分目录驱动（`make -C scripts` / `-C src` / `-C tests check` / `-C src install`）。**不能**用命令行 `SUBDIRS=...` 覆盖：它经 `MAKEFLAGS` 传进每一层 sub-make，会把 `src/`、`tests/` 自己的嵌套 `SUBDIRS` 也冲掉 |
| 4 | `configure` 的临时目录建出来不可写 | E114：HMDFS 强制目录 setgid，`umask 077 && mktemp -d ./confXXXXXX` 得到 `drwx--S---`，连 owner 都写不进去 | 把生成好的 `configure` 里 2 处 `umask 077` 改成 `umask 022`（a52dec/adcli/univalue/libxdg 同款） |
| 5 | 并行 make 挂在 jobserver FIFO | E074：OHOS worker 的 SELinux 策略拒绝 make 的 jobserver FIFO | 所有 make 调用带 `-j1` |
| 6 | 误以为需要 perl | `src/unuran.h`（tarball 内已生成）比 `src/unuran.h.in` **新**，`merge_h.pl` 根本不会被调用 | 比较这两个文件的时间戳即可判定；本包全程不调用 perl，也不 `tool_requires` perl |
| 7 | 多线程消费 `unur_sample_cont` 结果错乱 | 库内置 URNG 的状态是 `src/uniform/mrg31k3p.c` 里的**文件级 static**（`x10/x11/x12`…），全进程只有一条流：`unur_gen_seed(a,S)` 会重置整条全局流，两个默认配置的生成器无法从两个线程驱动 | 消费者必须给每个生成器一个自己的源：`unur_urng_new(你的函数, 你的状态)` → `unur_makegen_ssu("normal(0,1)","tdr",urng)`。test_package 的 group 2 把这个"进程级单流"属性写成可观测断言，group 6 演示 4 线程各持一个源 |
| 8 | `make -C src` 链接 `libunuran.la` 时 `llvm-ar: error: unable to load '/methods/.libs/libmethods.a'`（`src/Makefile:494`）；稍早还会先冒出 `libtool: warning: cannot determine absolute directory name of 'specfunct'` | `[shell_getcwd]`：HMDFS 下 conan build 树的父目录链对 `getcwd()` 不可达，shell 的 `pwd` 于是返回**空串**。libtool 用 `abs_ladir=\`cd "$ladir" && pwd\``（`autoconf/ltmain.sh:8418`）和 `my_xabs=\`pwd\`"/$my_xlib"`（:5531）把 `src/Makefile.am` 里**全部相对**的 `SUBLIBS = methods/libmethods.la …` 折成绝对路径，空串让 `my_xabs` 退化成 `/methods/.libs/libmethods.a`；`tests/Makefile.am` 的 `LDADD` 同样相对，一样中招。只有**以 `.la` 为参数**的那条路径要绝对目录，`.lo/.o` 参数不需要 | 三重兜底（adms 2.3.7 / nspr 4.37 / aribb24 1.0.4 先例）：① `build()` 里 `os.chdir(self.build_folder)` 固定进程 cwd；② 导出 `os.environ["PWD"]`，并在每次 `make -C <子目录>` **之前**用 `_enter_subdir()` 把 PWD 同步到该子目录（bash 启动时若 `getcwd()` 失败，会退用绝对、存在且与 `.` 同一 inode 的 `$PWD`；`make -C` 只 chdir 不改 PWD，所以必须手动同步）；③ 改写 `configure` 的 `ac_pwd=\`pwd\` && test -n "$ac_pwd" &&` 为 `ac_pwd=\`pwd\` 2>/dev/null || ac_pwd="$PWD"` + 新行 `test -n "$ac_pwd" &&`，让 configure 顶部那条 `working directory cannot be determined` 判定也能过 |

## 源码修改

**无 `patches/`**。上游源码一行未改：

- E007 的三元组改写、E114 的 `umask` 改写、`[shell_getcwd]` 的 `ac_pwd` 回退都作用在 **tarball 已生成的 `configure` / `autoconf/config.guess`** 上，属于"构建期注入"而非"源码补丁"，因此放在 `conanfile.py` 的 `build()` 里、不落 `patches/`；
- 三者都是 idempotent 的（已存在/已改写则跳过），重复执行安全。

## 依赖版本

- 无第三方运行时依赖：`libunuran.a` 只依赖 libc 与 libm（`cpp_info.system_libs = ["m"]`）。
- 无 `tool_requires`：tarball 自带 `configure` / `Makefile.in`，不需要 autoconf/automake；也不需要 perl（见问题 6）或 texinfo（见问题 3）。

## 验证结果

上游回归套件（`make -C tests check`，automake parallel-tests）：

```
=========================================
   unuran 1.12.0: tests/test-suite.log
=========================================
# TOTAL: 58
# PASS:  58
# SKIP:  0
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0
```

`build()` 内用 `_emit_upstream_test_result()` 直接解析这份 `test-suite.log` 并打出
`HMBS_UPSTREAM_TEST_RESULT=` 标记（数字取自框架，不取自配方估算）。

> 复测注意：在一个**已有**各用例 `.log` 的目录里重跑 `make check`，automake 会把
> 它们当作 up-to-date 跳过，TOTAL 因此低于真实值（实测 57 vs 58）。所有数字都必须
> 来自干净的构建树 —— `conan create` 每次都给一棵干净树。

消费者侧（WSL gcc 11.4，只用已安装的 5 个头 + `libunuran.a`）：

```
ALL PASS: unuran 1.12.0 consumer checks (6 groups)
RUN_EXIT=0
```

安装布局（`make -C src install` 的实际产出）：

```
include/unuran.h
include/unuran_tests.h
include/unuran_urng_gsl.h
include/unuran_urng_prng.h
include/unuran_urng_rngstreams.h
lib/libunuran.a
lib/libunuran.la        ← package() 里删除（内嵌绝对构建路径）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 自包含 autotools 配方（AUX_DIR 定位的三元组改写 + umask 改写 + 分目录构建 + `make -C tests check` 实跑 + `test-suite.log` 解析） |
| conandata.yml | 官方 URL + SHA-256；无 patches |
| test_package/ | 消费者测试 `test_unuran.c`（6 组 86 条断言，含 2 组鸿蒙特有）+ CMakeLists + conanfile + MANIFEST.yml |
| manifest.yaml / notes.md | 版本元数据与适配笔记 |
| knowledge/drafts/DRAFT-unuran-1.12.0-*.{md,kv} | 知识库扩展草稿 |

## 注意事项

- 任务路径：【知识库扩展】。新增知识条目见
  `knowledge/drafts/DRAFT-unuran-1.12.0-configure-auxdir-triplet-patch-and-doc-subdir-make.{md,kv}`，
  主题为「已带 `configure` 的 autotools 包在 OHOS 上的最小构建路径：AUX_DIR 里找
  helper、半量 E007、别让顶层 make 进 doc/」。
- rule4 口径：unuran 不在 GitHub 托管，没有"默认分支"可扫，故以钉版 tarball 的
  `tests/Makefile.am` 为准并取朴素行扫描的**上限**：以 ` t_` 开头的行 **109** 行
  （`check_PROGRAMS` 段 55 行 + `EXTRA_DIST` 段 54 行），去重标识符 **62** 个（58 注册 + 2 deprecated 门控 + 2 Mathematica 门控）。
  真实可执行 **58**（= `check_PROGRAMS`），未执行 **0**。差额是同一程序在
  `EXTRA_DIST` 里按 `t_<name>.conf`（参考数据文件）重复列名，以及 2 个
  `t_deprecated_*`（`ENABLE_DEPRECATED` 门控）与 2 个 Mathematica 程序
  （`HAVE_MATHEMATICA` 门控）——上游默认配置下这两个变量为空，不注册。
  适配后 N' = 58 实跑 + 86 条 test_package 断言 = **144 ≥ 109**，无减少。
- 库名与链接：`cpp_info.libs = ["unuran"]`（产物 `libunuran.a`），
  `system_libs = ["m"]` —— 拒绝/反演内核要 `log/exp/pow/sqrt`，静态消费必须带 `-lm`。
- `unur_get_genid()` 返回的是 **`METHOD.serial`**（如 `TDR.001`、`DARI.003`），
  不是分布名；连续型标准分布默认落到 TDR，Poisson 落到 DARI。test_package 的断言
  按这个实际契约写（`strchr(id,'.')` + 前缀匹配），不是按分布名匹配。
- 内置 `unur_urng_MRG31k3p` **不提供**种子/复位回调（`unur_urng_seed()` /
  `unur_urng_reset()` 对它返回 "missing functionality"）；需要可复现流时请用
  `unur_urng_new()` 自带源。

---

**编译结束**: 2026-09-20
**最终状态**: built
