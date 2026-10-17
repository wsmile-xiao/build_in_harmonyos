# sysklogd 1.5.1 适配笔记

> **状态：已构建、已验证（`conan-verify` G0–G4 已跑，`conan create` 建包
> `6b129b068851896169fae42d399fa922d239ce8a`，`status: built`；未 `upload`）。**
> 本文件按时间顺序保留前置调查与后续各回合的真实推进轨迹：
> 前置调查（W0/查重/源码风险预判，2026-09-23 早段） → 配方编写与静态自检 →
> 构建闸口实测（tmpfs 复现树 + 补丁 0003–0006 落真错） →
> 正式 `conan-verify` G0–G4 + W3 本地 CI（20:29–20:33） →
> 补丁 0001 的 A/B 对照与 41 行机制探针（§9.5，20:56–20:59） →
> W4 独立审计 fail（P1=3/P2=4/P3=7）后按整改回合作**同源更正**。
> 下文凡「未验证 / 未构建 / pending」字样均为**前置调查期的历史口径**，
> 已在 §10.5 与 §11（整改回合）逐项更正为交付态；**若与实况相反，一律以本框
> 与 §11 为准**。每条结论都标注了取证命令；**仍未验证的项显式写「未实测」**，
> 不当结论用（如 `ksym` 的运行期前提）。

## 编译环境

- 构建系统: **make（上游纯 Makefile）** — 不是 autotools
- 编译器: clang / clang++（profile `ci/conan/profiles/ohos-aarch64`：
  `os=OHOS`、`os.version=6.0`、`arch=armv8`、`compiler.version=15`、`libc++`）
- 编译日期: **2026-09-23**（与 `.ci-result.json` `timestamp: 2026-09-23T20:33:44`
  与 `manifest.yaml` `build_date` 同源；口径与依据见 §11.1）
- 状态: **built**（`conan-verify` G0–G4 已跑并 PASS，其中 G4 为「PASS 但空过」——
  见 §10.4；W3 本地 CI 已达成，见 §10.5）
- 官方源: `https://www.infodrom.org/projects/sysklogd/download/sysklogd-1.5.1.tar.gz`
  （`curl -fsSIL` → http=200；实测 sha256 `5166c185ae23c92e8b9feee66a6e3d0bc944bf673112f53e3ecf62e08ce7c201`）

## 前置门禁逐条结果

| 门禁 | 命令 | RC | 结果 |
|---|---|---|---|
| W0 依赖发布 | `bash ci/scripts/preflight_check.sh sysklogd/1.5.1` | **0** | `[OK] 预检通过（无依赖需要检查）`（该轮 conanfile 未生成⇒依赖集为空；交付态"零 Conan 依赖"以 §10.4 G1「12 项配方完整性逐条 ✅」的依赖检查与 §10.5 `✅ conan-verify 通过` 为准） |
| 查重 配方 | `python3 scripts/ohc-run.py recipe-search sysklogd` | **0** | `⚠️ 无相似配方（语料 6173 条）——首稿走 conan-init 模板` |
| 查重 归档 | `ls -d archives/s/sysklogd` / `grep -i sysklogd SUMMARY.md` | 1 / 空 | 确认全新包 |
| R47 语言预检 | `lang-preflight sysklogd 1.5.1 --src <src> --lang cpp` | **0** | `✅ 语言匹配: task=cpp, detected=c`（8 个 .c、主体占比 100%，c↔cpp 兼容族）⇒ **不触发 env_unsupported** |
| 知识图谱检索 | `engine "klog_ctl ... klogctl"` | **0** | **命中 E014**（见下） |
| 源码风险扫描 | `prescan <src> --no-writeback` | **0** | medium×3（HMDFS-002 / PATH-001 / GLIBC-001） |

## 构建系统证据（推翻了"预期 Autotools"）

```
$ ls -l configure configure.ac Makefile.am aclocal.m4 bootstrap
ls: configure: No such file or directory
ls: configure.ac: No such file or directory
ls: Makefile.am: No such file or directory
ls: aclocal.m4: No such file or directory
ls: bootstrap: No such file or directory
```
顶层只有单个 `Makefile` + 8 个 `.c` + 5 个 `.h`。`lang-preflight` 与 `prescan`
两个工具独立判定的 `build_system` 也都是 **`make`**。

⇒ **没有 `--prefix`/`--sysconfdir` 可配**；`prefix` 只能在 `make` 命令行传
（`BINDIR = $(prefix)/usr/sbin`，Makefile:33）。

### Makefile 关键行号实录（2026-09-23 §11 整改回合按真机 `grep -n` 复核）

```
$ grep -n "^all:\|^test:\|^install_exec:\|^oops\.ko:\|^CC=\|^SKFLAGS=\|^LDFLAGS=\|^INSTALL \|^BINDIR\|^syslog_tst:\|^tsyslogd:\|^tklogd:\|^ksym:\|^obj-m\|^syslogd:\|^klogd:\|make -C /lib/modules\|^check" Makefile
20:CC= gcc                                          ← 硬编码，必须 make CC=$CC
23:SKFLAGS= $(RPM_OPT_FLAGS) -O3 -DSYSV -fomit-frame-pointer -Wall -fno-strength-reduce
27:LDFLAGS= -s
30:INSTALL = /usr/bin/install
33:BINDIR = $(prefix)/usr/sbin
76:all: syslogd klogd
78:test: syslog_tst ksym oops.ko tsyslogd
82:syslogd: syslogd.o pidfile.o
85:klogd:	klogd.o syslog.o pidfile.o ksym.o ksym_mod.o
89:syslog_tst: syslog_tst.o
92:tsyslogd: syslogd.c version.h
95:tklogd: klogd.c syslog.c ksym.c ksym_mod.c version.h
116:ksym: ksym_test.o ksym_mod.o
129:install_exec: syslogd klogd                     ← 安装硬绑 klogd
139:obj-m += oops.o
141:oops.ko: oops.c
142:         make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
```

> 取证树：`/storage/Users/currentUser/tmp/uc2/sysklogd/sysklogd-1.5.1/Makefile`
> （5020 B、mtime `2014-10-05 03:47`，上游 tarball 原样解包）。
> **§11 更正说明**：本次调查初稿把 `all/test/install_exec/oops.ko` 记成 78/85/124/138，
> 交付轮已按 `grep -n` 复核为 **76/78/129/141-142**；仓内其余引用
> （`conandata.yml:16`、`conanfile.py:40`、`test_package/MANIFEST.yml:16/25/30`、
> 本文 §6 第 313-314 行）与实测值一致，本节以本节为准。

## ★ 系统类难点（klogd / 内核日志接口）— 已取证

### 上游用到的内核接口

```
$ grep -rn "klog_ctl\|klogctl\|SYS_klog\|__NR_klog" .
./klogd.c:285:#define ksyslog klogctl
$ grep -rn "/proc/kmsg" .
./klogd.8:101   ./klogd.8:409        ← 只在手册页，C 源码里没有 /proc/kmsg
```

`klogd.c` 的分派写法（`sed -n 255,300p`）：

```c
278: #include <linux/unistd.h>
279: #define __LIBRARY__
280: #if !defined(__GLIBC__)
281: # define __NR_ksyslog __NR_syslog
282: _syscall3(int,ksyslog,int, type, char *, buf, int, len);
283: #else
284: #include <sys/klog.h>
285: #define ksyslog klogctl
286: #endif
```
运行期调用点：`klogd.c:347(0)`、`533(8)`、`554(1)`、`570(7)`、`936(2)`。
其它 Linux 专有依赖：`ksym_mod.c:120 <linux/time.h>`、`ksym_mod.c:124 <linux/version.h>`、
`oops.c:32-37 <linux/module.h> <linux/kernel.h> <linux/init.h> <linux/proc_fs.h> <linux/poll.h>`、
`ksym.c:149 "/usr/src/linux/System.map"`。

### OHOS aarch64 sysroot 实况

sysroot = `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include`
（由 `ci/conan/profiles/ohos-aarch64` 里的 clang 路径与 `LD_LIBRARY_PATH` 反查得到）

头文件（逐个 stat，RC=0）：

| 头 | | 头 | |
|---|---|---|---|
| `syscall.h` | PRESENT | `sys/syslog.h` | PRESENT |
| `sys/syscall.h` | PRESENT | **`sys/msgbuf.h`** | **MISSING** |
| **`sys/klog.h`** | **PRESENT** | `utmp.h` / `paths.h` | PRESENT |
| `linux/unistd.h` | PRESENT | `netdb.h`/`resolv.h`/`arpa/nameser.h` | PRESENT |

符号与宏（grep / nm / strings）：

```
grep -rn "__NR_syslog" $S/usr/include   → aarch64-linux-ohos/bits/syscall.h:117:#define __NR_syslog 116
grep -rn "klogctl"     $S/usr/include   → sys/klog.h:8:int klogctl (int, char *, int);
grep -rn "_syscall3|_syscall1|_syscall0" $S/usr/include   → 空（不存在）
grep -rn "define __GLIBC__" $S/usr/include                 → 空（不存在）
nm -D --defined-only $S/usr/lib/aarch64-linux-ohos/libc.so | grep -iE "klog|syslog"
  → T klogctl / T syslog / T vsyslog
strings -a /system/lib/ld-musl-aarch64.so.1 | grep -xE "closelog|klogctl|openlog|setlogmask"
  → 四个都在
```

### 定性（可回指证据）

1. **klogd 上游写法在 OHOS 上会失败，但**首错不在编译期**（§11.3 更正，一手依据
   §9.5 的 A/B 对照 + 41 行机制探针）：sysroot 不定义 `__GLIBC__` ⇒ `klogd.c:280`
   走 `!defined(__GLIBC__)` 支路 ⇒ 展开 `_syscall3(...)` 时该宏**在整个 sysroot
   头树中不存在**；clang 15 因此按 K&R 语义把 `_syscall3(int,ksyslog,...)` **降级为
   一条隐式 int 返回类型的函数声明**，`klogd.o` 仍**编译成功**（RC=0、只有 5 条
   `-Wimplicit-int` 警告），故障点后移到**链接期**——`ld.lld: error: undefined
   symbol: ksyslog`、`make: *** [Makefile:86: klogd] Error 1`。
   **反直觉之处**：OHOS sysroot 的 `sys/klog.h` 与 `klogctl` 符号**是齐的**，
   所以正确修法是**让它走 `#else`（glibc）支路**，而不是"禁用功能"。
2. **`syslogd` 不调用任何内核日志接口** ⇒ "只构建 syslogd、klogd 记为已知限制"技术可行
   （见下节代价）。
3. **本包不属 `env_unsupported`**：语言匹配、CI 能力矩阵只需 clang+make（✅ 行）、
   所需头/符号大体齐备；门槛是源码自身 glibc/musl 分支写法与 GCC 专有 flag。

### 若只交付 syslogd，已知代价

- `make install` **不可用**：`install_exec: syslogd klogd`（Makefile:129）硬绑 klogd
  ⇒ 需在 conanfile `package()` 手工 `install -m 500 syslogd ${BINDIR}/`，或打 patch。
- R38 义务：产物是可执行文件 ⇒ 必须建 **`archives/s/sysklogd/commands.json`**（软件级，
  CI L0k / preflight PF8 校验；`templates/commands.json.template`）。
- `klogd` 若最终不交付，PR 正文与 notes 必须写明是"已知限制"，不能默认沉默
  （否则会被审查判定"适配完整性不足"R40 —— 系统底层类库编译通过≠适配完成）。

## 风险清单（构建阶段按序验证，未验证项已标注）

| # | 风险 | 证据 | 状态 |
|---|---|---|---|
| K1 | `_syscall3` 未定义 ⇒ klogd **链接期** `undefined symbol: ksyslog`（初稿"编译期未声明函数即报错"已被 §9.5 A/B 对照证伪） | klogd.c:280-286 + sysroot 两条 grep 均空 + §9.5 b0-report.log | **已坐实**（编译步 CC_RC=0、链接步 ld.lld 首错，见 §9.5） |
| K2 | `-fno-strength-reduce` 是 GCC 专有 flag，clang 可能 `unknown argument` | Makefile:23 | **规避成立**：`conanfile.build()` 显式覆盖 SKFLAGS、未带该 flag；§9.2/G1 编译行零命中、§10.4 G2 `conan create` 全绿 |
| K3 | `CC= gcc` 硬编码，profile 只给 clang | Makefile:20 + profile `compiler_executables` | 已确认需 override |
| K4 | `syslogd.c` 的 `!__GLIBC__` 支路声明 `int len`（845 行），而 1194 行 `recvfrom(...,&len)` 要 `socklen_t *` ⇒ `incompatible-pointer-types`（clang16+ 转 error；本 profile 是 clang15） | syslogd.c:845/1194 | **已规避**：补丁 0002 把非 glibc 支路的 `len` 也改成 `socklen_t`；§9.2/G3 编译 0 error、§10.4 G2 全绿 |
| K5 | `sys/msgbuf.h` MISSING，但被 `#ifdef SYSV` 的 `#else` 支路挡住 ⇒ **配方不得丢掉 `-DSYSV`** | prescan + 头文件表 | 已定性 |
| K6 | 硬编码 `/etc/`：`UTMP_FILE`(563)、`_PATH_LOGCONF`(569)、`_PATH_LOGPID`(577/584)、`klogd.c:295`；纯 Makefile **无 `--sysconfdir` 可传** | prescan PSCAN-PATH-001 | 已确认（运行期需 notes 记录） |
| K7 | `syslogd.c:1266 chmod(path,0666)` 在 HMDFS 上可能无权限效果 | prescan PSCAN-HMDFS-002，kb_ref **E046** | 已知非阻塞 |
| K8 | 上游无 `make check`；`make test` 含 `oops.ko` 内核模块目标 ⇒ OHOS 上必挂 | Makefile:78/141-142；设备实测 `ls /lib/modules` → **RC=1 No such file**、`ls /usr/src` → **No such file**、`uname -r` → **`HongMeng Kernel 1.12.0`** | **已坐实** |

## 上游测试清点（R51 第一步，必做）

- **无 `tests/` 目录**（`ls -d tests test` → 均 No such file or directory）
- **无 `make check` 目标**（Makefile 无 `check:`）
- 唯一真实测试程序 `syslog_tst.c`（1806 字节）→ 目标 `syslog_tst`（Makefile:89）：
  内容是 `openlog("DOTEST", LOG_PID, LOG_DAEMON)` 后把 stdin 逐行喂进 syslog 的
  **交互回环程序，非断言式、无退出码判定**
- `syslog-tst.conf` 是 **0 字节空文件**
- `tsyslogd`(Makefile:92-93) / `tklogd`(95-96) 是 `-DTESTING` **编译变体**，不是测试
  （二者**不属** `Makefile:78 test:` 依赖，`tklogd` 尤其不在 `make test` 的产物清单里）
- `ksym`(Makefile:116-120) 由 `ksym.c -DTEST` 构建，属内核符号表工具自测
⇒ 上游"可运行断言用例"数 = **0**。PR 正文须按 R51 逐条写"具体技术原因"
（K8 的 `/lib/modules` 缺失是设备实测事实，不是"没环境"这类被明令禁止的理由）。

## 工具链缺口（本次实证，未改共享 scripts/）

1. **`init-archive` 对 `build_system=make` 没有可用模板**（RC=0 但整段降级）：
   ```
   ✅   目录已就绪
   ✅   manifest.yaml 已生成
   ⚠️   conandata.yml 模板不可用，跳过
   ⚠️   conanfile.py 模板不可用（make），跳过
   ⚠️   test_package 模板不可用（test_package-conanfile-autotools.py），跳过
   ⚠️   test_package/MANIFEST.yml 模板不可用，跳过
   ✅   notes.md 已生成
   ⚠️   验证缺失: ['conanfile.py', 'conandata.yml']
   ```
   ⇒ 骨架只落出 `manifest.yaml` + `notes.md` 两个**文件**；`conandata.yml` 由本次**手工静态编辑**补出。
   ⚠ 更正：`init-archive` 同时建了 `patches/`、`reports/`、`test_package/`、`packaging/`
   **空目录**（实测 `find archives/s/sysklogd -type f` 只有 3 个文件 ⇒ 这些目录 0 内容；
   git 不跟踪空目录，故本次提交不含它们）。即 `test_package/` 是**空目录**、
   不是"没有该目录"、也不是"里有空壳文件"。
   ⇒ W2 结构完整性检查（finish step [5/10] L0a-L0e：要求 test_package/ 下有
   conanfile.py + 测试源文件 + MANIFEST.yml）**现在必然不通过**，构建阶段必须从零建满。
   ⇒ 好消息：**没有出现"按后缀误猜构建系统"** —— 显式传 `make` 后工具判定一致。
2. **`init-archive` 生成的 manifest 默认 `status: published` + `build_date: 当天`**，
   在**一次构建都没跑**的情况下就声称已发布 ⇒ 属假成功陷阱，本窗已改为 `pending` / 空日期。
3. **`init-archive` 生成的 `software: "{software}"`、`build_system: "{BUILD_SYSTEM}"` 占位符未替换** ⇒ 本窗已手工填实。
4. 本窗**未跑 `build`**，故未触发主理已记录的 Step9 重跑 `conan-init` 把
   `test_package/test.c` 与 `MANIFEST.yml` 重置成 printf/TODO 空壳的问题；
   当前 `test_package/` 为空目录 ⇒ 不存在"空壳文件被误判成假 G2 通过"的风险，
   但也意味着 **`test_package/` 必须在构建阶段从零建**（PF3 测试闸 + CI L0c/L0e 会拦空壳）。
   提醒：`test_package/MANIFEST.yml` 模板产物**本身不是合法 YAML**（`<TODO: …>` 裸标量撞 `: `），
   填数时整段加引号。

## 备注：本次留下的越界痕迹（如实记录）

`init-archive` 调用时**未在命令行导出 `OHC_RESULT_OUT`**（只在 `lang-preflight` 那次导出了），
R46 兜底把 `task_started` 草稿写进了 ECS 默认路径
`/storage/Users/currentUser/ohpcd-ai-worker-result.json`（覆盖了该共享落点）。
本任务的 `lang_checked` 草稿与 `task_started` 草稿均已另存到
`/storage/Users/currentUser/tmp/uc2/sysklogd/`（`result.json` / `result-task_started.json`）。
sisl 有独立目录 `tmp/uc2/sisl/`，其产物不依赖该共享落点。
**后续所有 ohc-run 命令必须显式 `export OHC_RESULT_OUT=/storage/Users/currentUser/tmp/uc2/sysklogd/result.json`。**

## 证据文件一览（设备侧，全部绝对路径）

```
/storage/Users/currentUser/tmp/uc2/sysklogd/preflight_check.log
/storage/Users/currentUser/tmp/uc2/sysklogd/recipe-search.log
/storage/Users/currentUser/tmp/uc2/sysklogd/graph_help.log
/storage/Users/currentUser/tmp/uc2/sysklogd/kb_index_syslog.log
/storage/Users/currentUser/tmp/uc2/sysklogd/engine_klog.log
/storage/Users/currentUser/tmp/uc2/sysklogd/lang-preflight.log
/storage/Users/currentUser/tmp/uc2/sysklogd/prescan.log
/storage/Users/currentUser/tmp/uc2/sysklogd/prescan.yaml
/storage/Users/currentUser/tmp/uc2/sysklogd/init-archive.log
/storage/Users/currentUser/tmp/uc2/sysklogd/result.json              (R46 draft: lang_checked)
/storage/Users/currentUser/tmp/uc2/sysklogd/result-task_started.json (R46 draft: task_started)
/storage/Users/currentUser/tmp/uc2/sysklogd/sysklogd-1.5.1.tar.gz    (90011 B, sha256 见 manifest)
/storage/Users/currentUser/tmp/uc2/sysklogd/sysklogd-1.5.1/          (解包源码)
/storage/Users/currentUser/tmp/uc2/sysklogd/PREFLIGHT.md             (本次调查全文)
```

---

# 配方编写回合（主理-9 / 子代理，2026-09-23）

> **本回合边界**：只写文件 + 只做静态自检。设备构建槽被另一个包占用，按硬性禁令
> **未执行任何 `conan create` / `make` / `configure` / `conan-verify` / `finish` / `submit`**。
> 因此下文所有"结论"分两类：**已取证事实**（头文件扫描、Makefile 行号、补丁 dry-run/真实应用）
> 与 **待构建闸口验证项**（明确标注，绝不当作已通过）。

## 一、症状 → 根因 → 最小复现（klogd，本包核心难点）

> ⚠ **本节初稿对症状的表述（"编译失败/第一条真实报错应为 call to undeclared
> function `_syscall3`"）已由 §9.5 的 A/B 对照实验与机制探针证伪**：真实首错
> 在**链接期**（编译步 clang 把缺失的 `_syscall3` 按隐式 int 降级、只有警告、
> RC=0）。下文"症状"条目已按实况改写，其余"根因/最小复现"保留原样并注明。

- **症状（构建闸口实跑；一手依据 §9.2/G2 与 §9.5）**：`make klogd` **编译步
  RC=0**（clang 15 把 `_syscall3(int,ksyslog,...)` 按 K&R 语义解析成"返回隐式
  int 的函数声明"，只吐 5 条 `-Wimplicit-int` 警告与 1 条
  `-Wimplicit-function-declaration`），`klogd.o` 落盘；**真实首错在链接步**
  `ld.lld: error: undefined symbol: ksyslog` → `clang-15: error: linker command
  failed with exit code 1` → `make: *** [Makefile:86: klogd] Error 1`、`MAKE_RC=2`。
  打回补丁 0001 后同一命令 `MAKE_RC_WITH_PATCH=0`、`klogd` 43392 B。
- **根因（已取证，静态 + §9.5 复核）**：
  1. `klogd.c:280` 写的是 `#if !defined(__GLIBC__)` ⇒ 走"自己造 syscall 包装"支路；
  2. OHOS sysroot **不定义 `__GLIBC__`**（musl 派生，`grep -rn "define __GLIBC__"` 零
     命中、`clang -dM -E` 亦未预定义，见 §9.5 探针 PROBE 5）⇒ 该支路在此平台是**活的**；
  3. 该支路需要的 `_syscall3` 宏在整个 sysroot 头树里**不存在**
     （`grep -rn "_syscall3" $SYSROOT/usr/include` → 空、PROBE 6 命中数 0），
     `linux/unistd.h` 只带 `__NR_syslog` 号码、不带 `_syscallN` 生成器（PROBE 7 空）；
     ⇒ clang 按 C 语法的"函数声明可省略返回类型 ⇒ 隐式 int"降级，编译不阻断；
     缺的**本该由宏展开出来的函数体**在链接期以 undefined symbol 形式暴雷；
  4. 讽刺的是，另一支路要的东西**全都有**：
     `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/sys/klog.h`
     存在且第 8 行就是 `int klogctl (int, char *, int);`；
     `nm -D --defined-only libc.so` 也确认 `T klogctl`；
     `linux/unistd.h`（提供 `__NR_syslog`）也在。
  ⇒ 判定条件把平台"判反了"：**在 OHOS 上正确的支路恰恰是上游那条 `#else`（glibc）支路。**
- **最小复现（构建闸口已跑过一遍，见 §9.5）**：
  `make CC=clang SKFLAGS="-O2 -DSYSV -Wall" klogd`（回退 0001 的复现树）→
  编译步 `CC_RC=0`、**链接步** `ld.lld: error: undefined symbol: ksyslog`；
  应用 `patches/0001` 后同一命令 `MAKE_RC_WITH_PATCH=0`、`klogd` 43392 B。
  41 行、无三方代码的机制探针
  （`$HOME/tmp/uc2/sysklogd/syscall3-mechanism-probe.c`）在同一 target 上
  A/B 双臂复现同形态（详见 §9.5 与 `syscall3-mechanism-probe.log`）。

## 二、本次新增的第二处同类分支（syslogd，非依赖、非平台差异）

同源写法在 `syslogd.c:844` 又出现一次：

```
#if !defined(__GLIBC__)
        int len, num_fds;        ← 845 行（本回合实测行号）
#else /* __GLIBC__ */
        socklen_t len;           ← 848 行
#endif
```

而 `syslogd.c:1194` 的 `recvfrom(finet, ..., &len)` 要求 `socklen_t *`。
在 OHOS 上活的是 `int len` 那条 ⇒ `&len` 是**不兼容指针类型**（clang 新版按 error 处理）。
⇒ 补丁 `0002` 把非 glibc 支路的 `len` 也改成 `socklen_t`。
作用域已核：main() 内 `len` 仅出现在 1191 赋值与 1194 取地址两处；
`syslogd.c:2000` 的 `int ttyf, len;` 是 console_write() 的另一变量，**未触碰**；
`printchopped(..., int len, ...)` 是形参，**未触碰**。

## 三、头文件全量扫描（把"缺头"类风险一次性圈干）

```
$ cd <解包树> && grep -h "#include <" *.c *.h | sed "s|.*#include <||; s|>.*||" | sort -u
48 个被 include 的系统头
$ while read h; do [ -f "$SYSROOT/$h" ] || echo "MISSING: $h"; done < hdrs.txt
MISSING: linux/init.h      ← 仅 oops.c:34（内核模块测试件，不在交付目标里）
MISSING: linux/proc_fs.h   ← 仅 oops.c:35（同上）
MISSING: sys/msgbuf.h      ← 仅 syslogd.c:533，且被 #ifdef SYSV 的 #else 挡住
```

⇒ 只要 **不构建 `test`/`oops.ko` 目标** 且 **保住 `-DSYSV`**，缺头问题为零。

## 四、排除掉的方案（不是"实测失败"，是"按证据排除"）

| 方案 | 排除依据 |
|---|---|
| `CFLAGS += -DNO_SYSLOG`（既有知识 E014 的口径） | E014 的前提是"syslog 符号缺失"。本包实况**相反**：`sys/klog.h` + `klogctl` 齐备，缺的只是 `_syscall3` 宏。`-DNO_SYSLOG` 会**自断 klogd 功能**，把可修的分支问题伪装成平台不支持。⇒ 本包不采用；**这一"符号在、包装宏缺"的反差即本包的可复用差异点**（主理据此定 B 与 E014 的关系）。 |
| 只交付 syslogd、把 klogd 记为"平台不支持" | 不必要：klogctl 路径存在且语义等价（同一个 `__NR_syslog`）。R40 要求实质说明，此处**没有**说明的必要——问题可解。 |
| `-D__GLIBC__`（一个 flag 让代码走对支路） | 撒谎式开关：会连带翻转 `klogd.c:265`、`syslogd.c:844` 等**其它** `!__GLIBC__` 判定的语义，且属"配方里注入平台宏"（R8/PF5 扩面所堵的绕道）。改用真实补丁。 |
| 在补丁里写 `#if defined(__OHOS__)` 之类 | 直接违反 R8/PF5（补丁新增行不得含平台宏）。补丁因此改成**无条件走 klogctl**，判定依据是能力而非平台。 |
| `make install` | 三处不可用：`install_exec`（Makefile:129）把 syslogd+klogd 硬绑一条规则；`${INSTALL}=/usr/bin/install`；`install_man` 要 `-o root -g root`。⇒ `package()` 手工安装（-m 500 语义由 chmod 0755 + 手工 copy 承担）。 |
| 注入共享系统前缀 | 违反 R49/PF6。prefix 取 `os.path.join(self.build_folder, "prefix")`。 |

## 五、最终方案（本回合落地物）

1. `patches/0001-klogd-use-klogctl.patch` —— klogd 无条件走 `klogctl()`（`#define ksyslog klogctl`），**klogd 功能完整保留**。
2. `patches/0002-syslogd-recvfrom-socklen-t.patch` —— `socklen_t len`。
3. `conanfile.py`（手写；`init-archive` 对 `build_system=make` 无模板，缺口已上报）：
   `basic_layout` + 树内构建、`package_type=application`、只构建 `syslogd klogd` 两个目标、
   `CC=`/`prefix=`/`SKFLAGS=`（含 `-DSYSV`）/`LDFLAGS=""` 全走 make 命令行覆盖、
   `package()` 手工装 `sbin/` + `share/man/man{5,8}` + `etc/syslog.conf` + `licenses/COPYING`、
   `package_info` 只暴露 `bindirs=["sbin"]`。
4. `test_package/`：`test_consumer.c`（真实消费者：对 AF_UNIX SOCK_DGRAM 日志套接字做
   socket/connect/send，优先级用 `<sys/syslog.h>` 常量组装）+ `test_runner.sh`（13 条断言，
   含**端到端**：起 `syslogd -n -d -m 0 -f <conf> -p <私有 socket>`，注入单行与两行记录，
   再断言它们出现在配置的日志文件里）+ `MANIFEST.yml` + `conanfile.py`。
5. `commands.json`（软件级，R38/L0k/PF8），字段完全照 `archives/a/a52dec`、`archives/a/abduco` 既有 schema。

## 六、R51 上游测试清点（申报表，逐条给"为什么没跑"）

上游 `Makefile` **无 check 目标**（`grep -n "^check" Makefile` 空），唯一入口是
`Makefile:78  test: syslog_tst ksym oops.ko tsyslogd`，且它是**构建**目标、不是运行器。

| 上游测试件 | 来源 | 本回合判定 |
|---|---|---|
| `make test` 整体 | Makefile:78 | **未执行**。①要建 oops.ko（见下）；②4 个产物都无断言/无期望值；③`syslog_tst` 硬编码 `/dev/log`，非 root 绑不上。 |
| `oops.ko` | Makefile:141-142 | **本平台不可执行（已取证）**：设备实测 `ls /lib/modules` RC=1、`/usr/src` 不存在 ⇒ 无内核构建树；另外部 .ko 需签名。其依赖的 `linux/init.h`、`linux/proc_fs.h` 确认 sysroot MISSING（旁证）。**不静默删除、不伪装通过。** |
| `syslog_tst` | Makefile:89-90 | **未执行**（路径不可重定位 + 无断言）。本包用 `test_consumer.c` 覆盖同一契约并改为可断言形式。 |
| `ksym`（`ksym.c -DTEST`） | Makefile:116-120 | **未执行**；"OHOS 上 `/proc/modules` 是否可用"**尚未实测** ⇒ 列入待验清单，不预设结论。 |
| `tsyslogd` / `tklogd` | Makefile:92-96 | `-DTESTING` 版守护进程构建件，无 runner、无断言 ⇒ 不构成可运行测试。 |
| test_package 新增断言 | 本包 | **13 条**（12 条无条件 + 1 条 klogd 内核读受 `CAP_SYSLOG` 限制，非特权下诚实记 SKIP）。**本回合未运行**（禁构建）。 |

## 七、待构建闸口验证清单（每条：命令 → 预期失败点 → 第一手判据）

| # | 待验命令 | 预期失败点 | 若失败的第一手判据 |
|---|---|---|---|
| G1 | `ohc-run.py build sysklogd 1.5.1`（含 `conan create`） | clang 拒绝 `-fno-strength-reduce`（本回合已从 SKFLAGS 剔除，属"应已规避"） | 日志首条 `unknown argument: '-fno-strength-reduce'` ⇒ 说明 SKFLAGS 覆盖未生效（Makefile 变量名/引号问题） |
| G2 | 同上，klogd.o 编译步 | 补丁 0001 未生效或 `sys/klog.h` 在本 profile 不可见 | 首条真实错误若仍为 `_syscall3` ⇒ 补丁没被应用（查 conandata `patches:` 与 `export_sources`）；若为 `'sys/klog.h' file not found` ⇒ sysroot 头路径问题（与本回合扫描矛盾，需查 `--sysroot`） |
| G3 | 同上，syslogd.c 编译步 | `-Wincompatible-pointer-types` 在 clang15 是 warning、clang16+ 是 error | 首条 `incompatible pointer types passing 'int *'` ⇒ 0002 未生效 |
| G4 | 链接步 | OHOS MAC 拒绝对已签名/被改写 ELF 的操作；`LDFLAGS=""` 未生效 | `Operation not permitted` 出现在 `clang -o syslogd` 之后 ⇒ 查是否仍带 `-s`；改 `STRIP=:` 式处置（abduco 先例） |
| G5 | 树内构建写在 `self.source_folder`（hmdfs） | HMDFS umask/权限导致 .o 或 ELF 落盘失败（acpid/sed 有先例） | `Permission denied` 落在 `.o`/`-o syslogd` 上 ⇒ 整套构建转移到 tmpfs（`/data/storage/el2/base`），照 archives/a/acpid/2.0.34 的 `_choose_build_root()` 形态改 |
| G6 | `make -j1 ... syslogd klogd` 的 `-j1` 与 `cwd=self.source_folder` | `basic_layout` + `folders.build="."` 下 source/build 目录错位 | `make: *** No rule to make target 'syslogd.c'` ⇒ 打印 `self.source_folder`/`self.build_folder` 实测值再定 layout |
| G7 | `conan-verify` / test_package | 端到端断言失败：`syslogd -n -d -m 0 -f -p` 起不来或 socket 不出现 | `test_runner.sh` 的 `[FAIL] syslogd did not create its log socket` + `syslogd.out` 前 20 行（那是第一手证据；不要改判据去"绕过"） |
| G8 | test_package 的 klogd 项 | `klogctl(2)` 需 `CAP_SYSLOG` | 期望输出 `[SKIP] klogd kernel-log read ... EPERM`；若出现 `symbol`/`CANNOT LINK` 则是 0001 的真失败 |
| G9 | `make ksym` / `ls /proc/modules`（可选补强） | 本平台无 /proc/modules | 见 §6 第 4 行，未实测前不下结论 |
| G10 | 安装位可执行性（HMDFS 忽略 chmod） | `copy()` 后 sbin 内二进制无 x 位 | `[FAIL] ... installed but not executable` ⇒ 与 §R49 记录一致（构建目录天然可执行）需复核 package_folder 是否同分区 |

## 八、适用边界（若本包结论要被别人复用）

- 补丁 0001 的适用面：**任何**用 `#if !defined(__GLIBC__)` + `_syscallN()` 自造 syscall 的老 C 包
  （判据先跑 `grep -rn "_syscall" $SYSROOT/usr/include` 与 `grep -n "klogctl" $SYSROOT/usr/include/sys/klog.h` 两条）。
  在"包装宏缺、被包装的 libc 函数在"的场合，正确解是**改走 libc 支路**，不是 `-DNO_*` 关功能。
- 补丁 0002 的适用面：`!defined(__GLIBC__)` 里把 socket 长度变量声明成 `int` 的老包（同一判反根因的另一表现）。
- 两补丁都**不含平台宏**，因此在任何"提供 klogctl/socklen_t 但非 glibc"的 libc 上语义同样成立。
- 本包**不声明**任何"OHOS 不支持内核日志"的结论：klogd 的运行期限制是 `CAP_SYSLOG`（特权），属 POSIX 通用约束，不是平台差异。


---

## 九、构建闸口实测（构建验证子代理，2026-09-23）

> 口径：每条给"命令 → 首条真实错误原文 → 处置"。本轮先跑**非 conan 的 tmpfs 复现树**，
> 目的就是在不占用内存窗口的前提下把 §7 的 G1–G10 一次过完；
> 补丁 0003–0006 全部来自这一轮的真错，不在 §7 预测表内。

### 9.1 复现环境与命令
- 复现树：`/data/storage/el2/base/skl-f`（tmpfs；解包后 `patch -p1` 顺序应用 0001..0006，
  每条先 `--dry-run` 后真实应用，RC 全 0）
- 编译命令（与 `conanfile.build()` 逐字一致，仅 `prefix` 取树内路径）：
  `make -j1 CC=/data/service/hnp/bin/clang prefix=<tree>/prefix SKFLAGS="-O2 -DSYSV -Wall" LDFLAGS="" syslogd klogd`
- 终态：**MAKE_RC=0、`error:` 计数 0**，产物 `syslogd` 55744 B / `klogd` 43392 B
- 日志绝对路径：`/storage/Users/currentUser/tmp/uc2/sysklogd/{pre1.log,diag.log,diag2.log,diag3.log,e2e.log,e2e2.log}`

### 9.2 G1–G10 逐条判决

| # | 原判据 | 实测结论 | 一手证据 |
|---|---|---|---|
| G1 | `-fno-strength-reduce` 复发 = SKFLAGS 未生效 | **未复发，规避成立** | 编译行实为 `clang -O2 -DSYSV -Wall -DSYSLOG_INET -DSYSLOG_UNIXAF -DNO_SCCS -DFSSTND -DSYSLOGD_PIDNAME=... -c syslogd.c`；全日志 `grep -c fno-strength-reduce` = **0** |
| G2 | 仍报 `_syscall3` = 0001 未应用 | **未出现** | 应用后 `klogd.c:296` 为 `#define ksyslog klogctl`；klogd.o 编译通过且 klogd 链接通过 |
| G3 | 不兼容指针 = 0002 未生效 | **未出现** | `syslogd.c:848/852` 两支路均为 `socklen_t len`；syslogd.o 编译 0 error |
| G4 | 链接步 `Operation not permitted`（`-s` 残留） | **未出现** | `LDFLAGS=""` 生效：链接命令无 `-s`，链接期无 EPERM |
| G5 | HMDFS 上 `.o`/ELF 落盘 `Permission denied` | **本轮未复现**（复现树在 tmpfs；conan 侧 HMDFS 构建由 conan-verify 覆盖） | 对照实验：clang 直接往 HMDFS 写 ELF **可执行**（`hello_hmdfs` 运行成功、`ls -l` = rwxr-x---），HMDFS 只有 `chmod` 被拒（`chmod ... Permission denied`） |
| G6 | `No rule to make target`（layout 错位） | **未出现** | `basic_layout` + `folders.build="."` 下 make 在 source_folder 内正常找到 Makefile 与各 .c |
| G7 | syslogd 起不来 / socket 不出现 | **命中，但根因不是 syslogd，而是 HMDFS 不允许 bind AF_UNIX** | 探针（socket/bind/chmod 三步）：`/storage/Users/...`(HMDFS) → `bind: Operation not permitted`；`/data/storage/el2/base`(tmpfs) → `BIND_OK` + `CHMOD_OK`；`/dev/shm` → `bind: Permission denied`。上游 `create_unix_socket()` 把 `bind` 与 `chmod(path,0666)` 串在同一判据里，故该步在 HMDFS 上必失败。**处置**：`test_package/conanfile.py` 的 scratch 目录改落 tmpfs（`_scratch_dir()`；tmpfs 不可用时退回 build_folder，让端到端**响亮失败**而不是静默跳过） |
| G8 | klogd 期望 `[SKIP] ... EPERM` | **命中，但不是 EPERM，而是 pid 文件** | 原文 `Can't open or create /var/run/klogd.pid.`、rc=1。根因三条并列：`PidFile` 为编译期固定（`_PATH_VARRUN "klogd.pid"`，随上游 `-DFSSTND`）；klogd 的 getopt 串 `c:df:iIk:nopsvx2` **无任何 pid 文件覆盖入口**；本设备实测 `ls /var/run` → `No such file or directory`。**处置**：分类改为 SKIP 并写明两条并列原因；`symbol`/`CANNOT LINK`/`Error loading shared library` 仍判 FAIL |
| G9 | `/proc/modules`（`make ksym`） | **未测**：`ksym` 不属配方构建目标，test_package 也不跑它 | 不给结论 |
| G10 | 安装位 x 位被 HMDFS 吞 | **未出现** | tmpfs 侧 `tprsbin/` 两条「已安装且可执行」断言 PASS；HMDFS 侧同结论由 9.2/G5 的对照实验支持 |

### 9.3 §7 预测表之外的四条真错（已全部落补丁）

按"第一条真实错误"逐条定位；四条判据一律是 libc/内核头**能力事实**，新增行不含任何平台宏。

1. **0003 `dprintf` 名冲突** — 首错原文
   `syslogd.c:824:13: error: static declaration of 'dprintf' follows non-static declaration`
   （`note: previous declaration is here` 指向 sysroot `stdio.h:145` 的 `int dprintf(int, const char *__restrict, ...)`）。
   机制：上游在 `syslogd.c:821-823` 写的是 `#if defined(__GLIBC__) → #define dprintf mydprintf → #endif`，
   即**只为 glibc 做过改名**；musl 派生 sysroot 同样声明 POSIX `dprintf()` 却不定义 `__GLIBC__`，守卫落空。
   该符号是 file-local 静态符号（全树仅 syslogd.c 一处使用，`grep -c dprintf` 80 次），无条件改名对无 `dprintf()` 的 libc 是空操作。
   一次消掉 20 条 error（含随后 19 条 `too few arguments to function call` 连锁）。
2. **0004 `union wait`** — 首错原文
   `syslogd.c:2107:13: error: variable has incomplete type 'union wait'`（`note: forward declaration`）。
   机制：`reapchild()` 的 `#if defined(SYSV) && !defined(linux)` 走 `#else` 支（clang 预定义 `linux`），
   其中 BSD 遗留的 `union wait` 在 sysroot `sys/wait.h` 全文 grep 无定义；`wait3()` 现带头集合的状态实参即 `int *`。
3. **0005 `sys/file.h` 不传递包含 `fcntl.h`** — 首错原文
   `pidfile.c:90:29: error: use of undeclared identifier 'O_RDWR'`（同处另有 `implicit function declaration` 的 `open`）。
   机制：`pidfile.c`/`syslog.c` 只用 `#include <sys/file.h>` 就调 `open()` 与 `O_*`；
   glibc 的 `sys/file.h` 会传递包含 `fcntl.h`，而本 sysroot 的 `sys/file.h` **全文只有 `LOCK_*` 常量与 `flock()` 原型**（已整文件读取核实）。
   另注意 `pidfile.o` 无显式规则，走 make 内建规则 → **不吃 SKFLAGS**，因此这类缺头只能靠源码补，不能靠加 flag。
4. **0006 `linux/time.h` 的 `struct timespec` 重定义** — 首错原文
   `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/linux/time.h:25:8: error: redefinition of 'timespec'`
   （`note: previous definition is here` → `aarch64-linux-ohos/bits/alltypes.h:237`）。
   机制：该头是安装出来的内核头（文件头注明由 bionic 的 `kernel/tools/update_all.py` 生成），内部 `struct timespec` **无守卫**；
   `klogd.c:266` 与 `ksym_mod.c:120` 的上游非 glibc 分支各引一次。两文件对内核头符号**零使用**
   （`timeval|timezone|timespec|time_t|gettimeofday` 全文 grep 皆空）⇒ 换成用户态 `<time.h>` 不改语义。

### 9.4 本轮另外钉死的运行期事实（写 PR 正文时用，勿超证据）

- **`/var/run` 在本设备不存在**，且 `/etc` 是 `/system/etc` 的符号链接（只读系统分区）。
  后果：两个守护进程的 pid 文件都无处可写。`syslogd` 的写入被上游 `if (!Debug)` 守卫挡住
  （这就是端到端断言用 `-n -d` 能跑通的原因）；`klogd` 的 pid 文件块无 `Debug` 逃逸
  ⇒ **打包产物在本设备以非特权身份不能常驻**，`klogd -n -s -o -f <file>` 亦在读取内核日志之前就 Terminate。
  属平台既有事实，不是本包引入的缺陷；本包不改上游行为（klogd 无 CLI 覆盖入口，加参数属改功能，需另行批准）。
- **`klogctl` 的证据只到链接期**：`lld` 对可执行文件里的未定义符号是硬报错
  （本轮用对照程序复现：`ld.lld: error: undefined symbol: qoder_symbol_that_does_not_exist`），
  而 klogd 链接成功 ⇒ 0001 的符号解析成立。**禁止**据此写"klogd 功能已真机验证"。
- test_package 判决实测：`SUMMARY checks=13 failures=0 skips=1`、`VERDICT=PASS`、驱动退出码 0
  （日志 `e2e2.log`）。分母仍按 §6 的注册口径申报 5 个上游测试产物，`oops.ko` 逐项记未执行 + 具体原因。

### 9.5 补丁 0001 的 A/B 对照与机制探针（W4 整改回合补跑，2026-09-23 20:56–20:59）

> **本节用途**：把 §一 初稿"编译期直接炸在 `_syscall3` 未声明"的**错误预测**改写成
> 一手证据支撑的**链接期首错**事实；也是路径 B 草稿
> `DRAFT-sysklogd-1.5.1-syscalln-macro-missing-defers-to-link` 的核心判据。
> 复现树、命令、环境变量与退出码全部留档，可回指。

**复现环境**（`b0-control-probe.sh` 头部实录）：
- 时间：`2026-09-23 20:56:52`；机器：HarmonyOS `HongMeng Kernel 1.12.0` aarch64；
- 编译器：`clang version 15.0.4`（`Target: aarch64-unknown-linux-ohos`，路径
  `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/`）；
- SRC：`/data/storage/el2/base/skl-f`（tmpfs、已顺序应用 0001..0006、`syslogd 55744 B`+`klogd 43392 B`）；
- DST：`/data/storage/el2/base/skl-b0`（SRC 的副本，再反向应用 0001）。

**A/B 双臂（真实退出码与首错原文，逐字摘自 `$HOME/tmp/uc2/sysklogd/b0-report.log`）**：

| 臂 | 命令 | 退出码 | 首错形态 |
|---|---|---|---|
| **B0（回退 0001 后的上游原样）** | `clang -O2 -DSYSV -Wall -DFSSTND -c klogd.c`（编译步）| **CC_RC=0** | 无 `error:`；15 条 `warning:`（含 5 条 `klogd.c:287: warning: type specifier missing, defaults to 'int'; ISO C99 and later do not support implicit int [-Wimplicit-int]`） |
| **B0（全量 make klogd）** | `make -j1 CC=clang SKFLAGS="-O2 -DSYSV -Wall" LDFLAGS="" klogd`（编译+链接） | **MAKE_RC=2** | `ld.lld: error: undefined symbol: ksyslog` → `clang-15: error: linker command failed with exit code 1` → `make: *** [Makefile:86: klogd] Error 1`（`b0-report.log` 第 211/221/222 行） |
| **A（应用 0001）** | 同 B0 全量命令，DST=skl-f | **MAKE_RC_WITH_PATCH=0** | `klogd` 43392 B 落盘 |

⇒ **首错在链接期、不在编译期**。补丁 0001 换的是**符号解析路径**
（`_syscall3` 宏展开出来的 `ksyslog` 本地 stub ⇒ 走 libc 的 `klogctl` 真符号），
不是"让编译能过"。

**41 行、无三方代码的机制探针**（`syscall3-mechanism-probe.c`，同一 OHOS target 上复现）：

```
PROBE 1  上游写法、只编译        → COMPILE_RC=0，仅 6 条 warning
                                   （5× -Wimplicit-int + 1× -Wimplicit-function-declaration）
PROBE 2  同一 object、链接        → LINK_RC=1，ld.lld: error: undefined symbol: ksyslog_probe
PROBE 3  -DUSE_WRAPPER（走 klogctl）、编译 → COMPILE_RC_WRAPPER=0
PROBE 4  -DUSE_WRAPPER、链接              → LINK_RC_WRAPPER=0，probe-wrapper 18816 B
PROBE 5  clang 是否预定义 __GLIBC__       → 空 ⇒ 上游 !__GLIBC__ 支路在 OHOS 上是活的
PROBE 6  _syscall3 / __syscall_keyword 等 sysroot 内命中数 → 全 0
PROBE 7  linux/unistd.h 是否带 _syscallN 生成器 → 空（只有 __NR_* 号码表）
```

**结论口径（供正文/notes 共用）**：

1. 上游 `#if !defined(__GLIBC__)` + `_syscall3()` 在 OHOS 上的失败**形态**是
   "**编译期 clang 按隐式 int 降级、只有 5 条 -Wimplicit-int 警告；链接期 lld
   报 undefined symbol**"——不是"编译期直接未声明函数即 error"。
2. 补丁 0001 之所以**必要且充分**：它把"本该由 `_syscall3()` 宏展开出来的
   `ksyslog` 本地 stub"换成 libc 的真符号 `klogctl`，走通链接；**功能不裁剪**。
3. 因此 `klogctl` 的**证据只到链接期**：`lld` 对可执行文件的未定义符号是硬报错，
   `klogd` 链接成功 ⇒ 0001 的符号解析成立；运行期读内核日志的能力**另受
   `CAP_SYSLOG` 与 pid 文件路径约束**（见 §9.4），test_package 相应断言记 SKIP，
   **禁止**据此写"klogd 运行期已真机验证"。

**一手日志与脚本（全部绝对路径，可回指）**：
- `/storage/Users/currentUser/tmp/uc2/sysklogd/b0-control-probe.sh`（3048 B，驱动）
- `/storage/Users/currentUser/tmp/uc2/sysklogd/b0-report.log`（16850 B，双臂完整判决 + 探针 1–7）
- `/storage/Users/currentUser/tmp/uc2/sysklogd/syscall3-mechanism-probe.c`（1835 B，41 行、无三方代码）
- `/storage/Users/currentUser/tmp/uc2/sysklogd/syscall3-mechanism-probe.log`（2801 B，探针 A/B 双臂输出）

**补丁 0001 头部的"cannot compile"措辞**：本轮同步更正，新表述与 §9.5 事实同源
（"does NOT fail at compile time ... defers to the link step ... ld.lld reports
undefined symbol: ksyslog"）。整改回合另按 §11.2 重生成 0001/0002，剥去
`2000-01-01 00:00:00` 伪时间戳，令头部与 0003-0006 的裸
`--- a/<file>` / `+++ b/<file>` 风格一致。

---

## 十、资源预算实测与正式闸口（构建验证子代理第二次派发，2026-09-23 20:23–20:35）

> 口径：每条给"命令原文 → 末行证据 → 判读"。上一轮 `--mem 6000` 五连撞 `SLOT_FAIL`
> 的取证与本轮的档位选择一并写在这里，避免下一个窗口再猜一次。

### 10.1 ⓓ 先评估：峰值探针（不靠猜）

- 复现副本树 `/data/storage/el2/base/skl-probe`（由前任的 `skl-f` 拷出后
  `rm -f ./*.o syslogd klogd`，**未改动 `skl-f` 原件**）
- 命令（`make` 部分与 `conanfile.build()` 下发者逐字一致）：
  `python3 /storage/Users/currentUser/Desktop/huawei/经验文档/tools/memcap-run.py --probe --mb 2000 --interval 0.2 -- /bin/sh -c "make -j1 CC=/data/service/hnp/bin/clang prefix=/data/storage/el2/base/skl-probe/prefix SKFLAGS=\"-O2 -DSYSV -Wall\" LDFLAGS=\"\" syslogd klogd"`
- 末行证据：`MEMCAP[probe] peak=94MB budget=2000MB rc=0 用时1.9s`
  产物 `syslogd` 55744 B / `klogd` 43392 B —— 与 §9.1 的 tmpfs 树逐字节同尺寸。
- **判读**：本包编译峰值是 **94 MB 量级**。上一轮把 `--mem` 填成 6000 属档位错配：
  `build-slot.sh` 的 `--mem` 在取槽前 fail-fast（149–155 行）、等槽期间每轮再判一次（170–177 行），
  `--wait` 只排槽**不排内存**；而扩容第 3 槽的门槛是 `2×--mem` ⇒ 填 6000 等于要求 12 GB。
  设备 `MemAvailable` 整晚在 4700–6242 MB 抖 ⇒ 永远进不去。
  旁证：`tmp/uc2/sysklogd/verify-001.log` 五次 `SLOT_FAIL` **每次都印**
  `SLOT_STATUS: 本机在用 0/2（硬上限 3）→ 还可取槽 ✅` —— 槽一直是空的，卡的是内存地板，不是并发闸。

### 10.2 再执行：本轮用的档位与理由

- 闸口形态（两次真跑同一条外壳）：
  `sh 经验文档/tools/build-slot.sh --wait 300 --mem 3000 -- python3 经验文档/tools/memcap-run.py --mb 1500 --avail-factor 1.2 --slow --interval 0.5 -- <ohc 命令>`
- `--mem 3000`：设备级排队 + 内存地板照过，**不因带预算而豁免**；取值按本包实测峰值放足，非 6000 的死等档。
- `--mb 1500`：94 MB 峰值上浮约 16 倍，覆盖 conan 驱动与 test_package 自身开销；
  `--avail-factor 1.2` ⇒ 可用内存不足 1800 MB 时 rc=91 直接拒启（比"等 6000"更贴本包实际占用）。
- `--slow` 的实际作用只有 `nice -n 19`（配方本就是 `-j1`）。按手册/05 ⓥ：**慢速本身不省内存**
  （本机无内核级封顶：`ulimit -v` 不生效、hishell cgroup 属 memmgr 只读、无 root 无 systemd），
  真封顶的只有预算这一件，故 `--mb` 不可省。
- 末行证据（两次真跑，逐字抄自日志）：
  `MEMCAP[run] peak=126MB budget=1500MB rc=0 用时25.1s` （conan-verify，含 `conan create` + 端到端）
  `MEMCAP[run] peak=124MB budget=1500MB rc=1 用时41.2s` （finish；rc=1 来自 Step6/Step10，非 W3）
  ⇒ 正式闸口全程**真实峰值 126 MB**，`test_package/MANIFEST.yml` 的 `max_rss_mb` 按预算 1500 登记，
  并把实测 126 / 探针 94 两个数一并写在该文件注释里，不拿预算冒充实测。
- 槽位与排队：起构建前 `ps -eo args | grep -c '[c]onan-verify svgpp'`、
  `grep -c '[o]hc-run.py finish svgpp'` 均为 0；本轮 `SLOT_OK 20:29:01`（在用 0/2 与 1/2 各一次）、
  收尾印 `SLOT_DONE:ok MemAvailable=5092MB`。**未发生 SLOT_FAIL，未 kill 任何进程。**

### 10.3 一次真实失败与它的定性（先留证据再重试）

- 20:25 首轮 `conan-verify` **G2 FAIL**。`reports/conan-create.log` 第一条真实错误原文：
  `sysklogd/1.5.1@ohpcd/stable: WARN: network: Error downloading file https://www.infodrom.org/projects/sysklogd/download/sysklogd-1.5.1.tar.gz: ... Failed to resolve 'www.infodrom.org' ([Errno -3] Try again)`（重试 2 次后 `ERROR: ... Error in source() method, line 101`）
- 同一时刻 `nslookup www.infodrom.org` 印 `communications error to 8.8.8.8#53: timed out` + `SERVFAIL`；
  20:28 复测 `python3 -c socket.getaddrinfo` 正常解析（CNAME `luonnotar.infodrom.org` → `217.114.79.202`），
  连试 3 次 `curl` 全 `HTTP=200`。
- **定性：设备侧 DNS 瞬时抖动，不是配方/依赖/上游问题。** 处置只有一条：同一条命令原样重跑（第 2 次即通过）。
  **没有**改 `sources.url`、**没有**注入 gh-proxy 镜像、**没有**用 `file://` 本机缓存顶包。

### 10.4 G0–G4 实况（正式 `conan-verify`，不是手工复现树）

日志：`/storage/Users/currentUser/tmp/uc2/sysklogd/verify-g04.log`、
`archives/s/sysklogd/1.5.1/reports/conan-verify-report.md`、`.../reports/conan-create.log`。

| 档 | 判决 | 一手依据与口径边界 |
|---|---|---|
| G0 | ✅ PASS | 报告原文 `构建系统: unknown` ⇒ 纯 Makefile 包无预查询对象，**PASS 的含义是"无风险可查"，不是"已查到无风险"** |
| G1 | ✅ PASS | 12 项配方完整性逐条 ✅，含 `conandata.yml 完整`、`test_package/ 存在 (R28)`、`MANIFEST.yml 存在` |
| G2 | ✅ **真 PASS** | `conan create` 成功建包 `6b129b068851896169fae42d399fa922d239ce8a`，并 `Launching test_package` → `Running test()` → `SUMMARY checks=13 failures=0 skips=1`、`VERDICT=PASS`；与 §9.4 手工 e2e 同判据同结果 |
| G3 | ✅ PASS | R26：无 `bin/`、无 `lib/`（可执行包）⇒ `无系统同名库冲突`，结论成立 |
| G4 | ⚠ **PASS 但是空过** | 报告原文 `## G4: ✅ PASS / ⚠️ 无法找到程序包 ID`，L2/L4/L5 一律 `⏭️ 跳过（无 cache 路径）`。**不得**据此写"产物完整性已验证" |

- **G4 空过的根因（框架侧缺陷，本包不改）**：`scripts/ohc/conan_verify.py:737` 按旧版 conan 的三层结构取
  `listing["Local Cache"][software][ref]["revisions"]`，而 conan **2.29.1** 的
  `conan list '<ref>:* --format=json'` 第二层键已是**完整引用** `sysklogd/1.5.1@ohpcd/stable`
  （实测 `KeyError: 'sysklogd'`，`TOP ['Local Cache']` → `L2KEYS ['sysklogd/1.5.1@ohpcd/stable']`）。
  框架改动须单独 PR ⇒ 只登记，不动 `scripts/`。
- **产物完整性改由手工取证覆盖**（同一 `package_id`，`conan cache path` 实得
  `/storage/Users/currentUser/tmp/ch/home-主理-9-sysklogd/p/b/sysklebc21127a0538/p`）：
  - 包内文件 10 个：`sbin/syslogd`、`sbin/klogd`、`etc/syslog.conf`、`licenses/COPYING`、
    `share/man/man8/{sysklogd.8,syslogd.8,klogd.8}`、`share/man/man5/syslog.conf.5`（另有 conaninfo/conanmanifest）
  - `sbin/syslogd` **55744 B** / `sbin/klogd` **43392 B** —— 与 10.1 探针树、§9.1 tmpfs 树三处同尺寸
  - `file sbin/syslogd` = `ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped`
    ⇒ `LDFLAGS=""`（不在链接期 strip）在最终产物上得到印证，与 abduco/acorn-fdisk 记录的 MAC 教训一致
  - 从包内路径直跑 `sbin/syslogd -v` → `syslogd 1.5.1`，`RC=0`
- **test_package 未被刷新**：`verify` 与 `finish` 两轮各自的 `MD5_BEFORE/MD5_AFTER` 四文件全等
  （驱动脚本 `diff` 输出 `MD5_IDENTICAL`），`ohc-run.py build` 全程未调用。
- **conandata 未被改写**：两轮 `CONANDATA_URL_AFTER` 仍是
  `url: "https://www.infodrom.org/projects/sysklogd/download/sysklogd-1.5.1.tar.gz"`（未出现 `file://`/镜像），
  提交态另以 `git grep -n "file://" HEAD -- archives/s/sysklogd` 复查。

### 10.5 finish：W3 达成，其余步骤的缺口如实登记

- Step5/10 `W3: 本地 CI 模拟验证 (sysklogd/1.5.1), 超时预算 3600s` → `✅ setup.sh 通过` →
  `✅ 本地 CI 模拟通过 (日志: archives/s/sysklogd/1.5.1/reports/w3-local-ci.log)` → `✅ W3 本地 CI 模拟通过`。
- W3 日志内部的逐档判决（`head`/`tail` 原文）：`setup.sh (RC=0)`、conan 2.29.1、
  远端 `ohpcd → https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/` 自动添加、profile `ohos-aarch64`；
  `L0_RESULT=pass: all checks passed`、`L1_RESULT=pass: test_package executed`、
  `L2_RESULT=skip: no bin/ dir`、`L4_RESULT=pass: patches clean`、`L5_RESULT=warn: no artifacts found`、
  `Build Summary Total: 1 / Success: 1 / Failed: 0`、末两行
  `[step] All packages built and tested successfully ✅`、`[step] Pre-download: conandata.yml 已还原为官方 URL`。
  **L2/L5 的 skip/warn 不是判据被绕过，而是本包按系统守护进程惯例装到 `sbin/`**：
  `grep -rl '"sbin"' archives/ | wc -l` = **119**（同族先例 `archives/a/apcupsd/3.14.14.1`、
  `archives/a/autofs/5.1.9`、`archives/d/dhcpcd/10.3.2`、`archives/b/base-passwd/3.6.8` 的
  `package_info()` 都写 `bindirs = ["sbin"]`），而这两档的检查器只找 `bin/`。
  产物真实可执行性由 10.4 的手工取证与 L1（端到端 13 断言）覆盖。
- **W3 判据文件已生成**：`archives/s/sysklogd/1.5.1/.ci-result.json`
  `"exit_code": 0`、`"step": "W3_local_ci"`、`"integrity_hash": "d57053ecc4216dec"`、
  `"log_sha256": "27589b97c56e964fb4793698f880f85c551182814d5ce9c0a3e103c43d219e94"`、`timestamp 2026-09-23T20:33:44`。
  ⚠ 该文件被 `.gitignore:238` 忽略，且仓内 `git ls-files archives | grep -c ci-result` = **0**（全仓无一例入库）
  ⇒ 本包同样**只留盘不入库**，不为此破例 `git add -f`。
- Step3/10 `❌ G0: 找不到原始 tarball` + `⚠️ G0 干净构建验证失败` —— 即 `经验库 12b:105` 记的
  `clean_verify.py` 硬编码 `CONFIG_SHELL ./configure` 对纯 Makefile 包入口不适用；
  本轮首条报错停在"找不到 tarball"、未走到 configure 127。**未伪造 configure、未改 `scripts/`**。
  该步失败**不阻塞**：Step4 随后重跑 conan-verify 并 `✅ conan-verify 通过`。
- Step6/10 `finalize-archive RC=2` 五告警，其中两条经查是**检查器自身误报**：
  ① `状态不一致: notes=published\` + \`build_date: 当天\`\` vs manifest=built` —— 匹配器把 notes.md 里
     "构建阶段务必改回枚举值"那段**说明文字**当成了状态字段值；
  ② `补丁数不一致: manifest=8 vs disk=6` —— `finalize_archive.py:145` 用
     `str(patches_applied).split(",")` 数条目，而 6 条补丁描述本身含逗号 ⇒ 8 是解析假数，盘上确为 6 条。
  真实缺口四条（**在 W3 判据之外，交主理处置，本回合不越范围补**）：
  软件级 `archives/s/sysklogd/README.md` 缺、release/debug tar.gz 缺、
  Step8 `gen_summary 失败: 'str' object has no attribute 'append'`（SUMMARY.md 未生成）、
  Step10 三项未就绪（`reports/test-report.md`、`packaging/` 打包、`.staging-verified`）。
- harness 自行改的两处**保留、不回滚**：`manifest.yaml` `status: pending → built`、
  `notes.md` 末尾追加"编译结束/最终状态"两行。`build_date` 曾留空、**已在 §11.1 补为
  `2026-09-23`**（口径同源 `.ci-result.json` `timestamp: 2026-09-23T20:33:44`）。
- Step9/10 `✅ 仅含配方变更 (15 文件)，无框架文件`（W2 原子性通过）。
- 结论口径：**W3 与 G0–G4（G4 除空过部分已手工补证）已齐**；
  本轮**不下**"可以提审/CI 会通过"的结论（Step6/Step8/Step10 缺口未清 + W4 P1/P2
  整改见 §11）。

---

## 十一、W4 整改回合（子代理，2026-09-23 21:20 起）

> **触发**：W4 首轮独立审计判 **fail（P0=0 / P1=3 / P2=4 / P3=7）**，审的是
> HEAD `b66ab68b409edce7e3b49e2509d7a5705273d26a`（15 文件 md5 与 blob 全等）。
> 本节按 3 条 P1 + 2 条指定 P2 逐条整改，并同步修正两处旧结论（与 §9.5 A/B
> 对照 + 机制探针冲突）与 PR 正文的路径口径（A → B=create）。

### 11.1 P1-1 `manifest.yaml` 交付态口径与 `build_date`

**旧**（被审正文第 5-9、18-24 行）：
> ★★★ 本目录是【前置调查骨架】，不是交付物 ★★★ / 尚未执行任何 conan create · make · configure /
> 因此 status 不是 published/built / 也不填 `.ci-result.json` / `reports/`；
> 本包尚未构建 ⇒ 不填上述任一值，用 pending；build_date 空。

而**同文件实值**已是 `status: built`，`.ci-result.json` 也已由 harness 生成 ——
**三处必有一假**。实况：构建确已发生、G0–G4 与 W3 均达（§10.4 / §10.5）。

**整改**（本文件所在 worktree 现状）：
- 头部 5-18 行整块重写为"状态：已构建、已验证（未 upload）"，把
  `conan-verify G0-G4`、`conan create` 包 ID、`test_package 13 断言`、
  `W3 .ci-result.json 判据` 逐条挂上具体值与文件路径；特别标出
  **G4 为 "PASS 但空过"** —— `scripts/ohc/conan_verify.py:737` 按旧三层缓存结构
  取包 ID、在 conan 2.29.1 下打印「无法找到程序包 ID」并跳过 L2/L4/L5，
  属框架缺陷，产物完整性由 §10.4 的手工取证覆盖，**不得把 G4 当独立产物证据引用**。
- `build_date: "2026-09-23"`（口径按 `ARCHIVE-SPEC.md:282-283` `YYYY-MM-DD`；
  **一手依据 = `.ci-result.json` 的 `timestamp: 2026-09-23T20:33:44`**，
  与本文件末尾「编译结束: 2026-09-23 20:33」同源，**不新造时间戳**）。
- `configure_options:` 上方"构建闸口尚未跑过 ⇒ 下面是配方声明的命令行"一句改为
  "已在 tmpfs 复现树与 conan 侧各跑过一遍"（对应 §9.1 MAKE_RC=0 + §10.4 G2）。
- `dependencies:` 上方"（conanfile 未生成⇒依赖集空）"改为交付态判据 +
  把前置调查轮的 `preflight_check RC=0` 降为**旁证**（对应审计 P3 关于 W0 时效的
  意见）。
- `knowledge_gained: []` 改为已入库的两条 B 草稿文件路径：
  `DRAFT-sysklogd-1.5.1-syscalln-macro-missing-defers-to-link.{md,kv}`。

**核实命令**（本回合已在设备执行）：

```bash
python3 -c "import yaml; m=yaml.safe_load(open('archives/s/sysklogd/1.5.1/manifest.yaml'));\
print(m['status'], m['build_date'], len(m['knowledge_gained']))"
# 输出: built 2026-09-23 2
```

### 11.2 P2-b 补丁 0001/0002 伪时间戳与 0001 内部注释更正

**旧**（被审正文）：0001 与 0002 的 `---/+++` 行都带 `2000-01-01 00:00:00.000000000 +0000`
的手工戳，全仓 13180 个 `.patch` 只有这 2 个这样写；0003-0006 反而**没**时间戳，
形成"六条补丁两种风格"。审计据此挂 R3 嫌疑。

**处置路径选择**：`refresh-patch --auto` 走的是"orig 树 vs work 树"整文件比对，
输出文件名按文件路径自动编号，会**重排现有语义命名**（`0001-klogd-use-klogctl.patch`
→ `0001-klogd.c.patch` 之类），且需要一整套已解包的 orig + work 双树。本包
6 条补丁按**语义能力点**命名（klogd-use-klogctl / recvfrom-socklen-t /
dprintf-name-collision / wait3-int-status / include-fcntl-h / drop-linux-time-h），
`refresh-patch --auto` 不适配该命名模型。

**整改**：
- 0001/0002 头部剥去 `2000-01-01 00:00:00` 伪时间戳，与 0003-0006 保持裸
  `--- a/<file>` / `+++ b/<file>` 风格（同 difflib.unified_diff 默认输出）。
- **0001 内部注释同步更正**：原写「so the old "not glibc => roll our own syscall"
  branch **cannot compile** on such a libc」是 §一初稿"编译期直接失败"错误预测
  在补丁文本里的镜像，与 §9.5 的 A/B 实测（CC_RC=0、真实首错在链接期
  `ld.lld: undefined symbol: ksyslog`）冲突。改成"does **NOT** fail at
  compile time: clang parses the missing macro as an implicit-int function
  declaration (only -Wimplicit-int warnings), klogd.o still builds, and the
  first real error defers to the link step, where ld.lld reports 'undefined
  symbol: ksyslog'"。**hunk 语义（源码替换：`_syscall3(...)` 自造 syscall
  → `klogctl()` 支路）未变**。
- 0002 只剥时间戳，正文与 hunk 不变。

**核实命令**（本回合已在设备执行）：

```bash
# 1. 全仓伪时间戳归零
grep -rl "2000-01-01 00:00:00" archives/ --include="*.patch"   # → 空
# 2. 六条补丁在 pristine 树上 dry-run 全 0（toybox patch）
for p in archives/s/sysklogd/1.5.1/patches/*.patch; do patch -p1 --dry-run < "$p"; done
# 3. 六条补丁在 pristine 树上真实 apply 全 0
for p in archives/s/sysklogd/1.5.1/patches/*.patch; do patch -p1 < "$p"; done
# 4. 新增行零平台宏（R8/PF5）
grep -c "^+.*__OHOS__" archives/s/sysklogd/1.5.1/patches/*.patch
```

**结果**：`grep -rl` 零命中、`DRY_RC=0 × 6`、`RC=0 × 6`、`__OHOS__` 命中数
`0 × 6`。0001 尺寸 1282 → **1497 B**（更正后的注释变长），0002 尺寸 491 → **419 B**
（仅剥时间戳）。生成脚本留档：
`/storage/Users/currentUser/tmp/uc2/zhuli-10-sysklogd/regen_patches.py`（4339 B、
sha256 `347004a4c55f47e7912e79fb2b44e952897bd917346374de6835dce416bcabb1`），
本轮**未跑 `conan create`**（属静态整改），复现验证仅在
`/data/storage/el2/base/skl-regen-check` 与 `/data/storage/el2/base/skl-regen-apply`
两棵 tmpfs 树上做 patch dry-run/真实 apply。

### 11.3 两处旧结论的实证更正（`_syscall3` 首错形态 + hicmd 断言撤销）

- **§一 与 §定性(可回指证据) 里"编译期直接炸在 `_syscall3` 未声明"** —— **错**。
  真机 A/B 对照（§9.5）：回退 0001 后 `make klogd` 编译步 `CC_RC=0`、只有 5 条
  `-Wimplicit-int` 警告，clang 把未声明函数按隐式 int 降级；**真实首错在链接期**
  `ld.lld: error: undefined symbol: ksyslog` → `make: *** [Makefile:86: klogd] Error 1`。
  打回补丁 `MAKE_RC_WITH_PATCH=0`、`klogd` 43392 B。41 行机制探针
  （`syscall3-mechanism-probe.c`）A/B 双臂复现同形态。§一 与 §定性的相应句已按
  此改写，PR 正文「补丁原因 1」「已知限制」两条 bullet 也按同一事实与日志路径重写。
- **`archives/s/sysklogd/commands.json` 描述里的「（hicmd 真机验证通过）」**
  —— **删除**。`grep -rn hicmd archives/s/sysklogd/` 只命中该行本身，
  `$HOME/tmp/uc2/` 内无一属本包；有据的只有 §10.4 从包内路径直跑
  `sbin/syslogd -v` → `syslogd 1.5.1`、`RC=0`。改成有据口径 + klogd 侧的
  运行期限制与 SKIP 事实，任何「真机验证通过」的字样不再落在 `klogd` 上。

### 11.4 P1-2 `notes.md` 头部与状态块五处同源

被审正文第 3-6 行「仅前置调查完成，未做任何构建」+ 第 13-14 行「编译日期：未构建」
+「状态：未定（manifest `status: pending`）」与 §9 / §10.4 / §10.5 的实测
"built" 直接矛盾。整改：
- 顶部状态块整段改为「状态：**已构建、已验证**（`conan-verify` G0–G4 已跑、
  `conan create` 建包 `6b129b…239ce8a`、`status: built`；未 `upload`）」
  并列出本文件的时间线推进（前置调查 → 配方 → 构建闸口 → 正式 conan-verify/W3
  → 补丁 A/B 对照 → W4 整改同源更正）。
- 「编译环境」小节的 `编译日期: 未构建` / `状态: 未定（manifest status: pending）`
  改为 `2026-09-23` / `built`（口径引 §11.1 与 §10.5）。
- W0 preflight 行备注由「conanfile 未生成⇒依赖集空」改为交付态判据 +
  调查轮作旁证（对应 P3 关于 W0 时效的意见）。
- §一 头加 ⚠ 提示：本回合已按 §9.5 更正"编译失败"预测。
- K1/K2/K3/K4/K8 五行的状态从「未验证 / 已定性未报错」升到「已坐实 / 已规避」，
  Makefile 行号（19/85/124/136-139 → 20/78/129/141-142、844 → 845）在
  Makefile 行号实录块 + K3/K8 行 + 「上游测试清点」段 + §五 排除方案表 + §六
  R51 申报表内**一次改齐**，全归档同一事实只留一套行号。

**同源点核对（本文件内五处）**：

| # | 位置 | 措辞 | 值 |
|---|---|---|---|
| ① | 顶部状态块 | 已构建、已验证 | `status: built` |
| ② | §编译环境 · 编译日期 | 2026-09-23 | §10.5 `.ci-result.json` `timestamp: 2026-09-23T20:33:44` |
| ③ | §编译环境 · 状态 | `built`（G4 空过已声明） | §10.4 |
| ④ | §九 末「编译结束/最终状态」两行 | `编译结束: 2026-09-23 20:33 / 最终状态: built` | harness 自写、保留 |
| ⑤ | §10.5 W3 判据文件段 | `.ci-result.json exit_code:0 step:W3_local_ci` | 与 ②同源 |

外加 `manifest.yaml` 的 `status: built` + `build_date: "2026-09-23"`——与 ①–⑤
全部对齐。

### 11.5 P2-a `Makefile` 行号（一次 `grep -n` 复核）

被审正文 §"Makefile 关键行号实录"写 `78:all / 85:test / 124:install_exec /
136-139:obj-m/oops.ko/make -C / 19/28/34:CC/LDFLAGS/BINDIR`。
**本回合独立复核**（`/storage/Users/currentUser/tmp/uc2/sysklogd/sysklogd-1.5.1/Makefile`，
5020 B，mtime `2014-10-05 03:47`）：

```bash
$ grep -n "^all:\|^test:\|^install_exec:\|^oops\.ko:\|^CC=\|^SKFLAGS=\|^LDFLAGS=\|^INSTALL \|^BINDIR\|^syslog_tst:\|^tsyslogd:\|^tklogd:\|^ksym:\|^obj-m\|^syslogd:\|^klogd:\|make -C /lib/modules\|^check" Makefile
20:CC= gcc
23:SKFLAGS= $(RPM_OPT_FLAGS) -O3 -DSYSV -fomit-frame-pointer -Wall -fno-strength-reduce
27:LDFLAGS= -s
30:INSTALL = /usr/bin/install
33:BINDIR = $(prefix)/usr/sbin
76:all: syslogd klogd
78:test: syslog_tst ksym oops.ko tsyslogd
82:syslogd: syslogd.o pidfile.o
85:klogd: klogd.o syslog.o pidfile.o ksym.o ksym_mod.o
89:syslog_tst: syslog_tst.o
92:tsyslogd: syslogd.c version.h
95:tklogd: klogd.c syslog.c ksym.c ksym_mod.c version.h
116:ksym: ksym_test.o ksym_mod.o
129:install_exec: syslogd klogd
139:obj-m += oops.o
141:oops.ko: oops.c
142:	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
$ grep -n "^check" Makefile     # → 空，无 check 目标
```

整改块已按此更新，并在块底加注：**"本次调查初稿把 `all/test/install_exec/oops.ko`
记成 78/85/124/138，交付轮已按 `grep -n` 复核为 76/78/129/141-142；仓内其余引用
（`conandata.yml:16`、`conanfile.py:40`、`test_package/MANIFEST.yml:16/25/30`、
本文 §6）与实测值一致，本节以本节为准。"**

### 11.6 路径 B 判=create 的正文回填（`pr-body.md` 与本文档同源）

`pr-body.md` 第 11-14 行原写「路径 A／知识库扩展：无」，与 §9.5 的机制探针 +
已入库的 `DRAFT-sysklogd-1.5.1-syscalln-macro-missing-defers-to-link.{kv,md}`
（提交 `ebb091ec4e`）冲突。整改回合把 `pr-body.md` 改成 B 最小声明 3+2 行
（`适配路径` / `使用知识库` / `知识库扩展` / `关联 Issue`）；`关联 Issue` 号
**由主理另行 `$P issue` 创建后回填**（本回合不碰平台）。

### 11.7 本轮未处理项（交主理 / CIW）

以下 5 条属审计的 P2/P3 或非文档整改范围，本整改回合不动，如实登记：
1. **P2（`notes.md` §10.5 已披露）**：软件级 `archives/s/sysklogd/README.md` 缺、
   release/debug tar.gz、`reports/test-report.md`、`packaging/`、`.staging-verified`
   ⇒ 属 `finish` Step6/Step10 交付产物，主理 `$P run --skip-finish` 会补 tar 与
   `.staging-verified`。
2. **P2（工作区脏改）**：`archives/l/libXext/`（本机 HMDFS 显示成 `libxext/`）
   未提交的 README/manifest 与 `feedback/SKILL_FEEDBACK_d1f5850d.md`——
   任务书与交接均定性为"多树复现的环境噪声、不是本包产物"，
   **不提交、不还原、不删除**。
3. **P3 全部 7 条**：`configure_options` 的尖括号伪值、`test_package/MANIFEST.yml`
   description 内嵌 `#` 续行、`test_runner.sh` 未加 `set -euo pipefail` 且缺豁免理由、
   usage 断言标签宽于判据、上游测试分母口径三处不统一、`test_package/conanfile.py`
   三处设备绝对路径、W0 引用时效。**W0 时效**已在 §11.1/§11.4 顺手更正；
   其余属可选优化，不属 P1/P2 硬整改范围。
4. **G4 降级 PASS 的框架侧修复**：`scripts/ohc/conan_verify.py:737` 键结构假设过期
   （conan 2.29.1 已把二级键换成完整引用），**属框架改动，须单独 PR**（AGENTS §8）；
   本包仅登记缺陷 + 手工补验。
5. **P2 里的"重跑 `preflight_check.sh`"**：属静态整改外的独立取证动作，需 build slot；
   §11.1 已改用「§10.4 G1 + §10.5 conan-verify ✅」作交付态判据。

### 11.8 最终同源核对（本回合结束时的状态）

| 位置 | 值 |
|---|---|
| `manifest.yaml` `status` | `built` |
| `manifest.yaml` `build_date` | `2026-09-23` |
| `notes.md` 顶部 | 「已构建、已验证（未 upload）」 |
| `notes.md` §编译环境 | `编译日期: 2026-09-23 / 状态: built` |
| `notes.md` §九 末两行 | `编译结束: 2026-09-23 20:33 / 最终状态: built` |
| `notes.md` §10.5 W3 判据 | `.ci-result.json timestamp: 2026-09-23T20:33:44` |
| `notes.md` §11（本段） | 逐条整改 + 一手依据 |
| `commands.json` description | 撤 hicmd，改「真机实测 `syslogd -v` RC=0 / `klogd` 记 SKIP」 |
| `patches/0001` `---/+++` 行 | 裸路径、无伪时间戳；内部注释按 §9.5 事实更正 |
| `patches/0002` `---/+++` 行 | 裸路径、无伪时间戳；hunk 内容不变 |
| `patches/0003-0006` | 保持原样 |
| `knowledge/drafts/DRAFT-sysklogd-1.5.1-syscalln-macro-missing-defers-to-link.{md,kv}` | 已入库（`ebb091ec4e`） |
| `pr-body.md`（Windows 侧草稿，非仓内） | 路径 B（3+2 声明） + 首行提交 SHA 回填 |
---

**编译结束**: 2026-09-24 02:30
**最终状态**: built
**CIW-B2 rule4 整改（2026-09-27）**: 按审查「上游 5 用例 0 测」判决，五件上游测试件全部真实触碰，详证 reports/upstream-tests-realrun.log：syslog_tst 编译+执行 rc=0（设备无 /dev/log，工具无断言语义）；ksym 编译+执行完整跑完 8 处 System.map 搜索（OHOS 无符号表）；tsyslogd 编译+执行，配置解析与 restart 消息落配置文件实证（-p socket bind EACCES(13) 紧循环重试已定位，TESTING 变体测试沙箱内不可建 socket）；tklogd 链接失败 undefined symbol: ksyslog（HongMeng 无 Linux syslog(2)）；oops.ko 构建失败 /lib/modules/HongMeng 不存在。执行用测试副本 musl 兼容（sed 改名 dprintf/union wait + compat_shim.h，记录在证据日志，未触碰 PR 配方）。
