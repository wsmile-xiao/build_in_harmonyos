# phylonium 1.7 适配笔记（设备真机，hw-9）

- 包/版本：phylonium/1.7（`package_type = "application"`，`bin_PROGRAMS = phylonium`）
- 上游：https://github.com/EvolBioInf/phylonium （tag `v1.7`）
- 赛道：cpp / autotools
- 终态：**conan create 真机通过（rc=0），上游 `make check` 2/2 PASS，消费者测试 12/12 PASS**
  - recipe revision `d32d95f04d56c8a9a4f50aadad914072`
  - package id `5700eb7cf8b7e169106d648238533d988254538d`（package revision `cbfe169d27a52b7dd6685af17d578d33`）
  - 全量日志：`~/tmp/uc2/hw-9/logs/create-full-20260927-132858.log`
  - 状态一律记 `built`：未 upload、未发布（AGENTS §8.1）

## 1. 源码件与来源核验

| 项 | 值 |
|---|---|
| URL | `https://github.com/EvolBioInf/phylonium/archive/refs/tags/v1.7.tar.gz` |
| sha256 | `87fc0828c4c96dc9b84e0bac640e7e1aaba749a9f218e1d4c4fbaa02d80412a0` |
| 大小 | 424647 B，顶层目录 `phylonium-1.7/`（`strip_root=True`） |
| 文件数 | 49 个文件 + 7 个目录条目（`tar tzf` 合计 56 条） |

Ubuntu pool 的 `phylonium_1.7.orig.tar.gz`（sha `4a19798e…`）是 Debian 删掉 `.travis.yml`
后的重压缩件，**不得**进 `conandata.yml`（R39：必须官方源）。

设备到 `github.com:443` **无路由**（实测 `curl: (28) Failed to connect to github.com:443`），
故按 AGENTS §12.3 把已验 sha256 的官方件预置进共享下载缓存
`~/tmp/ch/dlcache/s/<sha256>` + 同名 sidecar（只登记官方 URL），日志行
`Source ... retrieved from local download cache` 即生效证据。**不得**把镜像/`file://` 写进配方。

## 2. 依赖

- 宿主依赖 `libdivsufsort/2.0.1`：**无条件硬依赖**——`configure.ac:43-48` 用
  `AC_CHECK_HEADERS([divsufsort64.h])` + `AC_CHECK_LIB(divsufsort64, divsufsort64, ...)`，
  缺失即 `AC_MSG_ERROR([Missing libdivsufsort64.])`，无 `--disable` 开关。
  命中已发布的 OHOS static 制品 `83bf02d1dba113206f930938aa488b92249a1825`
  （`divsufsort64=True`），由 `AutotoolsDeps` 注入 `-I…/include` 与 `-ldivsufsort64`；
  真机链接行实证：`… -o simf simf-simf.o -ldivsufsort64 -lm -ldivsufsort`。
- `tool_requires`：`autoconf/2.72`、`automake/1.18`、`libtool/2.5.4.1`。
  坑：`libtool/2.5.4` 远端能列出一个包但**归档树无该版本目录**，`automake/1.17` 目录在但无
  `conanfile.py` —— 两者都会在 graph 解析期失败，必须 pin 成上面这组。
- W0：`bash ci/scripts/preflight_check.sh phylonium/1.7` → 4 个依赖全部 `[OK] 已发布`，
  且 `版本号未被占用: phylonium/1.7`（R37）。

## 3. 关键适配决策

1. **`--disable-x86simd --disable-avx512`**：`configure.ac:50-67` 两个 `AC_ARG_ENABLE`
   默认值都是 `enabled` 且**无 CPU 自动探测**，开着会让 `libs/Makefile.am` 去编
   `-msse2 / -mavx2 / -mavx512bw -mavx512vl` 的 x86 目标码，aarch64 必挂。
2. **必须 autoreconf 自举**（上游 Readme 原话 `autoreconf -fi -Im4`）：tag 件不含
   `configure`/`aclocal.m4`/`Makefile.in`，而且 **`configure.ac:85` 写的是
   `AC_CONFIG_HEADERS([config.h:config.hin])`，tarball 里根本没有 `config.hin`**
   （7 个源文件 `#include "config.h"`）—— 是 `autoreconf` 触发的 autoheader 生成该模板。
   同理顶层 `TESTS=` 需要 automake 的 `test-driver` 装进构建树。`-Im4` 是给
   `m4/ax_*.m4` 双保险（`AC_CONFIG_MACRO_DIR([m4])` 已被 aclocal 读，但照抄上游更稳）。
3. **不 `rm_safe("compiler.cppstd")`**（区别于 jaula）：`AX_CXX_COMPILE_STDCXX(17)` +
   `test/Makefile.am` 写死 `-std=c++17`，profile 的 cppstd=17 与之同向；
   全树无 `throw(...)` 动态异常规范、无 `register`，没有降级 C++ 标准的理由。
4. **E386 shell 路由**：共享 profile `ci/conan/profiles/ohos-aarch64` 的 `[buildenv]` 把
   `SHELL`/`CONFIG_SHELL` 钉成 `/data/service/hnp/bin/bash`，autoconf 序言用
   `exec $CONFIG_SHELL … "$as_myself"` 自重执行，而 hnp bash 在 HMDFS 构建目录 `getcwd()` 必挂。
   配方用 `_configure_with_binsh()`：`env CONFIG_SHELL=/bin/sh SHELL=/bin/sh /bin/sh <src>/configure <args>`，
   参数仍由 `load_toolchain_args()` 从 `conanbuild.conf` 取回（不手抄 `--prefix`）。
   `self.run()` 默认仍套 `conanbuild` 环境（`ConanFile.run` 在 `scope="build"` 时 env 空值→`conanbuild`），
   所以 `AutotoolsDeps` 的 `CPPFLAGS/LIBS` 与工具链的 `CC/CXX` 不丢，只换这两个 shell 变量。
5. **E011/E114**：autoreconf 之后把生成 `configure` 里的 `umask 077` 放宽为 `022`，并给
   `ac_pwd=\`pwd\`` 加 `$PWD` 回落（配方内定向改写，不产补丁、不改缓存包）。
6. **`make -j1`（含 `install`）**：HMDFS 无 `mkfifo` ⇒ make jobserver 在 `-j>1` 时不可用；
   `install` 也显式 `-j1`，否则 conan 会按 `tools.build:jobs=2` 自动追加 `-j2`。
   （窗口侧资源纪律另见 §6。）
7. **许可证随配方发布**：上游 tag 与 master **都没有许可证文件**，而逐源文件
   `SPDX-License-Identifier: GPL-3.0-or-later`，故发布 GPL-3.0 正文
   （`exports_sources = "licenses/*.txt"`，包内 sha256 `fb981668c18a279e285fc4d83fba1e836cc84dd4daa73c9697d3cfd2d8aca6e0`，
   与源侧文件一致）。**取文件必须用 `self.export_sources_folder`（缓存 `es/`）而不是
   `self.recipe_folder`（缓存 `e/`）** —— 见 §5 故障 3。
8. **E543**：HMDFS 新落盘件默认 660，`package()` 对 `bin/phylonium` 补 `chmod 0755`；
   真机实测交付件为 `-rwxrwx---`，test_package 直接执行成功。
9. **`--build/--host` 一个都不传**：`configure.ac` 无 `AC_CANONICAL_HOST`，且 `-pr:b` 与
   `-pr:h` 同为 OHOS（conan 判非交叉）⇒ 不生成三元组参数、config.guess 不被调用，
   整包避开 E007/E122/E072 家族（本机 `uname -s` = `HarmonyOS`，一旦真跑 config.guess 必挂）。

## 4. 上游测试账本（AGENTS §10.1 / R51 口径）

| 维度 | 数 | 判据（源码，不靠日志回填） |
|---|---|---|
| `N_static`＝`N_registered` | **2** | 顶层 `Makefile.am:10` `TESTS=test/simple.sh test/unittests` |
| `N_executed` | **2** | `make check`：`PASS: test/simple.sh`、`PASS: test/unittests` |
| `# TOTAL/PASS/FAIL/SKIP/XFAIL/ERROR` | 2 / 2 / 0 / 0 / 0 / 0 | 真机 `test-suite.log` 聚合，配方回显 `[upstream make check] # …` |
| 未执行 | **0** | 无条件跳过项；`unittests` 内部 6 个 `TEST_CASE`、43 个 `REQUIRE` 全部随该注册项跑完 |
| `N_consumer` | **12** | `test_package/test.sh`，全部真跑交付后的 `bin/phylonium` |

- **`simf` 不得计入分母**：`test/Makefile.am:1` 里它只是 `check_PROGRAMS`，是
  `simple.sh` 内部调用的数据生成器（`simf -s $SEED -l 100000 -p simple`），不是注册测试。
  原子口径与注册口径分列表述，不互相顶替。
- `test/simple.sh` 依赖构建树路径（`./src/phylonium`、`./test/simf`）⇒ 只能在 `make check`
  的 VPATH 顶层目录里跑，**不能**当交付后测试复用；故消费者测试另写（§5 断言清单）。
- 通过率申报口径：上游注册项 2/2；上游原子断言 43（Catch）；消费者 12/12。

## 5. 真机故障与修复（逐条，含第一条真实错误）

**故障 1 — autoreconf 期 perl 双架构（第 1 次构建，`logs/create-20260927-130751.log`）**
```
Can't load '.../perl/5.42.2/aarch64-linux-thread-multi/auto/Cwd/Cwd.so' for module Cwd:
Error relocating ...: Perl_my_cxt_init: symbol not found at .../XSLoader.pm line 94.
Compilation failed in require at /data/service/hnp/bin/autoreconf line 48.
ERROR: phylonium/1.7: Error in build() method, line 188  autotools.autoreconf(...)
ConanException: Error 255 while executing
```
根因：`conanbuild` 注入的 `PERL5LIB` 指向 conan `perl/5.42.2` 的 `aarch64-linux-thread-multi`
库目录，而 PATH 上先解析到的 `/data/service/hnp/bin/autoreconf` 跑的是**系统 perl**
（5.42.2 harmonyos 版）；两套同名异体 arch 目录不互通 ⇒ XS 模块重定位失败。
修法：**命中既有知识 DRAFT-6049**（libnxml 0.18.5 同族 `Cwd.c handshake mismatch`），
照其 `rec_approach` 做解释器统一（`_autoreconf_command()`）：
`PATH="<autoconf>/bin:<m4>/bin:$PATH" PERL=perl PERL5LIB="<automake>/share/automake-1.18:<autoconf>/share/autoconf" autoreconf -fi -Im4`
—— `PERL5LIB` 收窄到两包的**纯 Perl** 模块目录，核心 XS 模块回落系统 perl 自带 `@INC`，
解释器与 `Cwd.so` 同源。不改缓存包、不打补丁、不 shim。
> 补注：`spi-tools/0.8.4` 走的是另一条路（干脆不 `tool_requires` autoconf，用 HNP 系统件）。
> 本包需要 `libtool/2.5.4.1`+`automake/1.18`+`autoconf/2.72` 三件套的显式版本，保留 conan
> autoconf 并统一 perl 更可控；DRAFT-6049 的方案对本变体签名同样有效（新增一条实证）。

**故障 2 — 消费者测试自身判定式写错（第 2/3 次构建）**
11/12 通过，唯一红的是 `NOT OK - row ids / row count wrong: genomeA genomeB genomeC `
—— IDs 其实**完全正确**，错在我的 awk：`NR!=2 && NR!=3 && NR!=4{print "EXTRA"}` 对
NR==1（PHYLIP 首行的分类单元数 `3`）也成立，把首行拼进了 ID 串 ⇒ 断言式自身假红。
改为直接比对 `NR>1` 的 ID 串 + 行数（`nrows == 3`）。被测软件无缺陷。

**故障 3 — 包内没有 licenses/（第 4 次构建后发现）**
`package()` 用 `os.path.join(self.recipe_folder, "licenses")` 取许可证文本，
而 `exports_sources` 的文件在真机缓存里落在 `p/<h>/es/licenses/`，`recipe_folder` 是 `p/<h>/e/`
（只有 conanfile/conandata）⇒ `copy()` 匹配 0 个文件且**静默不报错**，包树缺 `licenses/`。
改用 `self.export_sources_folder`，并加"打包后存在性断言"（缺文件直接 `ConanException`），
防止再次静默漏包。第 5 次构建包树已含 `licenses/GPL-3.0-or-later.txt`。

## 6. 资源与并发（AGENTS §14.1）

- 构建前一律 `sh ~/tmp/uc2/hw-9/gate.sh 4000`（轻件档；本包实测 `MemAvailable≈4.9–5.2GB`、
  `PSI full avg10≈77%`，默认 6000 / 重档 8000 当时不过），窗口内单构建串行。
- 抢槽：`sh ~/tmp/uc2/hw-9/build-slot.hw-9.sh --wait 3600 --mem 4000 -- conan create …`；
  锁路径保持全机共享 `$HOME/tmp/uc2/.build-slots`。
  快照纪律：`build-slot.hw-9.sh` 与 `gate.sh` 均已与仓库版 `经验文档/tools/*.sh` 逐字节
  `diff` 核对（CR 归一后 0 差异），**无漂移需记录**。
- 消费者测试峰值内存实测（`memcap-run.py --probe`）：**4 MB**；按上游 `simple.sh`
  的 `-l 100000`（约 100× 输入）线性外推 **≈500 MB** ⇒ `test_package/MANIFEST.yml`
  记 `max_rss_mb: 64`（覆盖实测并留余量；不外推全量上机）。
- 环境：`CONAN_HOME=~/tmp/ch/home-hw-9-phylonium`（`global.conf` 加
  `core.sources:download_cache=~/tmp/ch/dlcache` 与 `tools.build:jobs=2`；
  `remotes.json` 的 `ohpcd` 在册——缺它会把"远端未配置"误诊成"依赖未发布"）。

## 7. 复现命令

```bash
export PATH=$HOME/usr/local/bin:$HOME/.local/bin:$PATH
export CONAN_HOME=$HOME/tmp/ch/home-hw-9-phylonium
export SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem
unset CONAN_USER CONAN_CHANNEL
cd ~/qzy/hw-9-phylonium-1.7
bash ci/scripts/preflight_check.sh phylonium/1.7                 # W0
sh  ~/tmp/uc2/hw-9/gate.sh 4000                                  # 择窗
sh  ~/tmp/uc2/hw-9/build-slot.hw-9.sh --wait 3600 --mem 4000 -- \
  conan create archives/p/phylonium/1.7 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 8. 交付产物（`conan create` 后包树）

```
bin/phylonium                        1219264 B；ELF 64-bit LSB arm64, dynamic
                                     (/lib/ld-musl-aarch64.so.1), not stripped；mode 770 可执行
share/man/man1/phylonium.1           由 man/phylonium.1.in 经 configure 生成后 make install 装入
share/doc/phylonium/manual.pdf       上游 documentation/manual.pdf
licenses/GPL-3.0-or-later.txt        sha256 fb981668c18a…（随配方发布，见 §3.7）
```
R38：`archives/p/phylonium/commands.json` 已声明该 tool（`type: tool`、
`versions."1.7".ref = "phylonium/1.7"`）。

## 9. 消费者测试断言清单（12 条，全绿；判定式全部来自上游源码/手册）

1. `--version` 在真机执行交付 ELF 并输出 `phylonium 1.7`（`phylonium.cxx:418`）
2. 三基因组长运行 rc=0
3. stdout 矩阵非空（警告走 stderr，故 stdout 只有矩阵）
4. 首行 = 分类单元数 `3`（`io.cxx` `just_print()`）
5. 行 ID = 去扩展名文件名 `genomeA genomeB genomeC`，且**无多余行**
6. 对角线全 0（矩阵确为 N×N）
7. 内容相同的两个基因组距离恰为 `0.0000e+00`（手册：0 means identical）
8. 2.5% 分歧对得到**有限正** JC 距离（实测 `2.5426e-02`；`nan` 即失败——<200bp 或 K>0.5）
9. 矩阵对称 `d(A,C) == d(C,A)`
10. 无 `--bootstrap` 时两次运行逐字节一致（`prng` 只被 `evo_model::bootstrap()` 用）
11. 缺输入文件 ⇒ 非零退出（`io.cxx` `read_fasta()` 的 `err()` → `EXIT_FAILURE`）
12. 只给 1 个文件 ⇒ 非零退出（`phylonium.cxx:249` `file_names.size() < 2` → `usage(EXIT_FAILURE)`）

成功时脚本自删工作目录（`phylonium-consumer-work` 不在 .gitignore 内，不留源树）；
失败时保留目录并把路径打进日志。

## 10. 已知限制与风险

- **OpenMP 被启用**（`AC_OPENMP` 探测通过，编译/链接行含 `-fopenmp`）：运行时 `THREADS`
  默认 `omp_get_num_procs()`。对 2 kB 级夹具无影响；超大基因组的内存/线程行为属上游算法
  固有特性，本次不改，也不把它算作适配缺陷。
- 交付件 `not stripped`（`phylonium_CXXFLAGS` 含 `-ggdb`，上游默认），体积 1.2 MB；未做
  strip 以保持与上游构建一致。
- 源件取用形态（2026-09-29 实测更新）：设备对 `github.com` 的直链出口已恢复（`curl -I` 官方
  tag 直链实测 302 / 1.65s），本轮 `conan-verify` G2 与 W3 均以 `conandata.yml` 里的**官方 URL**
  经共享下载缓存（`core.sources:download_cache=~/tmp/ch/dlcache`，blob 424647B 逐字节 sha 复核
  通过 + sidecar 登记三形态）命中；框架的 E017 镜像注入因 `ghfast.top` 可达性探测为假而未启用。
  **交付物 `conandata.yml` 只含官方 URL，不含任何镜像或本地路径**（W3 的 pre-download 阶段一度把
  `gh-proxy.com` 形态写回活文件，已用 `git show HEAD:<path>` 复原并 `git diff` 核为空）。
- 上游无 `NEWS/AUTHORS/ChangeLog`（`AM_INIT_AUTOMAKE([... foreign])` 已豁免），
  `documentation/Makefile` 不在 `AC_CONFIG_FILES` 内（是随手写的静态 Makefile，不参与构建）。
- 已完成：`conan-verify`（G1/G0/G2/G3 全 PASS、`VERIFY_RC=0`）与 `finish built`（W3 本地 CI 模拟
  `Total 1 / Success 1 / Failed 0 / Pass rate 100.0%`，`Junk Files: 0`，L0/L1/L2/L4/L5 全 pass）。
- 仍未做（不得越口径宣称）：W4 独立审计、`submit`、建 PR、提审。因此本归档**不得**标
  `published`，也**不得**称"可以提审"——四件套（§11.4）须由 CIW 在当前 HEAD 的 CI/AI 证据齐备后判定。

## 11. 对 B 判定的输入（供主理定档，本子代理不代判）

本次新增/命中的可复用机制，实测证据齐：
1. **DRAFT-6049 的 perl 解释器统一方案对 `Perl_my_cxt_init` 重定位变体同样有效**
   （原条目签名是 `Cwd.c handshake mismatch`）⇒ 既有条目的适用面扩大一条实证，偏 `hit`；
   若主理认定"新签名 + 同解法"算增量，则按 create 申报时可引 §5 故障 1 的完整证据链。
2. **`exports_sources` 落到缓存 `es/`，`package()` 必须用 `self.export_sources_folder`**，
   且 `copy()` 匹配 0 文件时**静默不报错** ⇒ 跨包通用坑（任何随配方发布许可证/数据的
   包都会撞上），值得单独一条机制草稿。
3. `AC_CONFIG_HEADERS([config.h:config.hin])` + tarball 缺 `config.hin` ⇒ 只能靠
   autoreconf 的 autoheader 生成模板（"tag 件没 configure 也没 config.hin"家族）。
---

**编译结束**: 2026-09-29 20:44
**最终状态**: built


## 12. B 判定定档与交付状态（new_hw-9，2026-09-29）

- **B 判定 = create（已落盘，非候选）**：`knowledge/drafts/DRAFT-phylonium-1.7-x86-runtime-dispatch-default-on.kv`
  与同 stem `.md` 成对随本 PR 提交。仓库真解析器 `draft-review`：质量三项 signature/root_cause/rec 全
  PASS、预审建议 create、相似 TOP1 仅 E100 0.16（低于灰区）。关联 Issue **#3524**。
  判 create 而非 §11 三条中任一条的理由：本包真正的稳定错误签名是"x86 运行期 CPU 分发内建
  `__builtin_cpu_init`/`__builtin_cpu_supports` 在 aarch64-OHOS clang 上不存在"，且改前/改后对照读数已做实
  （见 §5 故障 1 与 B 判定记录）；§11 第 1 条（DRAFT-6049 适用面扩大）与第 2 条（`export_sources_folder`
  坑）作为**已复用/已知机制**在正文"使用知识库"里引用，不另发草稿（一 PR 一知识）。
- **取包与依赖事实不变**：官方 tag `v1.7`（必须带 `v`，`refs/tags/1.7.tar.gz` 实测 404）；
  Ubuntu pool 件是 Debian 删掉 `.travis.yml` 后的重压缩（424468B/48 文件 vs 官方 424647B/49 文件），
  故**池 URL 不得入交付**；`libdivsufsort/2.0.1` 为无条件硬依赖（`configure.ac` 的 `AC_MSG_ERROR` 无
  `--disable` 开关），远端 OHOS 制品 `package_id=83bf02d1dba113206f930938aa488b92249a1825`
  （`divsufsort64=True`/static/clang15/libc++/cppstd17/armv8/OHOS 6.0）。
- **测试口径（与 PR 正文同源）**：`N_static = N_registered = N_executed = 2`（顶层 `Makefile.am:10`
  `TESTS = test/simple.sh test/unittests`）；`simf` 只进 `check_PROGRAMS` 不注册，**不入分母**；
  `test-suite.log` 逐字 `# TOTAL: 2 / # PASS: 2 / # SKIP: 0 / # FAIL: 0 / # ERROR: 0`。
  消费者测试 `test_package/test.sh` **12 条断言全 PASS**（`consumer assertions: pass=12 fail=0`）。
