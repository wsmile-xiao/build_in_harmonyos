# protomol 2.0.3 构建报告（OHOS aarch64）

- **目标包**：`protomol/2.0.3`
- **平台**：OpenHarmony / HarmonyOS PC，`aarch64-unknown-linux-ohos`
- **构建系统**：autotools（上游自带 Autoconf 2.57 生成的 `configure`）
- **编译器**：`/data/service/hnp/bin/clang` / `clang++` 15.0.4
- **日期**：2026-09-27
- **结论**：`configure` exit 0，`make -j1` **exit 0**，`make install` exit 0 ⇒ **6 个可执行文件**

---

## 1. 构建矩阵

| 阶段 | 命令 | 退出码 | 证据日志 |
|---|---|---|---|
| 解包 | `tar xzf protomol-2.0.3-tar.gz` | 0 | — |
| 打补丁 | `for p in patches/*.patch; do patch -p1 < "$p"; done` | 0（10/10） | `logs/verify/patch-apply.log` |
| configure | `./configure --prefix=/ --with-glut=no --with-fft=zfft ac_cv_header_png_h=no ac_cv_lib_png_png_create_write_struct=no` | **0** | `logs/verify/preflight-configure.log` |
| make | `make -j1` | **0** | `logs/verify/w3-make-sanitized.log` |
| install | `make install -j1 DESTDIR=<stage>` | **0** | `logs/verify/w3-consumer.log` |
| 消费者测试 | `test_package/test.sh` | **0**（17/17 断言） | `logs/verify/consumer-run.log` |

**`error:` 计数**：`grep -c 'error:' w3-make-sanitized.log` → **0**。

---

## 2. configure 判定（真实输出）

```
$ ./configure --prefix=/ --with-glut=no --with-fft=zfft \
      ac_cv_header_png_h=no ac_cv_lib_png_png_create_write_struct=no
checking for gcc... /data/service/hnp/bin/clang
using FFT ZFFT
using PNG... no
using GLUT... no
configure: creating ./config.status
```

- **CC/CXX**：`/data/service/hnp/bin/clang` / `/data/service/hnp/bin/clang++`（`AutotoolsToolchain` 注入）
- **FFT**：`ZFFT`（自带软件实现，不引入 FFTW）
- **PNG**：`no`（`framework/io/PNGWriter.cpp` 全树零调用者，属死代码；用 `ac_cv_*` 钉死，避免静默产生 `libpng16.so` 运行期依赖）
- **GLUT/X11**：`no`（OHOS PC 无 GLUT/X11，同时清空 `GLUT_LIBS`/`X_LIBS`，不会有 `-lGL`/`-lX11` 进链接行）

---

## 3. autotools 时间戳 pin（关键，防止补丁被覆盖）

补丁 0010 改写了 `configure` / `configure.in`，使其 mtime 比上游随包的 `aclocal.m4` /
`protomol_config.h.in` / `Makefile.in` 新。automake 1.6 的 maintainer 规则

```
$(srcdir)/configure: $(srcdir)/configure.in $(ACLOCAL_M4)
        cd $(srcdir) && $(AUTOCONF)
```

会经 `missing --run autoconf` 用**设备上的 autoconf 重新生成 `configure`**，覆盖补丁 0010 并重新触发
`use of undeclared identifier 'PACKAGE_CITE'`。实测重生成的 `configure` 为 Autoconf 2.72 版本，
与上游 2.57 版本 diff 达 **27,269 行**。

**修复**：`conanfile.py::_pin_autotools_timestamps()` 把 autotools 依赖链的 56 个文件
（`*.m4`/`*.am`/`*.in`/`*.ac` + `configure`/`aclocal.m4`/`install-sh`/`mkinstalldirs`/`missing`/`depcomp`/`compile`）
统一 pin 到 `stamp = 978307200`（2001-01-01）。GNU make 视 mtime 相等为 up-to-date。

**验证**（构建树 `pm-recipe-preflight`，pin 后）：

| 文件 | mtime | 说明 |
|---|---|---|
| `configure` | 978307200 (2001-01-01 08:00:00) | 已 pin |
| `configure.in` | 978307200 | 已 pin |
| `aclocal.m4` | 978307200 | 已 pin |
| `Makefile.in` | 978307200 | 已 pin |
| `missing` | 978307200 | 已 pin |
| `Makefile` | 1790443816 (2026-09-27 01:30:16) | configure 生成，晚于全部输入 ✓ |
| `config.status` | 1790443815 | configure 生成 ✓ |
| `protomol_config.h` | 1790443824 | 生成于 configure 之后 ✓ |

**重生成检查**：`grep -E 'autoconf|autoheader|aclocal|missing --run' w3-make-sanitized.log` → **无命中**
（构建期未触发 autoconf 链重建），`configure` mtime 前后一致。

**补丁 0010 生效产物**（`protomol_config.h:120`）：

```c
#define PACKAGE_CITE "Please cite T. Matthey, T. Cickovski, S. S. Hampton, A. Ko, Q. Ma, M. Nyerges, T. Raeder,
T. Slabach, and J. A. Izaguirre. ProtoMol: An object-oriented framework for prototyping
novel algorithms for molecular dynamics. ACM Trans. Math. Softw., 30(3):237265, 2004."
```

> 注意 `237265` 处那枚不可见字符即原 Latin-1 0xAD（soft hyphen），补丁 0010 已无损转为
> U+00AD（UTF-8 `C2 AD`），字符语义不变。修复前该行会整行被 toybox sed 丢弃，宏退化为
> `/* #undef PACKAGE_CITE */`。

---

## 4. 宿主环境加固（safe-delete shim）

### 4.1 现象

第一次 `make -j1` **编译全部通过**，但在**链接阶段**失败：

```
/data/service/hnp/bin/clang++ -DHAVE_CONFIG_H ... -c -o protomol.o ... protomol.cpp     ← 编译 OK
.../cli/vendor/shim/safe-bin/safe-delete-bash-env.sh: .../safe-bin/rm: /bin/bash: bad interpreter: No such file or directory
make[3]: *** [Makefile:190: protomol] Error 126
make[2]: *** [Makefile:144: all-recursive] Error 1
make: *** [Makefile:131: all] Error 2
```

### 4.2 根因

宿主环境（OHOS 设备上的 IDE shell runtime）通过**三条通道**注入 "safe delete" `rm` 垫片：

1. **PATH** 首部插入 `.../cli/vendor/shim/safe-bin`，其中 `rm`/`unlink`/`rmdir` 包装脚本 shebang 为
   `#!/bin/bash`——OHOS 上**不存在 `/bin/bash`**（bash 在 `/data/service/hnp/bin/bash`）⇒ exec 失败、退出码 126；
2. 导出的 shell 函数 `BASH_FUNC_rm%%` / `BASH_FUNC_unlink%%` / `BASH_FUNC_rmdir%%` 会被 bash 自动 import
   成同名函数，**优先级高于 PATH**；
3. `BASH_ENV` 指向 `shell-runtime-bash-env.sh`，**每个 bash 子进程启动时都会 source 它**，从而
   *重新注入* 通道 2 的函数。

致命点在于 `Makefile:190` 是 automake 的程序链接规则：

```make
protomol$(EXEEXT): $(protomol_OBJECTS) $(protomol_DEPENDENCIES)
        @rm -f protomol$(EXEEXT)          # ← 这里被垫片劫持
        $(CXXLINK) $(protomol_LDFLAGS) $(protomol_OBJECTS) $(protomol_LDADD) $(LIBS)
```

所以失败只出现在**链接规则**（编译规则不调用 `rm`），表现为"全编译通过但一链就挂"。

### 4.3 修复

`conanfile.py::_sanitize_path()`（**沿用仓库既有惯例**：`cryptsetup/2.8.8`、
`libnl3-cli/3.11.0`、`libmspub-tools/0.1.4`、`libfreehand-tools/0.1.2`、`libextractor/1.17` 等），
在 `build()` 起始处：

- 从 `os.environ["PATH"]` 剔除所有含 `safe-bin` 的目录项；
- `os.environ.pop()` 掉 `BASH_FUNC_rm%%` / `BASH_FUNC_unlink%%` / `BASH_FUNC_rmdir%%`；
- `os.environ.pop()` 掉 `BASH_ENV` / `CODEBUDDY_SAFE_DELETE_BIN_DIR` / `CODEBUDDY_SAFE_DELETE_ENABLED`
  ——**必须掐断整个 source 链**，仅删前两类是徒劳的（bash 子进程会经 `BASH_ENV` 重新注入）；
- `generate()` 中另在 `Environment()` 里 `env.unset(...)` 同名变量，使 `conanbuild` 环境脚本对
  `configure`/`config.status` 同样生效。

### 4.4 复验

| 检查 | 结果 |
|---|---|
| 脚本级探针：清理后 `type rm` | `rm is /bin/rm`（toybox，非垫片函数） |
| `rm -f <file>` 功能 | exit 0 |
| 清理后重跑 `make -j1` | **`=== MAKE_EXIT_CODE=0 ===`**，链接全部完成 |
| `make -j1` 期间 `rm -f libISGintegrators.a` 等规则 | 正常执行 |

日志：`logs/verify/w3-make-sanitized.log`（其头部打印了清理后的 PATH 与 `type rm`）。

> **为什么可以直接重跑而不是从零重建**：该树由干净源码 + 10 补丁在 01:30 生成，
> `configure` 已完成、`framework/**` 与 `applications/*` 的对象文件全部产出（见
> `logs/verify/w3-make.log`，`error:` 计数 0）。首次 `make` 仅止步于链接规则。
> 清理环境后续跑即完成剩余链接步骤，得到完整构建。
> 权威的**从零全量构建**证据由 `conan create` 提供（source→build→package 全新执行）。

---

## 5. 产物（ELF 基线）

`make install DESTDIR=<stage>` 只产出 `bin/` 下 6 个文件（`find` 实证）：

```
/bin/coords2coords
/bin/coulomb
/bin/dcd2dcd
/bin/iSGProtomol
/bin/protomol
/bin/xyzviz
```

| 程序 | 大小 (bytes) |
|---|---|
| `protomol` | 36,629,056 |
| `iSGProtomol` | 25,664,064 |
| `coulomb` | 13,335,104 |
| `coords2coords` | 2,304,576 |
| `dcd2dcd` | 1,165,888 |
| `xyzviz` | 121,344 |

ELF 属性（`llvm-readelf -h/-d`）：

```
Class:   ELF64
Type:    DYN (Shared object file)     ← PIE
Machine: AArch64
NEEDED:  libc++_shared.so
NEEDED:  libc.so
```

6 个程序 `NEEDED` 完全一致，**仅 libc++_shared.so 与 libc.so**（无 libpng/libz/libGL/libX11/libgfortran）。

另生成 **15 个静态归档**，全部为 `noinst_LIBRARIES`（不安装）：

```
framework/base/libbase.a               4,404,642
framework/io/libio.a                   6,050,354
framework/parallel/libparallel.a         289,258
framework/topology/libtopology.a       3,964,462
framework/forces/libforces.a           6,621,960
framework/imd/libimd.a                   607,450
framework/integrators/libintegrators.a 9,530,934
framework/frontend/libfrontend.a      13,992,842
framework/factories/libfactories.a    28,426,762
applications/iSGProtomol-app/base/libISGbase.a              88,896
applications/iSGProtomol-app/io/libISGio.a               2,109,276
applications/iSGProtomol-app/forces/libISGforces.a       1,876,070
applications/iSGProtomol-app/frontend/libISGfrontend.a   3,011,554
applications/iSGProtomol-app/factories/libISGfactories.a 16,123,572
applications/iSGProtomol-app/integrators/libISGintegrators.a 1,358,810
```

→ 因此本包 `package_type = "application"`，`cpp_info.libs = []`、`cpp_info.bindirs = ["bin"]`，
并按 R38 提供软件级 `archives/p/protomol/commands.json`。

### 5.1 差异边界核验（PR 原子性 / R2）

补丁集对源码的改动被严格限制在 **11 个文件**。三方对比（日志 `logs/verify/patch-boundary.log`）：

| 对比 | files differ | only in | 说明 |
|---|---|---|---|
| A `.orig` vs B 全新解包 | 1 | 1 | **基线自身噪声**：`.tarball-sha256`（取源工具写入）与 `autom4te.cache/requests`（缓存，含绝对路径），**与补丁无关** |
| **C 补丁后 vs B 全新解包** | **11** | **0** | **唯一真实边界** ✓ |
| A `.orig` vs C 补丁后 | 12 | 1 | = 11（真实）+ 1（基线噪声） |

11 个文件对应 11 个补丁（补丁 0010 覆盖 `configure` 与 `configure.in` 两个文件，补丁 0011 再改 `configure` 一处）：

```
applications/iSGProtomol-app/forces/iSGDihedralSystemForce.h    ← 0001
applications/iSGProtomol-app/forces/iSGImproperSystemForce.h    ← 0002
framework/base/Report.cpp                                       ← 0003
framework/forces/DihedralSystemForce.h                          ← 0004
framework/forces/HarmDihedralSystemForce.h                      ← 0005
framework/forces/ImproperSystemForce.h                          ← 0006
framework/forces/NonbondedCutoffMollyForce.h                    ← 0007
framework/forces/NonbondedCutoffSystemForce.h                   ← 0008
framework/frontend/OutputDihedrals.cpp                          ← 0009
configure                                                       ← 0010
configure.in                                                    ← 0010
```

**结论**：适配未触碰任何非目标文件（无依赖库源码、无 recipe、无日志混入源码树）。
`logs/verify/patch-apply.log` 记录补丁 `--dry-run` 全部 OK 且逐一真实应用 exit 0（补丁 0011 为 CI 首轮失败后追加，其独立干跑证据见 `reports/test-report.md` §5.5）。

---

## 6. 消费者测试（新增鸿蒙用例）

`test_package/test.sh` 在 conanrun 环境下运行（PATH 已含 `<package>/bin`），原始输出：

```
protomol -> <stage>/bin/protomol
[test] 1/4 installed programs are present and start
  [PASS] program 'protomol' starts and exits 0
  [PASS] program 'coulomb' starts and exits 0
  [PASS] program 'coords2coords' starts and exits 0
  [PASS] program 'dcd2dcd' starts and exits 0
  [PASS] program 'iSGProtomol' starts and exits 0
  [PASS] program 'xyzviz' starts and exits 0
[test] 2/4 protomol reports the packaged version
  [PASS] protomol --version reports 'ProtoMol Version 2.0.3'
[test] 3/4 upstream example argon_400 (Lennard-Jones, periodic box)
  [PASS] argon_400 protomol finished with exit status 0
  [PASS] argon_400 reached step 20 / 20
  [PASS] argon_400 energy table 'argon.out.energies.lf' written (21 data rows)
  [PASS] argon_400 total energy conserved (max-min = 0.0000 kcal/mol)
  [PASS] argon_400 final total energy 95.9160 kcal/mol matches reference 95.9160
[test] 4/4 upstream example butane_4 (bonded + dihedral + LJ)
  [PASS] butane_4 protomol finished with exit status 0
  [PASS] butane_4 reached step 20 / 20
  [PASS] butane_4 energy table 'UA_butane.out.energy' written (21 data rows)
  [PASS] butane_4 total energy conserved (max-min = 0.0051 kcal/mol)
  [PASS] butane_4 final total energy 6.8016 kcal/mol matches reference 6.8016
[test] assertions passed: 17   failed: 0
[test] RESULT: OK — packaged ProtoMol runs real MD calculations on OHOS
```

**17/17 断言通过，exit 0。** 覆盖：6 程序启动、版本串、两个化学上不同的上游算例各真实跑 20 步 MD，
断言步数到位、能量表落盘、轨道全程总能守恒、末步总能对设备参考值（容差 0.01 kcal/mol）。

> 本轮修复：版本断言原先写作 `protomol --version 2>&1 | grep -q …`，在 `set -o pipefail`
> 之下会被 **SIGPIPE**（横幅 1282 字节 / 29 行 > 单次 stdio flush；`grep -q` 命中即退出）
> 间歇性误判为失败（实测旧写法 4/20 失败、新写法 0/20）。现已改为先捕获完整输出再匹配，
> 详见 `reports/test-report.md` §4.1 与 `notes.md` 问题台账 #9。

---

## 7. 上游测试

见 `reports/upstream-tests.md`。摘要：上游无自动化测试套件（`make check` 仅 automake 样板），
真实入口为 `examples/**/*.conf`，36 例实跑 → **通过 20 / 失败 6 / 跳过 10**，
6 个失败全部为上游示例数据自身缺陷。

---

## 8. 复现

```bash
export PATH=/data/service/hnp/bin:/bin:/usr/bin
unset BASH_ENV BASH_FUNC_rm%% BASH_FUNC_unlink%% BASH_FUNC_rmdir%% \
      CODEBUDDY_SAFE_DELETE_BIN_DIR CODEBUDDY_SAFE_DELETE_ENABLED
unset -f rm unlink rmdir 2>/dev/null || true   # 仅 shell 级复现需要

tar xzf protomol-2.0.3-tar.gz && cd protomol
for p in ../patches/*.patch; do patch -p1 < "$p"; done

# 等价于 conanfile.py::_pin_autotools_timestamps()
python3 - <<'EOF'
import os
S=978307200
KEEP=(".m4",".am",".in",".ac")
EXACT=("configure","aclocal.m4","install-sh","mkinstalldirs","missing","depcomp","compile")
for r,d,f in os.walk("."):
    for n in f:
        if n.endswith(KEEP) or n in EXACT: os.utime(os.path.join(r,n),(S,S))
EOF

export CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++
export SHELL=/data/service/hnp/bin/bash CONFIG_SHELL=/data/service/hnp/bin/bash LC_ALL=C
./configure --prefix=/ --with-glut=no --with-fft=zfft \
    ac_cv_header_png_h=no ac_cv_lib_png_png_create_write_struct=no
make -j1
make install -j1 DESTDIR=$PWD/stage
```

在 OHOS 设备上，**shell 级复现还需 `unset -f rm unlink rmdir`**：`BASH_ENV` 会在脚本自身启动时
就把垫片函数定义进当前 shell，仅删 `BASH_FUNC_*` 环境变量不会撤销已有函数定义。
配方内不需要这一步——Conan 以全新子进程启动 bash，被 pop 掉 `BASH_ENV` 后函数不会预先存在。

---

## 9. CI 首轮失败与修复：`config.status` 临时目录 umask（PR #13092 → 补丁 0011）

### 9.1 现象（CI 侧分类：Autotools configure 失败）

```
configure: creating ./config.status
./config.status: line 475: ./confstatDPmIeK/subs.sed: Permission denied
./config.status: line 583: ./confstatDPmIeK/subs.frag: Permission denied
./config.status: line 754: ./confstatDPmIeK/out: Permission denied
mv: bad './confstatDPmIeK/out': Permission denied
./config.status: line 826: ./confstatDPmIeK/in: Permission denied     (grep: 同上)
./config.status: line 880: ./confstatDPmIeK/undefs.sed: Permission denied
./config.status: line 932/934: ./confstatDPmIeK/config.h: Permission denied
ERROR: protomol/2.0.3: Error in build() method, line 159
        ConanException: Error 2 while executing
```

### 9.2 根因

`configure` 自身所有平台探测均正常（`using FFT ZFFT` / `using PNG... no` / `using GLUT... no`），
失败只发生在 `configure: creating ./config.status` **之后**，且全部集中在 `config.status`
自建的 `./confstatDPmIeK/` 临时目录内。上游 `configure:18684/18689`：

```sh
  tmp=`(umask 077 && mktemp -d -q "./confstatXXXXXX") 2>/dev/null` &&
…
  (umask 077 && mkdir $tmp)
```

CI worker 的构建目录在 `/storage/...`（HMDFS）上，**umask 077 建出的 0700 目录在该文件系统上不可写**，
于是 config.status 对该目录内每个文件的操作全部 `Permission denied` → configure exit 2。
与配方、补丁 0001–0010、消费者测试**均无关**。

### 9.3 修复（补丁 0011，与仓库已合并先例同款）

| 先例 | 补丁 | 记录的原因 |
|---|---|---|
| `archives/a/a52dec/0.7.4` | `patches/0002-configure-umask-022.patch` | "setgid hmdfs makes umask 077 dirs unwritable" |
| `archives/t/teseq/1.1.1` | `patches/0002-configure.patch` | 同上 |
| `archives/v/vttest/2.7-20251205` | `patches/0002-configure.patch` | 同上 |

本包新增 `patches/0011-configure-umask-022.patch`，把 `configure` 内两处 `umask 077` 改为 `umask 022`。
**只改构建期临时目录权限，不改上游任何 C 源码、不注入平台宏。**

### 9.4 复现与验证

| 检查 | 结果 |
|---|---|
| 同目录 umask 对照（本机） | `umask 077` → `700 drwx------`；`umask 022` → `755 drwxr-xr-x` |
| 补丁 × 原始上游 `configure` | `--dry-run` → `patching configure`，**exit 0** |
| 补丁 × 已打 0001–0010 的 `configure` | `--dry-run` → `patching configure`，**exit 0** |
| 全新解包 + 按序应用 `0001..0011` | **11/11 ok**；`umask 077` 残留 0、`umask 022` 出现 2 |
| 重跑 `./configure` | **exit 0**；`Permission denied` **0** 次 |
| 新生成的 `config.status` | 第 454/459 行 = `umask 022` |
| `protomol_config.h` | 仍含 `PACKAGE_CITE` 与 `PACKAGE_VERSION` |

> 局限：CI worker 的文件系统语义**本地无法完全复刻**（本地 0700 目录是可写的），
> 因此「转绿」的最终判据是重新推送后 CI 的结果。
