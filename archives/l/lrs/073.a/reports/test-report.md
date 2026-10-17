# lrs 073.a 测试报告

> **项目**: lrs（上游项目 lrslib，7.3a bug-fix 版）  
> **测试日期**: 2026-09-26  
> **测试环境**: HarmonyOS PC（HongMeng Kernel 1.12.0 aarch64，HAD-W32）  
> **测试类型**: 官方回归套件（数据驱动）+ Conan test_package 消费者测试  
> **平台任务**: 智能任务平台 id 8566 · `lrs` `073.a` · 分支 `feat/lrs-073.a`

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 45 | 100% |
| 通过 (PASS) | 45 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

口径：
* 总测试数 45 = 30 例上游回归运行（`ine/test/*.ine`，每例一次完整 `lrs` 枚举运行）+ 15 条消费者（鸿蒙特有）断言（`test_package/`，3 条 C API + 12 条鸿蒙侧裸环境/分派判据）
* 另计 2 条上游参考输出独立 oracle（`ext/test/cube.ext` 声明 8 行、`ext/test/tsp5.ext` 声明 12 行）；含此 2 条后自动断言总数为 47（与 `test_package/MANIFEST.yml` 的 `assertion_count: 47` 同口径）

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。上游 30/30 回归输入全部真实运行通过；消费者 15/15 断言通过；
交付的 5 个可执行文件在**裸环境**（不 source conanrun、不设 `LD_LIBRARY_PATH`）可用。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游临时文件模板写死 `/tmp`（平台 `/tmp` 只读） | 30 例中 6 例 rc=139；stdin 暂存 + 64/128bit 溢出重启失效 | 🔴（本包已修复） |
| 上游可执行文件无 RUNPATH | 裸环境全部工具 rc=127；conanrun 下为假绿 | 🔴（本包已修复） |
| 上游 CLI 不认 `--version`/`--help` | L2 对 `bin/` 全部 5 个文件判红 | 🔴（本包已修复） |
| `gmp.h` 属公开头链（`lrslib.h`→`lrsgmp.h`→`gmp.h`） | 本包自测全绿、消费者编译红 | 🟡（`transitive_headers` 修复） |

### 2.3 可用功能清单

```
✅ 库:  liblrs.so.1.0.0（SONAME liblrs.so.1；含 64bit/128bit/GMP 三套算术后端）
✅ 工具: lrs（H↔V 转换 / 面枚举 / 体积）、lrsnash（双人博弈 Nash 均衡）
✅ 别名: redund / minrep / fel（argv[0] 分派，实测各自命中模式标志）
✅ 头:  include/lrslib/{lrslib.h,lrsdriver.h,lrsrestart.h,lrsgmp.h,lrslong.h,lrsmp.h}
⚠️ 未交付: mplrs/mplrsgmp（需 MPI）、plrs（需 libomp）、单精度变体（上游 make single）
```

### 2.4 已知限制

1. `mplrs`/`mplrsgmp` 未构建：需要 `mpicc` 与 OpenMPI，平台工具链不含（上游 `default` 目标同样不含）。
2. `plrs` 未构建：需要 libomp 运行库，未纳入本包。
3. 运行时需让 `TMPDIR` 指向可写目录（`lrs` 的 stdin 暂存与 64/128bit 溢出重启使用 `mkstemp`）。

---

## 三、测试详情

### 3.1 通过的测试（上游回归 30/30，逐例实测）

`build()` 内逐例运行 `./lrs-shared ine/test/<case>.ine`（`LD_LIBRARY_PATH`=构建树、`TMPDIR`=构建目录内可写目录，
逐例超时 900s）。判据：退出码 0 + 该例自身的 `*Totals:` 行（`cp4`/`ep`/`inf`/`left`/`right` 五例属转换/无解模式，
天然无该行，已在配方显式登记）；`cube`/`tsp5` 另与上游 `ext/test/` 参考输出的行数比对。

| 用例 | lrs 报告的顶点数 | 结果 |
|------|-----------------|------|
| cube | 8（上游参考 cube.ext 声明 8） | ✅ PASS |
| tsp5 | 12（上游参考 tsp5.ext 声明 12） | ✅ PASS |
| cross4 / diamond / lcube / truss2 | 8 / 4 / 4 / 1 | ✅ PASS |
| cyclic17_8 / in0 / in1 / in2 / in3 / in4 / in5 / in6 / in7 | 935 / 9 / 31 / 18 / 8 / 54 / 89 / 332 / 1188 | ✅ PASS |
| kkd38_6 / kq20_11 / kq20_11a | 252 / 1188 / 1188 | ✅ PASS |
| metric40_11 / metric80_16 | 32 / 16 | ✅ PASS |
| mit / mit31_20 | 4862 / 18553 | ✅ PASS |
| mp5 / trunc10 / trunc7 | 32 / 290 / 140 | ✅ PASS |
| cp4 / ep / inf / left / right | 转换/无解模式（rc=0，无 `*Totals:`，显式登记） | ✅ PASS |

汇总行（实测读数，见本地 W3 CI 日志 `reports/w3-local-ci.log` 第 332 行）：

```
lrs/073.a@ohpcd/stable: upstream regression battery: 30/30 cases executed, 0 failed
```

### 3.2 通过的测试（消费者 test_package 15/15）

| # | 测试项 | 功能 | 结果 |
|---|--------|------|------|
| 1-3 | `test_lrslib`（C API） | `lrs_init` + `lrs_alloc_dat`/`lrs_alloc_dic`/`lrs_set_row`/`lrs_getfirstbasis`/`lrs_getsolution`/`lrs_getnextbasis`，dim=2/3/4 超立方体 = 4/8/16 顶点 | ✅ 3/3（conanrun 与裸环境各跑一遍） |
| 4-9 | 裸环境工具查询 | `lrs --version`/`--help`、`lrsnash --version`、`redund`/`minrep`/`fel --version` 全部 rc=0 | ✅ 6/6 |
| 10-11 | 版本横幅 | `lrs`/`lrsnash --version` 必须含 `lrslib 7.3a`（本包 CLI 补丁新增） | ✅ 2/2 |
| 12 | 裸环境真实计算 | `<pkg>/bin/lrs cube.ine` 报 `vertices=8` | ✅ 1/1 |
| 13-15 | argv[0] 别名分派 | redund→`checking for redundant rows only`、minrep→`minimum representation`、fel→`no project/eliminate option found` | ✅ 3/3 |

### 3.3 跳过的测试

无（SKIP = 0）。

---

## 四、关键问题分析

### 问题1: 只读 `/tmp` 导致 6/30 上游回归用例崩溃（rc=139）

**现象**（修复前，0.73 上游版本实测）：
```
*Error opening output file /tmp/lrs_restartXXXXXX
*bad input file name
*lrs_setup failed
```
退出码 139（SIGSEGV）；`cyclic17_8`/`in7`/`kkd38_6`/`kq20_11`/`kq20_11a`/`truss2` 六例必崩。

**根因分析**：`lrslib.c` 两处 `mkstemp()` 模板是字面量 `/tmp/lrs_restartXXXXXX`（溢出重启）
与 `/tmp/lrs_stdinXXXXXX`（stdin 暂存）。平台沙箱 `/tmp` 只读 → `mkstemp` 失败 →
随后 stage-2 清理仍带着 `P == NULL` 进入会解引用的调用。

**解决方案**：`patches/0002-lrslib.c.patch` 改为 `$TMPDIR` 优先、`/tmp` 兜底；
并在 stage 0 返回 `-1` 时 `exit(1)`（`patches/0001-lrs.c.patch`）。修复后 30/30 rc=0。

### 问题2: 交付工具裸环境 rc=127（假绿陷阱）

**现象**（修复前）：`env -u LD_LIBRARY_PATH bin/lrs --version` → rc=127
`Error loading shared library liblrs.so.1`；而 `test_package` 在 conanrun 下全绿。

**根因分析**：上游 makefile 的 `lrs-shared`/`lrsnash-shared` 链接规则完全没有 RUNPATH 挂钩，
装出后 `bin/` 找不到 `lib/`；conanrun 注入 `LD_LIBRARY_PATH` 把缺陷盖住。

**解决方案**：`patches/0004-makefile.patch` 加 `RUNPATHFLAGS ?= -Wl,-rpath,'$$ORIGIN/../lib'`
并挂到两条规则。修复后实测：

```
readelf -d <pkg>/bin/lrs | grep RUNPATH
  0x000000000000001d (RUNPATH)      Library runpath: [$ORIGIN/../lib]
env -u LD_LIBRARY_PATH <pkg>/bin/lrs --version
  lrs (lrslib 7.3a)
```

### 问题3: CLI 不认 `--version`/`--help`

**根因分析**：`lrs` 把每个参数当输入文件名；`redund`/`minrep`/`fel` 是同一二进制的
argv[0] 别名，一次缺陷波及 5 个交付可执行文件（L2 冒烟会逐个判红）。

**解决方案**：`patches/0001-lrs.c.patch` / `patches/0003-lrsnash.c.patch` 在 `main()` 开头
处理 `--version`/`-V`（和 `lrs` 的 `--help`/`-h`）并 `return 0`；横幅版本串随本版更新为
`lrslib 7.3a`（消费者测试断言该字符串）。

---

## 五、测试环境

```
软件:  lrs 073.a（上游 lrslib 7.3a，lrslib-073a.tar.gz sha256 7fb16ad5…）
编译器: clang 15.0.4（Harmonybrew ohos-sdk@26.0.0.18，target aarch64-unknown-linux-ohos）
Conan: 2.29.1（OHOS 适配版），profile ohos-aarch64-device
依赖:  gmp/6.3.0（静态 libgmp.a，GMP 后端代码静态并入 liblrs.so）
验证:  conan-verify G0-G4 PASS；test_package 15/15；上游回归 30/30
产物读数（设备实测）:
  bin/lrs        sha256 21ffdf21f9fa43f9996492766fa0c080b486acf3f4152855c8647a2f9f2035ff
  bin/lrsnash    sha256 3bb2f4950e600469646af0dafa13506f95082294287e7809c70a765676829a91
  lib/liblrs.so.1.0.0 sha256 d7a37f15dcaca5867ab4ece5ae1ddc9500816859d69824c80995b528f190c22c
  liblrs.so.1.0.0 SONAME = liblrs.so.1；NEEDED 仅 libc.so（gmp 静态）
  bin/lrs RUNPATH = $ORIGIN/../lib；NEEDED = liblrs.so.1, libc.so
```

---

*报告生成时间: 2026-09-26*
