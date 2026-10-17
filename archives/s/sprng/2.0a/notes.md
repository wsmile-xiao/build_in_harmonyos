# 编译笔记 — sprng 2.0a

**软件名称**: sprng（Scalable Parallel Random Number Generator libraries）
**版本**: 2.0a
**编译日期**: 2026-09-24
**编译状态**: built ✅
**任务卡**: 10876（积分赛）

---

## 软件简介

SPRNG 是 NCSA/Indiana 的并行随机数库（C/C++/FORTRAN），提供 6 个生成器：
LFG（0）、LCG（1）、LCG64（2）、CMRG（3）、MLFG（4）、PMLCG（5）。
纯 C 实现，1999 年代码，构建体系为 `make.$(PLAT)`。

**源码地址**: https://archive.ubuntu.com/ubuntu/pool/universe/s/sprng/sprng_2.0a.orig.tar.gz
（sha256 `bcfa9e05…b937454e`；上游官方三站 2026-09-24 实测 http/https 全部
返回码 000 不可达，四路镜像 sha256 全等 + Debian `.dsc` Checksums-Sha256 锚定）

---

## 构建配置：为什么必须 `PLAT=GENERIC`（任务卡依据）

1. 顶层 `Makefile`：`include make.CHOICES` → 再 `include $(SRCDIR)/make.$(PLAT)`。
   **上游默认 `PLAT = INTEL`**。
2. `SRC/make.INTEL` 硬写 MPI 面：`MPICC = mpicc`、`MPIF77 = mpif77`、
   `MPIDIR = -L/usr/local/mpi/build/LINUX/ch_p4/lib`、`MPILIB = -lmpich`、
   `CFLAGS … -I/usr/local/mpi/include`。
3. 设备/环境实测：`mpicc`/`mpirun` 不在 PATH，`/usr/include/mpi.h`、
   `/data/service/hnp/include/mpi.h` 皆不存在 ⇒ **无 MPI 环境**。
4. `make.CHOICES` 里 `#MPIDEF = -DSPRNG_MPI` 默认注释（非 MPI 构建），
   但只要 PLAT 停在 INTEL 就会去 `-I/usr/local/mpi/include`、链接 `-lmpich`。

⇒ 本配方**显式 `PLAT=GENERIC`**（make 命令行 + 补丁把 make.CHOICES 默认值一并
改成 GENERIC 双保险；命令行变量随 MAKEFLAGS 传遍 SRC/TESTS/各生成器子 make）。
`make.GENERIC` 的 `MPIDIR`/`MPILIB` 为空、`CFLAGS` 不含 MPI 路径 ⇒ MPI 彻底排除。

### CFLAGS 落点实测（先测哪个变量吃 CFLAGS）

`TESTS/Makefile`、`EXAMPLES/Makefile`、`SRC/Makefile`、`SRC/<gen>/Makefile`、
`SRC/sprng/Makefile` **全部 include 同一个 `SRC/make.GENERIC`**，编译行统一是
`$(CC) -c $(CFLAGS) …`、链接行 `$(CLD) $(CLDFLAGS) …` ⇒ **flags 面 = 这两个
Makefile 变量**。补丁把它们钉成 `CFLAGS = -O3 -pipe -DNDEBUG $(PMLCGDEF) $(MPIDEF)
$(CPPFLAGS)`、`CLDFLAGS = -O3 -pipe -DNDEBUG $(LDFLAGS)`：既钉死优化旗标（不泄漏
外部 `CFLAGS` 环境），又保留 `$(PMLCGDEF)`（上游默认 `-DUSE_PMLCG`，丢了会让
pmlcg 从分发表消失）与注入口 `$(CPPFLAGS)/$(LDFLAGS)`（供配方注入 conan gmp 的
头/库路径）。同款做法先例：Debian 在同一文件注入 `-fpic ${GMPDEF}
${compilerflags}`。

---

## 测试面与判据（四口径不混用）

| 口径 | 取值 | 取数命令 |
|---|---|---|
| 源码宏数 | 不适用（无测试注册宏） | — |
| **框架注册数（本任务 N）** | **13** | `grep -n '^TESTLIST' TESTS/Makefile` → `TESTLIST = maxt collisions equidist serial gap perm runs coupon poker sum random_walk wolff metropolis` |
| assertion 数 | 见 `test_package/MANIFEST.yml` `assertion_count` | 消费者断言另计 |
| 消费者断言 | 8 | `test_package/test.c` |

* `fft` **不在** `TESTLIST` 内，且其链接面需要 SGI 专有库
  （`-lcomplib.sgimath -lftn`）⇒ 不属本任务测试面，**如实记录不运行**。
* 上游**没有** `make check` 目标（`Makefile` 只有 `all/src/examples/tests/clean/realclean`）；
  质量测试由 `make -C TESTS` 构建为 `TESTLIST` 中每项一个 `<name>.sprng` 可执行。

### 命令行约定（实测推导，README + 源码双证）

```
<test> rng_type nstreams ncombine seed param tests_per_stream skip <test_arguments>
```
`rng_type ∈ [0,5]`、`ncombine>0`、`tests_per_stream>0`（`TESTS/init_tests.c` 校验）；
`N_STREAM_PARAM=7`。wolff/metropolis 不走 `init_tests`，独立解析：
`<test> rng_type seed param lattice_size block_size discard_blocks use_blocks`
（lattice 必须=16、`use_blocks` 必须为 10 的幂、coupon 要求 `t>d`——均为实测踩到后按
上游校验信息改正）。

### 确定性种子（seeds 判据）

* 种子**完全来自命令行** `argv[4]`；`TESTS/*.c` 中**没有** `time()`/`srand()` 调用
  （`time()` 只出现在 `SRC/makeseed.c` 的 `make_sprng_seed()`，质量测试不调用）
  ⇒ **固定 seed 即结果可复算**。
* 本轮固定：`seed=1234567`、`nstreams=10`、`ncombine=1`、`param=0`、
  `tests_per_stream=10`、`skip=0` ⇒ `NTESTS = n*tests_per_stream = 100` 组统计量，
  再做 KS 检验。
* 统计判据（**如实记**）：各测试输出的 p 值/百分数落 **[0.5%, 99.5%]** 记 PASS。
  本轮实测 13/13 全部落区间（最小 runs=3.68%、最大 sum=96.23%）。若某项设备相关
  超界，按实测如实记为 FAIL，不改判据。

### rc 不可作判据（重要）

上游 8 个测试是 `void main`（equidist/gap/perm/runs/serial/wolff/metropolis/fft）、
6 个是 K&R `main(argc,argv)` 隐式 int 且**成功路径无 `return`** ⇒ 进程返回值未定义。
设备实测：`equidist/gap/runs` 成功却 rc=8、`wolff/metropolis` 成功却 rc=72，
而结果行完整、统计值正常。usage 错误路径走 `exit(-1)/exit(1)` ⇒ rc=255/1 有意义。
⇒ **判据 = 输出断言（结果行存在 + 统计值落接受域），rc 原样留档，不改上游测试源码**。
（改 `void main → int main` 会让 13 个文件产生与平台无关的 diff，属“改测试凑绿”风险面，
故不动；此项在 `reports/test-report.md` 与 PR 正文均注明。）

### checksprng（上游可移植性自检，18 项）

`make -C SRC checksprng_c_exec CHECKSPRNG_LIB=sprng` 构建 + 运行：
**17 PASSED / 1 FAILED**。唯一 FAILED = `pmlcg: Simple C interface`，根因已 A/B 定位：

* `SRC/memory.c` 的 `_mymalloc` 对 `size==0` **显式 `return NULL`**；
* `pmlcg init_rng` 里 `mpz_init_set_ui(&k, gennum)`，**gennum==0 ⇒ k=0 ⇒ GMP
  `_mp_alloc=0`**（实测 gmp 6.3.0：`mpz_init` 后 `alloc=0 size=0`）；
* `pmlcg_unpack_rng` 用 `mymalloc(q->k._mp_alloc*sizeof(mp_limb_t))` = `mymalloc(0)`
  → NULL → `unpack_rng` 返回 NULL → 该自检的 pack/unpack 段判 FAILED。

**定性：上游固有缺陷、平台无关**（判据：`_mymalloc` 的 size==0 分支与 GMP 的
`_mp_alloc=0` 语义都不依赖 OS/架构）。同一程序的 *Default* 接口之所以 PASSED，
是因为它 pack 的是 **spawn 出来的流（gennum≠0）**，k≠0、alloc>0——自洽解释。
**处置：不修库语义**（改 pack/unpack 会改变库行为且无上游背书），如实记录、
入 notes 与知识草稿；质量测试面（TESTS 13 项）不涉及 pack/unpack，故不受影响。

---

## 编译过程

### 构建系统：`make.$(PLAT)`（custom）

无 `configure`/`CMakeLists`，**自定义 `build()` 直调 make**（指望 autotools/cmake
入口必失败）。命令形如：

```bash
make -j1 PLAT=GENERIC CC=/data/service/hnp/bin/clang AR=… RANLIB=… \
     CPPFLAGS='-I<conan gmp>/include' LDFLAGS='-L<conan gmp>/lib' -C SRC
make -j1 <同上> -C TESTS
```

`CC/AR/RANLIB` 显式绝对路径（裸命令名在设备子进程无 PATH 搜索的族例）；
`-j1` 避开 mkfifo jobserver 噪声。

### 补丁（1 个，三关已过）

`patches/0001-sprng-2.0a-ohos-build-portability.patch`，9 个文件 12 个 hunk：

| 文件 | 改动 | 原因（实测） |
|---|---|---|
| `make.CHOICES` | 默认 `PLAT = INTEL` → `GENERIC` | INTEL 硬写 MPI 路径（见上） |
| `SRC/make.GENERIC` | `RANLIB=echo`→`ranlib`；`CFLAGS/CLDFLAGS` 钉 `-O3 -pipe -DNDEBUG` 并留 `$(CPPFLAGS)/$(LDFLAGS)` | flags 落点（见上）；`echo` 版 ranlib 不建索引 |
| `SRC/sprng/Makefile` | `all : sprng timesprng checksprng` → `all : sprng` | 后两者依赖 `F77`（设备/CI 均无 Fortran） |
| `SRC/insertmenu` | `echo -e` → `printf` | 无 shebang 脚本回退 toybox sh，`echo -e` 是 bashism（Debian #818762 同款） |
| `SRC/primes_32.c`/`primes_64.c` | 补 `<string.h>`；`int primes[]`→`static` | **原版链接必失败**：两文件同名全局 `primes[]`，现代工具链默认 `-fno-common` ⇒ `duplicate symbol: primes`（实测） |
| `SRC/sprng/sprng.c` | 补 `#include "store.h"` | `store_*`/`load_*` 无原型 ⇒ 隐式声明 |
| `SRC/pmlcg/pmlcg.c` | `#include "gmp.h"` → `<gmp.h>`；补 `store.h` | **捆绑 1996 年 gmp.h 与 gmp6 符号不兼容**（实测 undefined `__mpn_add_n`/`__mpn_sub_n`/`mpz_init`/`mpz_init_set_str`/`mpz_clear`）；Debian 同款改法 |
| `SRC/pmlcg/Makefile` | 依赖清单去掉 `gmp.h` | 配合上一行 |

补丁三关：`NUL=0` ∧ `@@ hunk=12 ≥1` ∧ 全新解压树 `patch -p1` rc=0 后与 work 树
**9/9 文件逐字节 `cmp` 一致**。未改任何测试用例源码。

---

## 依赖

* **硬依赖**：`gmp/6.3.0`（上游默认开 `PMLCGDEF/GMPLIB`，pmlcg 进 libsprng.a ⇒
  链接面必需；Debian `Build-Depends: libgmp-dev`、arm64 产物 `NEEDED libgmp.so.10`
  同证）。conan `ohpcd` 与本仓均有该配方/二进制。
* **libm**：`-lm`（`system_libs=["m"]` 对外声明）。
* **MPI**：**不引**（`PLAT=GENERIC` 排除，环境无 MPI）。
* **Fortran**：不构建（无 F77；只建 C 面）。
* **缺依赖清单：空集。**

---

## 质量测试记录（设备离线，2026-09-24）

| # | 测试 | rc（留档，未定义） | 统计值 | 判定 |
|---|---|---|---|---|
| 1 | maxt | 0 | KS% = 72.89 | PASS |
| 2 | collisions | 0 | KS% = 70.52 | PASS |
| 3 | coupon | 0 | KS% = 92.73 | PASS |
| 4 | equidist | 8 | KS% = 26.76 | PASS |
| 5 | gap | 8 | KS% = 23.28 | PASS |
| 6 | perm | 0 | KS% = 64.69 | PASS |
| 7 | poker | 0 | KS% = 41.22 | PASS |
| 8 | runs | 8 | KS% = 3.68 | PASS |
| 9 | serial | 0 | KS% = 82.07 | PASS |
| 10 | sum | 0 | KS% = 96.23 | PASS |
| 11 | random_walk | 0 | percent = 6.39 | PASS |
| 12 | wolff | 72 | （Ising 模型输出） | PASS |
| 13 | metropolis | 72 | （Ising 模型输出） | PASS |

**TOTAL=13 PASS=13 FAIL=0**（判据=输出断言；seed=1234567 固定，可复算）。
原始逐字输出：`$TASK_DIR/test-logs/<name>.out`；汇总 `summary.json`。

---

## 环境与工具

* 编译：`/data/service/hnp/bin/clang` 15.0.4（`aarch64-unknown-linux-ohos`）、
  GNU Make 4.4.1、`ar`/`llvm-ar`/`ranlib`（binutils 2.45 / OHOS SDK 26.0.0.18）
* Conan：OHOS 适配版 2.29.1，profile `ci/conan/profiles/ohos-aarch64`
* 依赖：`gmp/6.3.0`（ohpcd 预编译二进制，`shared=False`）

---

## 已知限制 / 未运行项（如实记录）

1. `EXAMPLES/` **未构建**：其默认目标 `serial` 的清单里混着 Fortran 程序
   （`sprngf`/`seedf`/`pif-simple` 等），无 F77 即不可建；C 例程的等价覆盖面由
   `test_package` 消费端断言承担。
2. `timesprng`/`checksprng` 的 **Fortran 半边**未构建（同上）；C 半边已构建运行。
3. `TESTS/fft` 未运行（不在 TESTLIST 注册表，且需 SGI 专有库）。
4. `checksprng` 的 pmlcg Simple 接口 1/18 FAILED：上游固有 pack/unpack 缺陷
   （根因见上），未修库语义。
5. 未挂 CI 窗：按用户 2026-09-24 令，终点=建 PR 即停，不发 `/rebuild`、
   不做 changes 核，CI/AI Review/外部审查全冻结到恢复令。
