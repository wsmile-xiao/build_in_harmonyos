# Dinotrace 9.4f 适配笔记（OHOS PC aarch64）

## 编译环境

- 构建系统: autotools（2019 年手写 `configure` + `Makefile.in`，**in-source 构建**）
- 编译日期: 2026-09-13
- 编译器: clang / clang++（OHOS SDK 26.0.0.18，`aarch64-linux-ohos`）
- Conan profile: `ci/conan/profiles/ohos-aarch64`（host 与 build 同 profile）
- 目标产物: `bin/dinotrace`（ELF aarch64，DT_NEEDED libXm.so.4/libXt.so.6/libX11.so.6）
- 状态: built

## 源码与来源核验（OBSERVED）

- 上游官方 FTP: `https://www.veripool.org/ftp/dinotrace-9.4f.tgz`（R39/PF7 clean，https 官方源）
- 大小 1,292,431 B。

**sha256 勘误（重要）**：任务书给的期望值 `a45b462da5797496d1d305b6f7953ee7572e0201d9e4a4678bfd458044762 0be`
（结尾 `...7620be`）**与官方文件不符**——最后一位十六进制有误。实测（本轮现场从官方 URL 重新下载）：

```bash
$ /usr/bin/curl -fsSL -o dinotrace-verify.tgz https://www.veripool.org/ftp/dinotrace-9.4f.tgz
$ sha256sum dinotrace-verify.tgz
a45b462da5797496d1d305b6f7953ee7572e0201d9e4a4678bfd4580447621be  dinotrace-verify.tgz
$ sha256sum "$HOME/tmp/dino/dinotrace-9.4f.tgz"      # 本机既有副本
a45b462da5797496d1d305b6f7953ee7572e0201d9e4a4678bfd4580447621be
```

两个独立副本 + 现场重下三次一致 → conandata.yml/manifest.yaml 采用实测值
`a45b462da5797496d1d305b6f7953ee7572e0201d9e4a4678bfd4580447621be`。
（conan 首次尝试用 `...7620be` 报 `sha256 hash failed ... Computed hash: ...447621be`，
证据见下方"遇到的问题 #2"。）

## R51 上游测试清点（census，raw commands + outputs）

在源码根 `dinotrace-9.4f/` 实测：

```bash
$ grep -nE "^(check|test):" Makefile.in
119:test: dinotrace_exe

$ grep -nE "^(check|test|install):" Makefile.in src/Makefile.in
Makefile.in:119:test: dinotrace_exe
Makefile.in:184:install: all info installdirs install-info

$ find . -iname "*test*"
# 无输出（0 个文件）

$ ls traces/
ascii.dino  ascii.tra  dinotrace.dino  tempest.bt.gz  tempest.dino  vcd.dino  vcd.vcd

$ find . -name Makefile.am | wc -l
0
$ find . -name Makefile.in | wc -l
2

$ make -n check
make: *** No rule to make target 'check'.  Stop.      # exit 2
```

**结论**：Dinotrace 9.4f **无正式测试套件**，**无 `check:` 目标**。上游只有 1 个测试相关目标
`test:`（`Makefile.in:119`，= `./dinotrace traces/ascii.tra`，需 X display）。`traces/` 仅样例波形，
非自动化断言。`Makefile.am` 数 = 0（本项目为手写 Makefile，非 automake）。

→ 计：上游自动化测试 0 项；上游可运行测试目标 1 个（`test:`，平台受限）。

### build() 对上游 target 的处置（不删、不伪造）

`build()` 末尾 `_run_upstream_tests()` 原样调用上游 `test:` 目标并捕获原始输出
（`timeout 60 make test`，DISPLAY 取消）。**为让二进制真正加载打包的 Motif/X11 链并进入 X 初始化路径**，
该步骤内 `export LD_LIBRARY_PATH=<所有依赖 lib 目录>`（否则动态链接器直接报
`Error loading shared library libXm.so.4` 而到不了 `XtOpenDisplay`）。实测原始输出（conan create 日志）：

```
dinotrace/9.4f: [upstream-test] ### upstream test census (dinotrace 9.4f) ###
dinotrace/9.4f: [upstream-test] 119:test: dinotrace_exe
dinotrace/9.4f: [upstream-test] ### make -n check ###
dinotrace/9.4f: [upstream-test] check-target: ABSENT (upstream ships no check: target)
dinotrace/9.4f: [upstream-test] ### upstream `make test` verbatim (test: dinotrace_exe) ###
dinotrace/9.4f: [upstream-test] ./dinotrace traces/ascii.tra
dinotrace/9.4f: [upstream-test] Can't open display ''
dinotrace/9.4f: [upstream-test] TEST_EXIT=0
```

即：上游 `test:` 目标被**原样执行**；其程序确实运行到 X 初始化，因本平台无 X server 打印
`Can't open display ''` 后 `exit(0)`（`src/dt_dispmgr.c:521-524`）。此即平台豁免，已同时声明于
`test_package/MANIFEST.yml`（`platform_exemption: true`）。**未删除该目标、未伪造通过。**

## 编译步骤（配方内部）

1. `source()`：`get(url, sha256, strip_root=True)`。
2. `generate()`：`AutotoolsToolchain`；`--x-includes=<libx11>/include`、`--x-libraries=<libx11>/lib`
   （满足 `AC_PATH_XTRA`/`AC_PATH_X`）；环境注入 `CC/LD/AR/RANLIB/STRIP/NM/PERL` +
   `CPPFLAGS`（所有依赖 include，R49 私有前缀）+ `LDFLAGS`（所有依赖 lib + `-rpath-link`）。
3. `build()`：`replace_in_file` 修 `configure`（`umask 077`→`022` E011、shebang→OHOS shell）与
   `Makefile.in`（`SHELL = /bin/sh`→OHOS shell，同时修 `install-sh`/`mkinstalldirs` shebang）；
   `configure`（`--prefix=/`）+ `make -j1`（in-source，生成 `obj_dir/dinotrace`→`./dinotrace`）；
   末尾运行上游 `test:` 目标（见上）。
4. `package()`：**确定性显式打包**（不再依赖 `make install`，详见下节"打包（package）"）——
   `copy()` 三件套：`bin/dinotrace`（build 目录）、`share/info/dinotrace.info`（source 目录）、
   `licenses/COPYING`；随后**校验**前二者均存在，缺失即 `raise ConanException`。`make install` 仅作
   **非权威证据步骤**（staging 到包外 `install-staging/`、非致命）。删除 `*.la`。

## 打包（package）：HMDFS 限制与确定性策略（OBSERVED）

`package()` 原先为 `self.run("make install DESTDIR=<pkg>", ignore_errors=True)`，在本 OHOS/HMDFS
机器上该命令**必然失败**（两个独立根因，均在保留构建目录
`/storage/Users/currentUser/.conan2/p/b/dinotadd98d04a2efa/b` 复现），且 `ignore_errors=True` 把失败
静默吞掉，仅靠 `if not os.path.isfile(bin_path)` 兜底侥幸得到正确包——**脆弱**：一旦 `make install`
半成功（如拷了二进制但漏了 info），兜底被跳过，包会**静默丢失** `share/info/dinotrace.info`。

**上游 install 规则集**（`Makefile.in`，行号与生成的 `b/Makefile` 一致）：

```make
all: dinotrace_exe info                                        # 117
dinotrace_exe dinotrace: obj_dir bin                           # 132
	(cp obj_dir/dinotrace ./dinotrace >/dev/null 2>&1\        # 135
	 || cp obj_dir/dinotrace.exe ./dinotrace.exe >/dev/null 2>&1)
installdirs:                                                   # 181
install: all info installdirs install-info                     # 184
install-info: info installdirs                                 # 195（recipe 在 196-198）
	for i in *.info*; do \
	  $(INSTALL_DATA) $$i $(DESTDIR)$(infodir)/$$i; \
	done
```
即上游 `install` **只**安装：程序 → `$(bindir)`、每个 `*.info*` → `$(infodir)`；**无** `share/dinotrace`
数据（`pkgdatadir` 仅为运行期 config 搜索路径，未随包发布）。此即本配方 `copy()` 镜像的集合。

**根因 1 — HMDFS 拒绝覆盖已存在的（可执行）文件**：`make install` 先触发 `all`→`dinotrace_exe`，
其 body `cp obj_dir/dinotrace ./dinotrace`（`Makefile:135`）的目标已由先前 `make` 生成，HMDFS 拒绝覆盖：

```
cp: /storage/Users/currentUser/.conan2/p/b/dinotadd98d04a2efa/b/dinotrace: Operation not permitted
make: *** [Makefile:135: dinotrace_exe] Error 1
```
先 `rm -f dinotrace dinotrace.exe` 可使该 `cp` 成功（本轮复现：删除目标后 cp 步不再报错）。

**根因 2 — HMDFS 忽略 chmod，`install-sh` 无法被 exec**：越过根因 1 后，上游下一步 `install-info`
用 `$(INSTALL)=./install-sh -c` 安装 info，而 `install-sh` 在本文件系统上无执行位：
```
/bin/sh ./mkinstalldirs .../install-staging//bin .../install-staging//share/info
/bin/sh: ./install-sh: can't execute: Permission denied
make: *** [Makefile:196: install-info] Error 126
```
（本轮现场 `cd <build-folder> && make install DESTDIR=<stage>` 复现，`MAKE_INSTALL_EXIT=2`。）

**选择的策略**：**保留**上游 `make install` 仅作**证据步骤**，但 (a) 先 `rm -f dinotrace dinotrace.exe`、
(b) `ignore_errors=True` 保持非致命、(c) `DESTDIR` 指向包**外**的 `install-staging/`，**绝不**让它产生
包；真正的包由 `copy()` **无条件显式**生成，再**校验** `bin/dinotrace` 与 `share/info/dinotrace.info`
均存在，缺失即 `raise ConanException`（`from conan.errors import ConanException`）并给出显式信息——
**不再有静默成功**。选"保留"而非"删除 `make install`"的原因：它让两个 HMDFS 限制在**每次构建日志**中
可复现（活证据），并验证我们镜像的安装集恰为上游 `install` 所装集合。`touch dinotrace.info/.txt/.pdf`
仍保留（使证据步骤的 `info` 前置为 no-op；`makeinfo`/`texi2pdf` 本平台无）；其 `ignore_errors=True`
**已移除**（两文件恒存在且可写，`touch` 不会失败）。

**本轮构建实据**（`conan create` 日志 `conan-create-rework.log`）：

```
dinotrace/9.4f: RUN: touch dinotrace.info dinotrace.txt dinotrace.pdf
dinotrace/9.4f: === upstream `make install` trace (non-authoritative) ===
dinotrace/9.4f: RUN: rm -f dinotrace dinotrace.exe && make install DESTDIR=.../b/install-staging
...
(cp obj_dir/dinotrace ./dinotrace ...)            # 现成功——因目标已 rm -f
...
/bin/sh: ./install-sh: can't execute: Permission denied
make: *** [Makefile:196: install-info] Error 126
dinotrace/9.4f: === end upstream `make install` trace ===
dinotrace/9.4f: package(): Packaged 2 files: dinotrace, COPYING
dinotrace/9.4f: package(): Packaged 1 '.info' file: dinotrace.info
```

## 源码修改（patches）

**无源码补丁**（`conandata.yml: patches: {}`）。所有平台处理均为环境/配置层：
configure `umask`/shebang、`Makefile.in` 的 `SHELL`、`--x-includes/--x-libraries`、`CPPFLAGS/LDFLAGS` 注入、
`touch` 文档时间戳。**未使用任何 `__OHOS__` 宏**（PF5 clean）。

## 依赖版本

- `motif/2.3.8`（`transitive_headers=True, transitive_libs=True`）— 提供 `libXm.so.4` + `Xm/*.h`
  （Motif 上游不存在，为本仓新适配依赖）。
- `xorgproto/2025.1`（`transitive_headers=True`）— `<X11/X.h>`/`<X11/Xfuncproto.h>`。
- 传递依赖（配方经 `self.dependencies.host` 注入其 include/lib）：`libx11/1.8.13`、`libxt/1.3.1`、
  `libxext/6.4.0.1`、`libsm/1.2.6`、`libice/1.1.2`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `KeyError: '9.4f'` in `source()` | 我最初按"版本字典"写 `self.conan_data["sources"][str(self.version)]`，但本项目 conandata 为扁平 `sources:`（同 x3270） | 改为 `dict(self.conan_data["sources"])` 并 pop 元数据键 |
| 2 | `sha256 hash failed ... Computed hash: ...447621be` | 任务书给的 sha256 末位有误（`...7620be`） | 现场重下官方 URL 实测 `...7621be`，更新 conandata/manifest（见上"勘误"） |
| 3 | `Cannot change permissions for .../motif.../s/bitmaps! Directory not empty` + 计划外的 motif 源码重建 | **并发协作者**正在跑 `conan create archives/m/motif/2.3.8`，其每次 re-export motif 产生无二进制的新 recipe revision；我的图解析到该 revision → 触发 motif 重建，与其源码目录清理竞争 | 等待并发 motif create 结束（其产物落盘后 motif 最新 revision 有二进制），再重跑；后续运行显示 `motif/2.3.8: Already installed`，不再重建 |
| 4 | 上游 `test:` 在 build 环境直接 `Error loading shared library libXm.so.4`（动态链接器失败，TEST_EXIT=2） | build() 的 `conanbuild` 环境无运行期库路径（`-rpath-link` 只用于链接期） | `_run_upstream_tests()` 内 `export LD_LIBRARY_PATH=<依赖 lib 目录>`，使二进制真正 exec 并到 `XtOpenDisplay`（→ `Can't open display ''`，TEST_EXIT=0） |

## 已知限制 / 禁用特性

1. **GUI 无法在本平台验证**：OHOS / 本机构无 X server、无 Wayland。所有到达 `XtOpenDisplay()`
   的路径必然失败（`src/dt_dispmgr.c` 打印 `Can't open display ''` 并 `exit(0)`）。
   因此**仅**能验证非 GUI 面（`--version`）与二进制可加载性；波形交互界面不可运行。
   已在 `test_package/MANIFEST.yml` 声明平台豁免。
2. 上游 `test:` 目标名义"通过"（TEST_EXIT=0）**仅因** dinotrace 在无 display 时 `exit(0)`；
   该目标**不构成实质断言**（无论是否成功打开 display 都返回 0）。真正验证靠 test_package（R34）。
3. **版本串含空 HOST（纯外观，非缺陷）**：`--version` 第 3 行为 `Configured <date> for `
   （结尾无主机名）——上游 `configure.ac` **显式注释掉了 `AC_CANONICAL_HOST()`**，`$host` 从未设置，
   故 `config.h` 中 `HOST=$host` 为空。此为上游行为、**纯外观、不影响功能**；`--version` 首行
   `Dinotrace 9.4f` 正常（test_package 断言此项）。
4. **`make install` 依赖 makeinfo**：上游 `install: all info installdirs install-info`，`info`
   会把 `dinotrace.texi` 生成 `.info/.txt/.pdf`。本平台无 `makeinfo`/`texi2pdf`，故 `package()`
   先 `touch` 上游自带的 `.info/.txt/.pdf` 使其新于 `.texi`，令 `info` 成为 no-op。
5. 安装内容仅 `bin/dinotrace` + `share/info/dinotrace.info` + `licenses/COPYING`：上游 `install`
   **不安装** `share/dinotrace` 数据（`pkgdatadir` 仅作运行期 config 搜索路径，未随包发布）；
   lisp 文件上游明确"not installed"。

## motif/2.3.8 依赖状态（残留风险，务必知悉）

- `motif/2.3.8` **已发布到制品仓**（2026-09-19，本机实测 `conan list "motif/*" -r=ohpcd` 可见，`conan install --requires=motif/2.3.8` 依赖图 11/11 解析通过）。
  本轮 `conan create` 因本地缓存命中而通过（`motif/2.3.8: Already installed`）。
- **CI 影响**：本包 PR 的 CI（`conan create --build=missing`）在**干净远端环境**上拉取
  `motif/2.3.8` 会失败（制品仓无该包）。**PR 会被 CI 阻塞，直到 motif/2.3.8 先 release 到制品仓。**
  处置：**不发布 motif、不 push、不开 PR**（遵任务约束；motif 由其自身 PR 合并/release）。
- 另注意：本轮期间**有并发协作者在本机反复 `conan create archives/m/motif/2.3.8`**，
  motif 的本地 recipe revision 被多次刷新；本包仅按 `motif/2.3.8`（不锁 revision）引用，CI 需以
  最终 release 的 motif 为准。

## 验证结果（OBSERVED）

```bash
cd <REPO>
conan create archives/d/dinotrace/9.4f \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# EXIT_CODE=0
# Created package revision aa9844b1d45c2a691beb49e9650c0283
# Full package reference: dinotrace/9.4f#e7efb6491ba6a47dc5bcac6a7fc13ef5:bafdbc981437e62c46ad05e5c176c9290e9da5a9#aa9844b1d45c2a691beb49e9650c0283
# test_package: assertions=6 failures=0
```

test_package 原始输出（节选）：

```
PASS: bin/dinotrace exists and is executable
--- captured: dinotrace --version (exit=0) ---
Dinotrace 9.4f
Distributed Sun Sep 13 04:06:22 2026
Configured Sun Sep 13 04:05:59 CST 2026 for
--- end ---
PASS: --version exits 0 and stdout contains 'Dinotrace 9.4f'
--- captured: llvm-readelf -d ... ---
  0x0000000000000001 (NEEDED)       Shared library: [libXm.so.4]
  0x0000000000000001 (NEEDED)       Shared library: [libXt.so.6]
  0x0000000000000001 (NEEDED)       Shared library: [libX11.so.6]
  0x0000000000000001 (NEEDED)       Shared library: [libSM.so.6]
  0x0000000000000001 (NEEDED)       Shared library: [libICE.so.6]
  0x0000000000000001 (NEEDED)       Shared library: [libc.so]
--- end ---
PASS: ELF DT_NEEDED libXm.so.4
PASS: ELF DT_NEEDED libXt.so.6
PASS: ELF DT_NEEDED libX11.so.6
--- captured: headless dinotrace (DISPLAY unset, timeout 30) exit=0 ---
Can't open display ''
--- end ---
PASS: headless dinotrace printed upstream display error and exited (0)
assertions=6 failures=0
```

日志：`$HOME/tmp/dinotrace-work/conan-create-rework.log`（`EXIT_CODE=0`）。

## 交付物（包内，实测）

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/dinotrace` | 346,560 B | ELF aarch64 可执行；sha256 `48ca2d4a…0f6c327`（随内嵌构建日期变化，非固定） |
| `share/info/dinotrace.info` | 118,559 B | Texinfo 手册（上游自带）；sha256 `e30aaa6b…189a8370` |
| `licenses/COPYING` | 35,147 B | GPL-3.0；sha256 `8ceb4b9e…eb65b903` |

## 复现命令

```bash
cd <REPO>
conan create archives/d/dinotrace/9.4f \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 注意事项

- 需 `perl`（`src/dist_date.pl`→`dist_date.h`、`src/dinodoc.pl`→`dinodoc.h`）。本机 perl 位于
  `/data/service/hnp/bin/perl`；配方经 `PERL` 环境变量显式指定。
- 必须 **in-source 构建**（`folders.build="."`）：顶层手写 Makefile 不支持 VPATH
  （`dinotrace_exe` 生成相对 `obj_dir` 并 `cp` 回 `./dinotrace`/`bin/dinotrace-$(HOST)`，
  `install-info` 对当前目录 `*.info*` 做 glob）。
---

**编译结束**: 2026-09-20 10:36
**最终状态**: built
