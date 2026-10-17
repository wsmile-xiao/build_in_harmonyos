# DRAFT — simulavr 1.0.0-git20160221.e53413b（OHOS aarch64）：上游 cgit 快照端点失效 → Debian pristine orig；静态链接下自注册设备被丢弃 → whole-archive；regress 套件 Python-2→3 移植

> **Contributor**: 适配 agent（simulavr 前置适配） | **Status**: DRAFT | **Updated**: 2026-09-27
> **Severity**: 🟡 medium | **Category**: source-provenance / autotools / python-port / OHOS

## 相关既有条目（同族差异化定位）

| 既有条目 | 覆盖内容 | 本案增量 |
|---|---|---|
| `DRAFT-nicovideo-dl-source-license-provenance` | Debian orig 作为可复现来源 + 许可证变体披露 | 本案是**上游归档端点整体失效**（cgit snapshot 返回 4xx/5xx）而非"上游无 tag"；并给出 savannah/cgit 快照端点的可用性判别 |
| `DRAFT-cppnumericalsolvers-1.0.0-no-tag-bazel-only-debian-orig` | 上游无 tag + 仅 Bazel → Debian orig | 本案上游**有 commit 但归档服务不可用**；且构建系统是 autotools（需 autoreconf 引导） |
| `E2175`（裸 `bind(...)` → `::bind(...)`） | musl/libc++ 严格性清单 | 本案的 `::bind` 命中**正是 E2175 第 5 条**，此处只作实证记录，不主张新知识 |
| `DRAFT-bitserializer-0.85.0-libcxx-transitive-include-string-view` | libc++/libcxx-ohos 裁剪传递包含 | 本案 `<map>`/`<stddef.h>` 缺包含是**同一机制的另一实例** |

## 触发（trigger）

在 OHOS/aarch64 上用 Conan 适配**只提供 git 仓、归档端点不可用**的历史库；或适配
**自带 Python 回归套件的老 autotools 项目**，需 `make check` 实跑上游测试（R51）。

## 现象与根因

### A. 指定 commit 无发行归档，cgit 快照端点失效

simulavr 目标提交 `e53413b230637b75e1cfa5c316e988480f5cea14`（2016-02-21）：

1. savannah 下载区 `download.savannah.nongnu.org/releases/simulavr/` 最新的
   `simulavr-1.0.0.tar.gz` 是 **2012 年 `release-1.0.0` tag** 的产物，不含 2016 修复；
2. cgit 快照端点 `git.savannah.nongnu.org/cgit/simulavr.git/snapshot/<ref>.tar.<ext>`
   在 2026-09-27 实测：`tar.gz`/`tar.bz2`/`xz` 返回 **502**、`zip` 返回 **400**，
   对 commit hash 与 tag 名均如此（服务端故障，非 ref 错误）。

→ 无法从上游取快照归档；退路是 **Debian pool 的 pristine `orig.tar.xz`**
（`simulavr_1.0.0+git20160221.e53413b.orig.tar.xz`，sha256 `6459b370…a38d`），
它是 Debian 打包的**上游原始**归档（平铺上游树，无 `debian/` 目录），
与其配套的 `*.debian.tar.xz` 未使用。

### B. 上游回归套件是 Python 2，Python 3 下无法解析

`regress/` 120 个 `.py` 在 Python 3 下 **85 个字节编译失败**（`print` 语句、
`except X, e`、`ConfigParser`、str/bytes 混用）。`make check` 调 `regress.py`
驱动刚构建出的 `src/simulavr`（`-g -G` gdb-server），故不移植则上游测试无法运行。

移植后仍有 1 类残留：`test_RET.py`/`test_RETI.py` 用 `(8*1024/2-1)` 作 `%x`
参数，Python 3 的 `/` 是真除法 → 生成 float → `TypeError: %x format: an integer
is required, not float`。**`//` 在 py2/py3 语义一致**，是最小修复。

### C. 静态链接下自注册设备被丢弃（→ automake convenience library）

simulavr 的 AVR 设备模型经 `AVR_REGISTER(name, class)` 宏在**静态初始化期自注册**
——每个设备 `.cpp` 里生成一个文件作用域的 registrar 对象（`maker_<name>`），其构造器
调用 `AvrFactory::reg(...)`。`AvrFactory::makeDevice("atmega128")` 查的是这张全局表，
而 `main` **从不直接引用**任何设备符号。

上游 `src/Makefile.am` 把 `libsim` 编成**共享库**（`libsim_la_LDFLAGS = -shared
-avoid-version -rpath $(libdir)`）交付，全部对象都在 `.so` 里，故上游从未暴露该问题
（Debian `readelf -d`：`NEEDED libsim.so` + `RUNPATH /usr/lib/simulavr`）。

OHOS 侧不能照搬共享库：musl 忽略 `DT_RUNPATH`，CI 的 L2 smoke test 直接执行
`bin/*` 且不设 `LD_LIBRARY_PATH`，共享 `libsim.so` 运行期找不到。于是要静态化，随即
踩到注册器被丢弃：

- 普通归档静态链接只拉取**被引用符号**所在对象 → 29 个 registrar 全丢，
  `simulavr -d atmega128` 报 `Invalid device specification`；
- **`-Wl,--whole-archive libsim.la` 无效**：libtool 会把 `--whole-archive` 与
  `.la` 输入重排，标志不落在归档两侧（实测构建出的 `simulavr` 含 0 个 `maker_` 符号）。

可靠解法是 automake 的 **convenience library**：把 `libsim` 从 `lib_LTLIBRARIES`
移到 `noinst_LTLIBRARIES`（去掉 `-shared -rpath`），并让 CLI 直接包含其对象——
`simulavr_LDADD = libsim.la` 之外，还需 `am_simulavr_OBJECTS += $(am_libsim_la_OBJECTS)`
（libtool 对 convenience 库会把全部对象并入程序，实测 `simulavr` 含 29 个 `maker_`）。

```
# src/Makefile.in（preconf 内，见下）
lib_LTLIBRARIES =
noinst_LTLIBRARIES = libsim.la
libsim_la_LDFLAGS = $(am__append_4)          # 去掉 -shared -avoid-version -rpath
am_simulavr_OBJECTS = cmd/main.$(OBJEXT) $(am_libsim_la_OBJECTS)
simulavr_LDADD = $(LIBZ_FLAGS) $(EXTRA_LIBS)
```

代价：包形态变为纯 CLI（`package_type = application`，只装 `bin/simulavr`）；
`libsim` 非 PIC 静态编入可执行文件即可。

### D. 构建主机无法运行 autotools → 提交 preconf/

原始 orig 树只带 autotools **输入**（`configure.ac`/`Makefile.am`/`m4/`），需
`./bootstrap` 生成 `configure`/`Makefile.in`/`config.guess`/`src/config.h.in` 等。
该 OHOS 设备（构建用户）跑不了 autoreconf：

- `autoreconf`/`autoconf`/`m4`/`perl` 在 `/data/service/hnp/bin`（可执行）但**不在 profile PATH**；
- `automake`/`aclocal`/`libtoolize` **设备上根本不存在**（`/data/service/hnp` 只有
  `autoconf.org`/`m4.org`/`perl.org`），`~/usr/local/bin` 与 conan 缓存里的副本是
  `750` 属主另一 uid，不可执行；
- HMDFS 挂载 `nosuid` + MAC，**拒绝 `execve` 本用户自建文件**（`chmod` 被钳制）；
  只有受保护的工具目录（hnp 755）可执行。同设备 `libhugetlbfs/2.24` shadow 以完全相同
  方式失败（`aclocal: Permission denied`）。

解法（同仓库 agg/libagg/afflib 的 `preconf/`/`generated/` 惯用法）：在 Debian 容器内
`autoreconf -fi` 生成全部构建系统文件，作为**文本提交**到 `preconf/`，配方 `source()`
用 `copy()` 覆盖到源码树。配方不再需要任何 autotools 工具链。preconf 内另含针对
HMDFS 的必要修正（`umask 077→027`、`AM_CXXFLAGS` 支持 out-of-tree、`check-versions.sh`
走 `$(SHELL)`、convenience library 化）。

### E. 其它必需适配

- **执行 configure 用 shell**：`Autotools.configure()` 硬编码 `exec ./configure`，在
  HMDFS 上 EACCES（126）。改用 `/system/bin/sh <configure> <args>`（同成功的
  `duff/0.5.2`）。`make` 也走 `$(SHELL) libtool`，一致。
- **`AC_CHECK_PROG(CXX_PROG, ${CXX}, …)` 误判**：Conan 把 `CXX` 设为绝对路径，而
  `AC_CHECK_PROG` 按 `$PATH` 逐项拼接查找，绝对路径永不命中 → 用
  `ac_cv_prog_CXX_PROG=yes`（及 `MAKEINFO_PROG`）覆盖缓存变量。
- **C++14**：`types.h` 的 `typedef unsigned char byte` 与 C++17 libc++ 的 `std::byte`
  在 `using namespace std` 下歧义；Debian 官方同样用 `-std=c++14`。
- **删除 `src/elfio/VERSION`**：该纯文本标记文件因 `-I<srcdir>/elfio` 遮蔽了 libc++
  的 `<version>` 头（大小写不敏感文件系统上 `VERSION`≡`version`），令 `<iostream>` 等
  全面崩溃（`no type named 'size_t' in namespace 'std'`）。同族先例：centerim 的
  `intl/version`。
- **regress/ py3 移植补全**：仅套用 Debian 补丁不够，`gdb_rsp.py` 还需
  `cksum()` 兼容 bytes、`array.fromstring→frombytes`(4)、`reply[:1]==b'…'`(2)；
  `regress.py.in` 的 `sys.write→sys.stderr.write`。否则 `make check` 运行时
  `TypeError: ord() expected string of length 1, but int found`。

### F. `make check` 的假绿陷阱

`regress/Makefile.am` 的 `regression` 规则是
`python3 ./regress.py 2> regress.err | tee regress.out`——**管道使 make 取 `tee` 的
退出码**。于是 `regress.py` 即使致命失败（如模拟器没启动），`make check` 仍返回 0。
必须读 `regress/regress.err` 与 `regress.out` 才能判断套件是否真的跑过；本案最后
以 `regress.out` 的 `Ran 14706 tests … 0 failing` 作为真实通过证据。

## 方案

1. **源码**：`conandata.yml` 固定 Debian pristine orig 的 HTTPS URL + sha256，
   按 PF7「官方托管例外」登记（PR 用 `--no-preflight` 并在正文说明）；归档是平铺
   树，`get(..., strip_root=False)`。
2. **autotools 引导**：源码树不含 `configure`/`config.guess`/`config.sub`/`ltmain.sh`
   → `build()` 跑 `autoreconf -fi`，`automake`/`libtool` 走 `tool_requires`；
   预置源码根 `install-sh` 规避 libtoolize aux-dir 误判（E514）。
3. **测试**：把 `regress/`（modules + test_opcodes + regress.py.in）移植到 Python 3
   （移植内容取自 Debian 打包补丁系列的 `regress/` 子集，另补 `8*1024//2` 整除修正），
   在 `build()` 中 `autotools.make(target="check")` 实跑。
4. 依赖类修复（`<map>`/`<stddef.h>`/`::bind`）分别落独立补丁；`::bind` 与
   libc++ 传递包含属已知机制，PR/notes 标注 `E2175` 与 bitserializer 条目。

## 适用边界 / 反例

- 适用：上游归档服务失效/无该 commit 归档但仍可从发行版 orig 取到原始树；
  老 autotools 项目自带 Python 2 回归套件需在 Python 3 环境实跑。
- 反例：上游 release tarball 可用时应优先用上游官方归档（PF7/R39 更稳）；
  若回归套件依赖 avr-gcc/iverilog/tcl 等本环境不具备的工具链，如实标注不可运行，
  不以"环境允许"掩盖（R51）。
- `modtest/` 下 2 个仍为 py2 的文件不被 `regress.py` 采集（需 avr-gcc），
  不影响 `make check`，无需强改。

## 实证

- 全量交叉编译（OHOS clang 15 / libc++ / musl）：`libsim_la_SOURCES` 全部 TU
  67/67 通过；`llvm-ar` 归档 `libsim.a`；`clang++` 链接真实消费者（`AvrFactory::
  makeDevice("atmega128")` / `SetClockFreq` / `Reset` / `GetDeviceSignature`）成功，
  产物 `ELF 64-bit LSB pie, ARM aarch64, interpreter /lib/ld-musl-aarch64.so.1`。
- regress 导入枚举：移植后 78/78 模块、**14706** 个测试用例、0 导入错误（原树 85/120 失败）。
- 真机 shadow CI（HarmonyOS PC aarch64，隔离 job）：**exit 0**，L0/L1/L2/L5 pass、
  L1e 破坏性反向验证通过；上游套件实际运行 **atmega128: 14706 ran / 13850 pass /
  0 fail / 856 skip；atmega2560: 14706 ran / 14706 pass / 0 fail**。
