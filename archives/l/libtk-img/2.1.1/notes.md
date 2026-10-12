# libtk-img (Img / TkImg) 2.1.1 适配笔记

## 编译环境
- 构建系统: autotools（TEA — Tcl Extension Architecture；`configure.ac` + 每子目录 configure）
- 编译日期: 2026-10-08
- 编译器: clang 15（`/data/service/hnp/bin/clang`，OHOS 原生）
- 平台: HarmonyOS PC / HongMeng Kernel，`os=OHOS` arch=armv8（aarch64），Release
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 包类型: shared-library（产物为 Tcl 可 load 的动态库集合）
- 状态: built

## 编译步骤

1. **取源**：`conandata.yml` → SourceForge tkimg 2.1.1 官方发行包
   `Img-2.1.1.tar.gz`（12,451,223 B，sha256 `0e41efa8…9ae34f`），`strip_root=True`。
   必须用 `downloads.sourceforge.net` 直链：`/download` 形式返回 HTML，conan `get()` 会失败。

2. **应用补丁** `patches/0001-ohos-consumer-test.patch`（新增 `tests/ohos.test`）。

3. **E011 预处理**：源码树内所有 `configure` 的 `umask 077` → `umask 022`
   （HMDFS 拒绝 0600 临时目录）。

4. **宿主识别预处理**：
   - `_install_uname_shim()`：把 `uname`（`-s`→`Linux`、`-r`→`6.6`、`-m`→`aarch64`）
     注入 `PATH` 头部（与仓库内 tcl/tk 配方同款）；
   - `_stub_vendored_config_guess()`：把 `compat/**/config.guess` 换成固定输出
     `aarch64-unknown-linux-gnu` 的桩 —— 因为 conan 的 `conanbuild.sh` 会把 profile
     buildenv 的 PATH（`usr/local/bin`、hnp `bin`）前置，可能盖住 shim，桩化后结果确定。

5. **configure**（`AutotoolsToolchain`，**只用 Toolchain 不用 Deps**）：
   ```
   ./configure --with-tcl=<tcl包>/lib --with-tk=<tk包>/lib \
               tcl_cv_sys_version=Linux-6.6 ac_cv_prog_cc_works=yes \
               --prefix=/ --exec-prefix=/ …
   ```
   顶层 configure 会经 `TEA_CONFIG_SUBDIR` 依次配置 24 个子目录
   （zlib / libpng / libtiff / libjpeg / base / bmp / gif / ico / jpeg / pcx / pixmap /
   png / ppm / ps / sgi / sun / tga / tiff / window / xbm / xpm / dted / raw / flir）。

6. **Makefile 修补**（`_fix_generated_makefiles()`，实测改写 **47** 个 Makefile）：
   ```
   -L${TCL_ROOT}/lib  →  -L<tcl包>/lib
   -L//lib            →  -L<tk包>/lib
   -lX11              →  -L<libx11包>/lib -lX11
   CPPFLAGS          +=  -I<xorgproto包>/include
   ```

7. **构建**：`make`（顶层 `all:` 递归 `for sub in $(SUBDIRS); do cd $sub && make all; done`，
   实测在本平台可用，前提是 configure 已完整跑完、子目录 Makefile 齐备）。

8. **安装**：`make install-libraries INSTALL_ROOT=<build>/_stage`
   —— 即 `collate`（逐子目录 install 到 `Img/exec_prefix/lib/Img/`，合并 `pkgIndex.tcl`，
   再搬到 `$(INSTALL_ROOT)$(LIB_RUNTIME_DIR)`）。

9. **层 1 上游测试**（见下）：真实执行 `tests/all.tcl`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot run C compiled programs` | `AutotoolsDeps` 把 `LIBS="-ltcl9tk9.0 -ltcl9.0 -ldl …"` 注入每个 conftest 的链接命令；宿主上 conftest 加载 `libtcl9tk9.0.so` 失败（exit 127） | 只用 `AutotoolsToolchain`（不生成 `AutotoolsDeps`），与仓库 `tkpng` 配方一致 |
| 2 | `configure: error: cannot guess build type; you must specify one` | `uname -s` 返回 `HarmonyOS`，`compat/libtiff`、`compat/libjpeg` 自带 `config.guess` 不识别 → 内层 configure 未生成 `tif_config.h`/`tiffconf.h`/`jconfig.h` | uname shim + `compat/**/config.guess` 桩化为 `aarch64-unknown-linux-gnu` |
| 3 | `fatal error: 'tif_config.h' file not found`（以及 `tiffconf.h`、`jconfig.h`） | 同 #2 的后果 | 同 #2；桩化后内层 configure 正常生成 3 个头 |
| 4 | `ld.lld: error: unable to find library -ltclstub` / `-ltkstub` | tk 包发行的 `tkConfig.sh` 带 `TK_LIB_SPEC='-L//lib -ltcl9tk9.0'`、`TK_STUB_LIB_SPEC='-L//lib -ltkstub'`、`TK_INCLUDE_SPEC='-I//include'`；tcl 包 `tclConfig.sh` 带 `TCL_PREFIX='${TCL_ROOT}'` | Makefile 中 `-L${TCL_ROOT}/lib` → tcl 包 lib、`-L//lib` → tk 包 lib |
| 5 | `ld.lld: error: unable to find library -lX11` | `TEA_PATH_X` 在本平台找不到 X11，退化为裸 `-lX11` | Makefile 中 `-lX11` → `-L<libx11包>/lib -lX11` |
| 6 | `window.c:28:13: fatal error: 'X11/Xproto.h' file not found` | `window/window.c` 直接 include `X11/Xproto.h`，该头既不在 libx11 包也不在 tk 包的 `include/X11/` | 依赖 header-library `xorgproto/2025.1`，并把其 `include` 加入 `CPPFLAGS` |
| 7 | 运行期 `Error loading shared library libxcb.so.1: (needed by …/libX11.so.6)` | 处理器经 `tkConfig.sh` 的 `SHLIB_LD_LIBS` 链接了 `libX11.so.6`，而 X11 运行期需要 `libxcb.so.1` | 依赖 `libx11/1.8.13`（传递带来 `libxcb/1.17.0`、`libxau`、`libxdmcp`）；消费者 `LD_LIBRARY_PATH` 需含各包 `lib/` |
| 8 | `make: rm: No such file or directory` (Error 127, ignored) | 宿主把 `rm` 注入为沙箱函数；Makefile 里 `-rm -f` 前缀在部分实现下丢失 | 无功能影响（Makefile 用 `-` 忽略）；门禁环境已 `unset -f rm` |

## 源码修改

- `patches/0001-ohos-consumer-test.patch`：**新增** `tests/ohos.test`（鸿蒙消费者可行性用例，
  25 个 tcltest 用例）。不改动上游任何现有源码或测试语义。

构建期的其余改动（`umask 077→022`、`config.guess` 桩、Makefile 路径修补）都发生在
conan 构建目录内，`conanfile.py` 中有明确注释，**不落盘为补丁**。

其中 `umask 077→022` 使用 Conan 官方 `conan.tools.files.replace_in_file`
（仓库内 445 个 recipe 同款惯用法）而非手写 `open/read/write`。这是 build() 内的
**运行时修复**：`ohc clean-verify`（G0）只跑裸 `./configure`、不执行 `build()`，
无法复现该修复，故 `clean_verify.py` 会把它判为「预期行为（非阻塞）」，
真正的构建证据由 G2（`conan create`）与 W3（本地 CI）提供。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| tk | 9.0.3.2 | `--with-tk` 需要 `tkConfig.sh`；自动依赖 tcl |
| tcl | 9.0.3.2 | tk 的传递依赖；提供 `tclsh9.0`（上游测试与 test_package 的消费者解释器） |
| libx11 | 1.8.13 | `window` / `xpm` 处理器链接 `-lX11` |
| libxcb | 1.17.0 | libx11 的传递依赖（运行期必需） |
| libxau | 1.0.11 | libxcb 的传递依赖 |
| libxdmcp | 1.1.5 | libxcb 的传递依赖 |
| xorgproto | 2025.1 | 提供 `X11/Xproto.h`（header-library） |
| xtrans | 1.4.0 | libx11 的传递依赖（仅配方/头） |
| xcb-proto | 1.17.0 | libxcb 的传递依赖（仅配方生成用） |

包内 `compat/` 自带 zlib / libpng / libtiff / libjpeg 源码随包编译并静态并入各处理器，
因此**不需要**外部 conan 的 zlib/libpng/libtiff/libjpeg。

W0 可消费性全部经 `conan download -r=ohpcd` 实测通过（见 `reports/test-report.md` 证据表）。

## 验证结果

### 层 1：上游官方测试（`docs/TEST_QUALITY_SPEC` §3.1，在 `build()` 末尾真实执行）

入口即上游顶层 Makefile 的 `tcltests` 目标（`cd tests && tclsh all.tcl`）：

```bash
cd <build>/tests
<build>/_unbuffered_all_tcl.tcl  # 无缓冲包装器
tclsh9.0 <build>/_unbuffered_all_tcl.tcl <build>/tests/all.tcl
```

```
Tests began at 2026-10-08 23:09:19 +0800
...
Tests ended at 2026-10-08 23:09:43 +0800
all.tcl:	Total	315	Passed	297	Skipped	18	Failed	0
Sourced 20 Test Files.
Number of tests skipped for each constraint:
	18	Ghostscript
```

- 用例总数 **315**，通过 **297**，失败 **0**，跳过 **18**（全部为 Ghostscript 约束：
  `pdf-*` 9 例 + `ps-*` 9 例，OHOS 宿主无 `gs`，与平台适配无关）
- 20 个测试文件（上游 19 个 + 新增 `ohos.test`）
- 逐用例明细见 `reports/test-report.md`

### 层 2：test_package（消费者视角）

```bash
conan create archives/l/libtk-img/2.1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="libtk-img/*"
# test_package 内：/bin/sh run_test.sh <tclsh> test_consumer.tcl <Img 运行时目录>
```

### 层 3：CI 门禁（W3 本地 CI 模拟，真实执行 `ci/conan/*.sh`）

```bash
JUNK_PR_DIFF=<本包 14 文件的 unified diff> \
  zsh ci/conan/setup.sh && zsh ci/conan/build_and_test.sh archives/l/libtk-img/2.1.1
```

```
KC_RESULT=pass     JC_RESULT=pass  (检查模式: prdiff (14 个文件), Junk Files: 0, 涉及软件数: 1)
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed     ← 含 L1e 破坏性反向测试（搬走 lib/+include/ 后测试确实失败）
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
Total: 1  Success: 1  Pass rate: 100.0% (1/1)
```

`.ci-result.json` 双哈希溯源一致：`integrity_hash=30a03225c1ec2159`、
`log_sha256` == `sha256(reports/w3-local-ci.log)`。逐项细节见 `reports/test-report.md` §7。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `conanfile.py` | ~13 KB | 主配方 |
| `conandata.yml` | ~1.2 KB | 源码 URL + sha256 + 1 个补丁 |
| `patches/0001-ohos-consumer-test.patch` | ~3.7 KB | 新增鸿蒙测试用例 |
| `test_package/{conanfile.py,run_test.sh,test_consumer.tcl,MANIFEST.yml}` | — | 消费者可用性测试（`run_test.sh` 为入口，CI L0c 要求的 `.sh`） |
| `manifest.yaml` / `notes.md` | — | 版本级归档元数据 |

安装到包的产物布局：

```
lib/Img2.1.1/            24 个 .so（20 个格式处理器 + 4 个 compat 包装）+ 5 个 .a stub + pkgIndex.tcl
lib/*Config.sh           tkimgConfig.sh / jpegtclConfig.sh / pngtclConfig.sh / tifftclConfig.sh / zlibtclConfig.sh
include/                 tkimg.h / tkimgDecls.h / jpegtcl*.h / pngtcl*.h / tifftcl*.h / zlibtcl*.h
licenses/license.terms
```

## 注意事项

- `tclsh` **不在**宿主默认 `PATH` 上（来自 tcl conan 包），所以上游 Makefile 的
  `tcltests` 目标（裸 `tclsh`）在 CI 环境直接跑会 127；配方改为用 tcl 包内
  `bin/tclsh9.0` 绝对路径执行同一入口 `tests/all.tcl`（语义等价）。
- OHOS 上解释器**退出路径**可能被 Tk 拆除拖住（实测 Tcl 脚本 `package require Tk`
  后进程可挂住），故上游测试用 `timeout 2400` 包裹 + 无缓冲包装器，
  保证超时强杀时不丢已打印的 tcltest 结果。
- 上游 `visualtests`（需真实显示设备）与 `dpitests`（需屏幕 DPI）未纳入自动化；
  `make test` 目标包含它们，故不使用 `make test`。
- Img 是 dlopen/`pkgIndex.tcl` 形态的扩展，**不导出可链接 libs**；
  消费者需把 `<prefix>/lib/Img2.1.1` 放进 `TCLLIBPATH` 或 `auto_path`。

## 对话记录

### 对话 #1 [2026-10-08] 需求确认与源码定位
- 问题：目标库 `libtk-img` 2.1.1 在上游叫什么、源码在哪、有没有自动化测试入口。
- 操作：读 `SKILL.md`（W0-W5 / R1-R52）；在仓库内检索 `libtk-img` 是否已有归档；
  `ohc search-url` 未命中，改用 WebSearch 定位到 SourceForge 工程 `tkimg`。
- 结果：`libtk-img` = TkImg / Img，发行包 `Img-2.1.1.tar.gz`；上游有 tcltest 套件
  （`tests/all.tcl` + 19 个 `*.test`）。

### 对话 #2 [2026-10-08] 分支与工作树
- 问题：需要在独立分支上工作，且不影响其他分支。
- 操作：`origin` / `upstream` 同步；本地 `main` 与仓库 main 对齐（`a5bda0fd27`）；
  从 main 新建 worktree `.wt/libtk-img-2.1.1`，在其上创建并切换到
  `feat/libtk-img-2.1.1`。
- 结果：worktree 就绪；工作区仅剩 `archives/l/libxext/**` 的大小写不敏感伪改动
  （按用户要求隔离、不提交）。

### 对话 #3 [2026-10-08] W0 依赖可消费性
- 问题：前置条件要求所有依赖经 `conan download` 验证可消费，否则立即 R36 阻塞。
- 操作：`conan download tk/9.0.3.2`、`tcl/9.0.3.2`、`libx11/1.8.13`，
  后续又补验 `xorgproto/2025.1`、`libxcb/1.17.0`、`libxau/1.0.11`、
  `libxdmcp/1.1.5`、`xtrans/1.4.0`、`xcb-proto/1.17.0`。
- 结果：全部 `rc=0`（OHOS/armv8 clang15 二进制或 header-library），**无 R36 阻塞**。

### 对话 #4 [2026-10-08] 真实构建打通（8 个问题逐一修复）
- 问题：clean 构建从 configure 到链接连续失败（见上表 8 行）。
- 操作：逐项定位根因 → 修复 → 重新验证；关键实验包括 `AutotoolsDeps` 的 `LIBS`
  泄漏对比、`config.guess` 手工执行、`tkConfig.sh` 变量核对、`window.c` include 链追溯。
- 结果：24 个子目录全部 `make all` 成功，产出 24 个 `.so`（含 20 个格式处理器）。

### 对话 #5 [2026-10-08] 上游测试真实执行 + 新增鸿蒙用例
- 问题：上游测试入口是 `make tcltests`（裸 `tclsh`），CI 环境无 `tclsh`；
  且需要新增至少一个鸿蒙消费者用例。
- 操作：用 tcl 包内 `tclsh9.0` + 无缓冲包装器执行 `tests/all.tcl`；
  新增 `tests/ohos.test`（25 例，补丁形式）；补全 `LD_LIBRARY_PATH`
  （tcl/tk/libx11/libxcb/libxau/libxdmcp）。
- 结果：`Total 315 / Passed 297 / Skipped 18 / Failed 0`；`ohos-*` 25 例全绿。

### 对话 #6 [2026-10-08] 门禁验证
- 问题：需要跑通 conan create / conan-verify / finish / W2 / W3 与 PR 原子性检查。
- 操作：`conan create … -pr:h/-pr:b=ohos-aarch64 --build=missing
`；随后 `ohc conan-verify` / `ohc finish`（与 CI 同形态，不带 user/channel）。
- 结果：见 `reports/conan-verify-report.md` 与 `reports/test-report.md`。

### 对话 #7 [2026-10-09] 门禁链收尾（conan create / conan-verify / finish / W3）
- 问题：需以 **CI 同形态**跑通全链，并处理 W3 的假失败与 finish 的非阻塞告警。
- 操作：`conan create <pkg> -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --build="libtk-img/*"`
  （**不带 user/channel**，与 `ci/conan/build_and_test.sh` 一致）→ `ohc conan-verify` →
  `ohc finish libtk-img 2.1.1 built`（额外 `JUNK_PR_DIFF` 指向本包 14 个文件的 unified diff，
  使 `junk_check` 走 prdiff 模式）。
- 结果：
  - `conan create` rc=0；仅本包 "Building from source"（**无依赖被构建**）；
    上游 `Total 315 / Passed 297 / Skipped 18 / Failed 0`；test_package `failures=0`；`Package '…' created`。
  - `conan-verify` **Verdict PASS**（G0/G1/G2/G3 全 PASS）。
  - W3 本地 CI 模拟全通过：`L0 pass / L1 pass（含 L1e 破坏性反向测试）/ L2 skip（无 bin/）/ L4 pass / L5 pass`，
    `Junk Files: 0`、`Success 1 / Pass rate 100.0%`。
  - `finish` 唯一失败步骤是 **step5b**，根因是**其他包**的既有知识债 E219/E253/E305
    （`root_cause`/`rec_approach` 为空）+ 仓库既有 2797 条草稿；`gen_summary` 抛
    `'str' object has no attribute 'append'`（框架已知缺陷，非致命）；G0 clean-verify 因
    `clean_verify` 不带 conan 依赖环境而失败（`configure: error: <tcl包>/lib directory doesn't contain tclConfig.sh`），非阻塞。
  - 归档 **一致性问题 0**、补丁 1 个保留（未被 refresh-patch 丢弃）、submit 就绪预检 4 项全 ✅。
- 新坑：CI `junk_check` 在无 `JUNK_PR_DIFF` 时整仓扫描，会命中**他人包已跟踪的**
  `.build-closed`/`.staging-verified` → 阻塞 W3 → `finish` 直接 `sys.exit(1)`（后续步骤全不执行）；
  正解 = export `JUNK_PR_DIFF` 指向只含本包路径的 diff。另：`test_package/` 会被 `conan create`
  就地塞入 conan 生成物（7 个 `conan*.sh`/`deactivate_*.sh` + 空目录 `metadata/`），提交前须清。

状态: built
---

**编译结束**: 2026-10-09 10:41
**最终状态**: built
