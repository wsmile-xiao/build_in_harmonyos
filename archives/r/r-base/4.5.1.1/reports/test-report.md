# r-base 4.5.1.1 测试报告

> **项目**: r-base（R 语言解释器与基础运行时）
> **测试日期**: 2026-09-30
> **测试环境**: HarmonyOS PC（HongMeng Kernel 1.11.0）aarch64，`/data/service/hnp` clang 15，Conan 2.29.1
> **测试类型**: 上游官方测试套件（`make -j1 check`）+ `test_package` 消费侧验证（W3 本地 CI 同源脚本）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游 `tests/*.R` 全量清点 | 68 | — |
| 上游实际执行 | 62（61 直接 + 1 间接） | 91.2% |
| 上游执行通过 | 62 | 100%（执行项） |
| 环境受限（实际执行，OOM） | 1（reg-large.R） | — |
| 具体技术原因不可执行 | 5 | — |
| `test_package` 消费侧/结构项 | 15 | 100%（14 执行 + 1 条件跳过） |

测试项构成：上游 `tests/*.R` 原生测试脚本 **68 项全量清点**，其中 62 项实际执行（61 项直接执行 + 1 项经 `eval-etc.R` 间接执行）全部通过；1 项（`reg-large.R`）实际执行但被环境内存限制终止；5 项因具体技术原因不可执行（见 3.3）；另有 `test_package` 消费侧断言 8 项 + 结构性标记 6 项 + ELF/可移动性结构扫描 1 项。

**核心功能通过率**: ✅ **100%**（实际执行的 62 项上游脚本 0 项失败；1 项环境受限见 3.3；5 项不可执行有具体技术原因，见 3.3）

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。R 解释器在本机原生运行，REPL/管道/脚本三种执行路径、基础包数值与绘图设备、包安装与加载、网络（真实 HTTPS）、资源目录重定位全部可用；`r-base/4.5.1.1` 作为 `rmatrix` 等 R 扩展包的下游构建依赖已具备发布条件。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游 `tools-Ex.Rout` 与 `.save` 有 2 行告警差异（`file("")` 用法告警） | 仅 example 输出文本，非功能缺陷，R 判定为 NOTE | 🟢 |
| 上游绘图测试 `reg-plot.pdf` 二进制有亚像素舍入差异（0.01 pt），R 判定 `OK` | 仅 PDF 内部数值字面量，画面一致 | 🟢 |
| 迭代器/时区等系统能力差异已由 0003/0008 补丁规避 | 无（已修复并回归） | 🟢 |

### 2.3 可用功能清单

```
✅ 解释器: R / Rscript 可执行，REPL、stdin 管道、脚本文件三种模式均正常
✅ 基础包: base/tools/utils/grDevices/graphics/stats/datasets/methods/grid/splines/stats4/compiler/parallel
✅ 数值与线性代数: BLAS/LAPACK 走 openblas/0.3.33，lapack.R / d-p-q-r-tests.R / iec60559.R 全部 OK
✅ 包机制: install.packages/library/sessionInfo 正常，R_HOME 由配方 runenv 注入
✅ 网络: 私有 curl + 包内 CA 束完成真实 HTTPS 请求（CURL_HTTPS_CONSUMER=PASS）
✅ 可移动性: 从任意前缀启动（R_HOME 相对定位）、build 路径不泄漏（负向测试通过）
✅ 时区: 以 HarmonyOS 权威 param 时区为准，Sys.timezone() 回归通过
⚠️ 图形后端: X11/cairo 设备依赖宿主图形栈，本环境仅验证 pdf/png 设备（与 4.5.1 结论一致）
```

### 2.4 已知限制

1. 本包为原生 OHOS/armv8 专用（`validate()` 显式拒绝其他 os/arch），不提供交叉编译产物。
2. `.conan2` 与 `~/.harmonybrew` 两个宿主前缀在测试中做遮蔽校验；后者目标机不存在时按设计跳过（见 3.3）。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| `make -j1 check` → running strict specific tests | 基础包回归（eval-etc/arith/lm-tests/method-dispatch/d-p-q-r-tests/structure/any-all 等） | ✅ PASS |
| `make -j1 check` → running sloppy specific tests | complex/print-tests/lapack/datasets/datetime/iec60559 | ✅ PASS |
| `make -j1 check` → regression tests | reg-tests-/reg-IO/reg-BLAS/reg-S4/reg-encodings/reg-plot-latin1 | ✅ PASS |
| `make -j1 check` → Examples（14 个基础包） | 各包 example 输出与 `.Rout.save` 逐行比对（69 项 `... OK`） | ✅ PASS |
| `make test-DateTime`（`tests/` `test-all-devel` 族） | datetime2/3/4/5.R 日期时间打印回归（RVAL_IF_DIFF=0，平台差异允许） | ✅ PASS |
| `make test-Demo` | demos.R / demos2.R（base+stats demo） | ✅ PASS |
| `make test-Primitive` | primitives.R 原语一致性 | ✅ PASS |
| `make test-Random` | p-r-random-tests.R 随机数发生回归 | ✅ PASS |
| `make test-Regexp` | utf8-regex.R + PCRE.R 正则回归 | ✅ PASS |
| `make test-Translation` | reg-translation.R（LANGUAGE=fr）消息翻译 | ✅ PASS |
| `make test-Conditions` | conditions.R 条件系统单测 | ✅ PASS |
| `make test-Misc-dev` | misc-devel.R（含 serverSocket 端口探测） | ✅ PASS |
| `make test-Internet2` | internet2.R + libcurl.R（libcurl 下载/头部） | ✅ PASS |
| `make test-Internet-dev` | download.file.R + sockets.R（socket HTTP 客户端） | ✅ PASS |
| `make test-CRANtools` | CRANtools.R（available.packages/CRAN 元数据，真实网络） | ✅ PASS |
| `make test-System`（PATH 含 test-system2 辅助二进制） | test-system.R system()/system2() 语义 | ✅ PASS |
| `make test-UTF-8` | utf8.R 全 Unicode 码点 intToUtf8 往返 | ✅ PASS |
| `make test-Iconv` | iconv.R iconv sub/转码回归 | ✅ PASS |
| `eval-fns.R`（间接执行） | 由 eval-etc.R `source(echo=TRUE)` 执行，eval-etc.Rout 含执行回显（证据在 eval-etc.Rout） | ✅ PASS（间接） |
| `R_BASE_HTTPS=PASS` | 内置网络能力（curl + CA 束）真实握手 | ✅ PASS |
| `CURL_HTTPS_CONSUMER=PASS` | 消费侧 HTTPS 探针（私有 curl 链接与运行库解析） | ✅ PASS |
| `R_BASE_RSCRIPT=PASS` | `Rscript -e` 无交互执行 | ✅ PASS |
| `R_BASE_CACHE_MASK=PASS` | 遮蔽 `~/.conan2` 后仍能正常启动（不依赖宿主缓存） | ✅ PASS |
| `R_BASE_RELOCATION_NEGATIVE_TEST=PASS` | 负向控制：先把 `~/.conan2`（及存在时的 `~/.harmonybrew`）遮蔽，再仅从移动副本启动 `R`，成功即证明未回落到原始安装/宿主缓存 | ✅ PASS |
| `test_package` ELF/可移动性结构扫描 | 全包路径串扫描（禁止 `/storage/Users/...`、`.conan2`、`.conan-build-*` 残留）+ 全 ELF `readelf -d` 检查 RPATH/RUNPATH 与逐个 NEEDED 在包内可解析 | ✅ PASS |
| `R_BASE_CONSUMER_ASSERTIONS=8/8` | 消费侧断言（`test_r.R` 8 条 `stopifnot`）：① `getRversion()=="4.5.1"` ② 算术 `2+3==5` ③ perl 正则引擎 ④ `crossprod` 结果矩阵属性与数值（走 openblas）⑤ gzip `memCompress`/`memDecompress` 往返 ⑥ `iconv` UTF-8 往返 ⑦ `R.home()` 重定位一致性（含 `share`/`include`/`doc` 子目录）⑧ 对 `https://cran.r-project.org/` 发起真实 HTTPS 请求并取回首行 | ✅ PASS |

### 3.2 失败的测试

无。

### 3.3 未执行/环境受限的测试（具体技术原因）

| 测试项 | 原因 |
|--------|------|
| `reg-large.R`（`make test-Large`） | **实际执行，环境内存受限终止**：设备物理内存 32 GB（MemAvailable ≈ 27 GB），脚本自身按 `availableGB` 阈值自动跳过高内存段后，在无阈值守卫的 `rank(x <- -1:2^31)`（PR#18617，需同时持有 2×17 GB double 长向量 ≈ 34 GB）处被 OOM kill（`Signal 9`）。上游注释明示该测试需要 ≥60 GB 内存（"On x86_64 Linux uses up to 220GB of VM"），属目标机硬性资源边界，非包缺陷。原始日志：`reports/upstream-make-check-devel.log` |
| `eval-etc-2.R`（`test-src-sloppy-b`） | 需要 R 推荐包 Matrix（`@USE_RECOMMENDED_PACKAGES_TRUE@` 才启用）；本构建未编译推荐包（R 源码不自带，需单独下载），configure 判定 false 后上游 Makefile 自行将其排除 |
| `reg-tests-3.R`、`reg-examples3.R`（`test-src-reg3`） | 同上：仅 `USE_RECOMMENDED_PACKAGES_TRUE` 时纳入（需 Matrix/MASS）；本构建该变量为 false，上游 Makefile 将 reg3 收缩为 reg-plot-latin1.R（已执行通过） |
| `reg-win.R` | 仅 Windows：首行即调用 `windows(record=TRUE)` 图形设备（仅 Windows 存在）；上游仅在 `Makefile.win` 中运行，Unix `Makefile.in` 将其归入 INSTFILES 不执行 |
| `gct-foot.R` | 非独立测试：仅 1 行 `cat("Time used {gctorture()}:", proc.time() - .ptime)`，是 `test-Gct`（gctorture 慢速压测 harness）的计时尾部，由 harness 拼接注入，无 `.Rout.save`、无独立 make 目标 |
| `R_BASE_HARMONYBREW_MASK=SKIPPED (root absent: /storage/Users/currentUser/.harmonybrew)` | 该遮蔽校验要求宿主存在 `/storage/Users/currentUser/.harmonybrew` 根；本 worker 上不存在，按“存在才遮蔽”的设计跳过并如实输出。`~/.conan2` 遮蔽校验保持无条件执行，负向校验强度不受影响。 |

---

## 四、关键问题分析

### 问题1: `test_package` 硬编码宿主目录，导致包无法通过 CI 发布

**现象**：
```
stat: cannot statx '/storage/Users/currentUser/.harmonybrew': No such file or directory
（run_test.sh 以 set -e 运行，整条测试链随即中止）
```

**根因分析**：
`test_package/run_test.sh` 无条件对 `/storage/Users/currentUser/.harmonybrew` 执行 `stat -c %a` 并随后 `chmod 000`。该目录是为验证“遮蔽宿主预置 R 环境”而构造的，但它是**构建机个人目录**，目标 worker 上并不存在；`set -e` 下该命令失败即中止整个 `test_package`，于是 `conan create` 失败、包无法进入 release 流水线。这正是 r-base 4.5.1 合入后长期无法发布的直接原因。

**解决方案**：
改为“存在才遮蔽”：根存在时记录原权限 → `chmod 000` 遮蔽 → 校验 → `finally` 还原；根不存在时输出 `R_BASE_HARMONYBREW_MASK=SKIPPED (root absent: ...)`，不改变退出码。遮蔽能力保留，可移植性恢复。

### 问题2: 测试产物写入源码树，归档被污染

**现象**：
`archives/r/r-base/4.5.1/test_package/moved-r-base/` 被提交进仓库：**87 MB / 2025 个文件**（4.5.1 归档 87 MB 几乎全部来自它），另有 `conanbuild.sh`/`conanrun.sh`/`deactivate_*.sh` 等生成脚本。

**根因分析**：
Conan 对仓库内 `test_package` 直接以该目录自身作为 `build_folder`，`run_test.sh` 把被测包副本搬移/复制到 `moved-r-base` 后驻留在源码树内；构建产物与源码混在同一棵树，`git add` 时被一并提交。

**解决方案**：
在 `test_package/conanfile.py` 的 `test()` 中以 `try/finally` 无条件 `shutil.rmtree(moved, ignore_errors=True)`，无论测试成功或失败都清理；实测连续两次完整 W3 运行后归档稳定为 462 KB、`git status` 无残留。

---

## 五、测试环境

```
软件:      R (r-base) 4.5.1.1   upstream 4.5.1
源码:      https://cran.r-project.org/src/base/R-4/R-4.5.1.tar.gz
           sha256 b42a7921400386645b10105b91c68728787db5c4c83c9f6c30acdce632e1bb70
补丁:      patches/0001-0009（与 4.5.1 逐字节一致）
依赖:      zlib/1.3.1.1 pcre2/10.45.1 bzip2/1.0.8 xz/5.6.2 libiconv/1.17
           curl/8.15.0 openblas/0.3.33 openssl/3.5.6.1
构建工具:  flang-ohos/20.1.0（tool_requires）
profile:   ci/conan/profiles/ohos-aarch64（os=OHOS 6.0, arch=armv8, clang 15, libc++, Release）
命令:      CI_PACKAGES=archives/r/r-base/4.5.1.1 zsh ci/conan/build_and_test.sh
```

---

*报告生成时间: 2026-09-30*
