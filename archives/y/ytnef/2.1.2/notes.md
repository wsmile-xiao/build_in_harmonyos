# ytnef 2.1.2 适配笔记（HarmonyOS PC / OHOS aarch64）

## 编译环境
- 构建系统: autotools（上游 git-archive 快照**不含 configure**，必须 `autoreconf -fi` 引导）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，profile: `ci/conan/profiles/ohos-aarch64`）
- 目标平台: HarmonyOS PC (aarch64 / os=OHOS / armv8)
- 状态: published（`conan create` 与 `conan-verify` G0-G4 + L2/L4/L5 全绿）

## 源码与方案
- 上游: https://github.com/Yeraze/ytnef ，tag **v2.1.2**（commit `d9f089144414d3b0912c29ab96f8f1c591d00319`）
- URL: `https://codeload.github.com/Yeraze/ytnef/tar.gz/refs/tags/v2.1.2`
  - **必须同时给 `filename: ytnef-2.1.2.tar.gz`**：codeload 形式的 URL 以裸 tag `v2.1.2` 结尾，
    不给 filename 时 Conan 无法判断归档格式，会按 zip 解压并报 `BadZipFile: File is not a zip file`。
  - 不使用 `https://github.com/...` 形式：conan_verify/CI 会对含该前缀的 conandata 临时注入
    ghfast.top 镜像（实测已注入，虽然本机 G2 仍通过，但避免依赖镜像可用性）。
- sha256: `340f03f495884611209e9c0bc943fad06ce920e8c79655aa228d5ca7418dc360`（与 init-build 下载物一致）
- 产物:
  - `lib/libytnef.a` + `lib/pkgconfig/libytnef.pc`（默认 `shared=False`；`-o shared=True` 可产出 `libytnef.so.0.0.0`）
  - `include/`：ytnef.h / mapi.h / mapidefs.h / mapitags.h / tnef-types.h / tnef-errors.h
  - `bin/`：ytnef、ytnefprint、ytnefprocess（perl 脚本，上游原样安装）
- 依赖: **无第三方库**。configure.ac 只有 `AC_PROG_CC` / `AC_PROG_LIBTOOL`，无 `AC_CHECK_LIB`、无
  pkg-config；只需 libc + libtool（W0 依赖链为空，无需先发布任何依赖）。
- tool_requires: `automake/1.18` + `libtool/2.5.4`（本机与 CI 均无系统 automake/aclocal/libtoolize，
  HNP 只提供 autoconf 套件）——与 `archives/a/abiword-plugin-*/3.0.8` 同款做法。

## 编译步骤（探索阶段实测）
```bash
# 1) 工具链环境（conan 侧拉 automake/libtool）
conan install . -pr:b=ci/conan/profiles/ohos-aarch64 -pr:h=ci/conan/profiles/ohos-aarch64 \
    --build=missing -g VirtualBuildEnv        # tool_requires: automake/1.18 libtool/2.5.4 autoconf/2.72 m4/1.4.19
source conanbuild.sh

# 2) 引导 configure（git archive 无 configure）
mkdir -p m4 && autoreconf -vfi

# 3) E007：给生成的 config.guess 注入 HarmonyOS 分支（config.sub 已支持 linux-ohos）
#    —— 见下方「问题 1/2」

# 4) configure / make / install
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX

# 5) R51 上游测试
cd test-data && ./test.sh
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type`，configure 报 `cannot guess build type` | **E007**：GNU config.guess 无 HarmonyOS 分支；`uname -s` 返回 `HarmonyOS`，`uname -r` 为 `HongMeng Kernel 1.12.0`，无法匹配任何已知系统。且 config.guess 缺识别时还会走编译器探针，其 `mktemp -d`（umask 077）在 HMDFS 上生成 `drwx--S---` 不可写目录，报 `Permission denied` | 在 `uname` 分派表 NetBSD 分支前插入 `*:HarmonyOS:*:*)` → `GUESS=${MACHINE}-unknown-linux-ohos`（**不含 `__OHOS__`**，HARMONY 分支不进入 Linux/GNU 分支，故无需 LIBC 探针 → 规避 R8/PF5 平台宏红线）。**未使用 `--build/--host`**（E205/R1 禁止） |
| 2 | config.guess/config.sub 无法用 conandata 补丁修复 | 二者由 `autoreconf` 生成，**pristine tarball 中不存在**（`.orig` 无 config.guess），补丁无从匹配；而 patch 在 `source()` 阶段应用，早于自动生成 | 在 `build()` 中 `autoreconf` **之后**用配方内 Python 函数就地补全（幂等：已含 `linux-ohos` 则跳过）。`config.sub`（automake 1.18 版）本身已支持 `aarch64-unknown-linux-ohos`，仅在缺失时补齐 |
| 3 | `./config.status: line 819: ./confmAOPle/subs1.awk: Permission denied` → `could not setup config files machinery` | **E114 家族**：系统 autoconf（HNP 2.72，未打 OHOS 补丁）生成的 config.status 走通用分支 `umask 077 && mktemp -d "./confXXXXXX"`；HMDFS 把 0700 目录变成 `drwx--S---`，属主也不可写。（注：conan 制品仓里的 `autoconf/2.72` 是打过 OHOS 补丁的，其 `m4sh.m4` 含 `linux-ohos*:* \| *:HarmonyOS)` 快速分支；但 build env 的 PATH 里 `/data/service/hnp/bin` 在前，`autoconf` 解析到系统版） | `_harden_configure_tmpdir()`：在 configure 运行前从生成的 `configure` 中删除 `(umask 077 && mktemp -d "./confXXXXXX")` / `(umask 077 && mkdir "$tmp")` 的 `umask 077`（config.status 由 configure 内嵌模板生成，改 configure 即同时覆盖两者）。与 `abiword-plugin-*`、`abook` 同款处置。**注意**：`mkdir` 走 umask 077 在 HMDFS 上得到 `drwxrws--x`（可写），是 `mktemp -d` 才得到不可写的 `drwx--S---` |
| 4 | `autoreconf` 失败：`Can't load Cwd.so ... Permission denied` / `Perl_my_cxt_init: symbol not found` | conan `automake/1.18` 的 `aclocal`/`automake` 包装脚本指向**系统 perl**（`#!/data/service/hnp/bin/perl`，5.42.0 非线程版），而 `VirtualBuildEnv` 把 `PERL`/`PERL5LIB` 指向 conan perl（5.42.2 thread-multi）。两套 perl 混用导致 XS 模块 ABI 不匹配 | `_bootstrap_configure()` 内统一到**系统 perl**（`unset PERL` 让 conan 包装脚本 `"${PERL:=perl}"` 回退到 PATH 的 perl），并把 conan automake 的 `share/automake-*` 加入 `PERL5LIB`（`Automake/Config.pm` 在那里）。此时 conan 的 `autoconf`/`autoreconf` 包装脚本也用系统 perl，全链路一致 |
| 5 | `make` 报 `jobserver mkfifo: ... Operation not permitted` | **E074**：HMDFS/SELinux 禁止创建 jobserver FIFO | 全部 `make`（含 `make install`）带 `-j1`；实测 `-j2` 也会告警（make 会退化继续），配方统一 `-j1` |
| 6 | 上游 `test-data/test.sh` 在 conan 构建里报 `../ytnef/ytnef: No such file or directory` | Conan 使用 **out-of-source** 构建（`basic_layout` → build 目录 `build-release/` 在 source 目录之下），`test.sh` 用相对路径 `../ytnef/ytnef` 且 `test-data/` 的测试夹具不会被复制进 build 目录 | `_run_upstream_tests()` 先把 `test-data/` 内容镜像进 build 目录再 `cd test-data && bash ./test.sh`（source/build 同目录时跳过镜像） |
| 7 | `conan create` 报 `BadZipFile: File is not a zip file` | codeload URL 末尾是裸 tag，Conan 无法推断格式 | conandata.yml `sources` 增加 `filename: ytnef-2.1.2.tar.gz`（仓库内 241 个 codeload 配方同样做法） |
| 8 | test_package 把 CMake 构建产物写进 `test_package/`（污染归档） | test_package 未声明 layout，CMake 就地构建 | test_package `layout()` 使用 `cmake_layout(self)`，构建树落到 `build/<triplet>-<build_type>/` |
| 9 | **CI `checkout-pr` 阶段失败**：`error: missing binary patch data for 'archives/y/ytnef/2.1.2/test_package/one-file.tnef'` → `PR 10776 diff 无法应用——PR 与 main 分支存在冲突`（build #50321，4.9s 即失败） | GitCode 的 MR `.diff` 端点**不输出二进制补丁数据**（无 `GIT binary patch` 段，只有 `Binary files differ`），而 CI 用 `git apply pr.diff` 重建 PR 工作区 → 只要 PR 新增任何二进制文件，`checkout-pr` 必然失败（报"冲突"是误导性提示） | `test_package/one-file.tnef` 改为 **base64 文本** `one-file.tnef.b64`（40 行 ASCII，2272 B 原文），由 `test_package/conanfile.py` 的 `_materialise_fixture()` 在 ctest 前 `base64.b64decode` 还原到 CMake 构建目录；`CMakeLists.txt` 移除 `configure_file`。**教训：PR 中不得新增二进制文件**（图片、夹具、.a/.so 均不可） |

## 源码修改（补丁）
**无补丁（`patches/` 为空）。** 本包不需要改任何上游源码：
- E007 的 config.guess 补全针对 `autoreconf` **生成**的文件（pristine 中不存在），只能运行时处理；
- E114 的 umask 处理同样针对生成的 `configure`，属运行时处置（abiword/abook 先例）；
- 二者均不落 `.patch`，因此 `patches/` 为空、PF5 平台宏闸无触发项。

运行时补全的实际写入内容（config.guess，插入到 `*:NetBSD:*:*)` 之前）：
```
    *:HarmonyOS:*:*)
	case "$UNAME_MACHINE" in
	    aarch64|arm64) MACHINE=aarch64 ;;
	    armv7*|armv8*) MACHINE=arm ;;
	    x86_64|amd64)  MACHINE=x86_64 ;;
	    i?86)         MACHINE=i686 ;;
	    *)            MACHINE="$UNAME_MACHINE" ;;
	esac
	GUESS=${MACHINE}-unknown-linux-ohos
	;;
```

## 依赖版本
- conan 依赖：无
- tool_requires：automake/1.18、libtool/2.5.4（build context，与 host 同 profile）
- 运行期 extra：无（ytnef/ytnefprint 仅依赖 libc；ytnefprocess 为 perl 脚本，需 MIME::Parser 等 perl 模块——上游原本如此，CI 不执行）

## R51 上游测试清点与实测（真机实跑）

清点（`test-data/` 为唯一测试载体；`test-data/Makefile.am` 只有 `EXTRA_DIST`，**没有 `make check` 目标**，
上游 `travis-build.sh` 直接 `cd test-data && ./test.sh`）：

| 测试类型 | 上游用例数 | 来源 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无单元测试框架 |
| 集成测试 | 8 | `test-data/test.sh`（1 组附件提取 + 1 组字节级 diff + 5 组 ytnefprint 字段断言 + 1 组畸形输入健壮性） |
| 其他测试 | 0 | 无 |
| 合计 | 8 | |

实测结果（`cd test-data && ./test.sh`，探索阶段与 `conan create` build() 内各跑一次，两次均全绿）：

| # | 断言 | 实测 |
|---|------|------|
| 1 | `ytnef -f data winmail.dat` + `ytnef -f data *.tnef`（共 7 个夹具，脚本内 1 组提取） | ✅ 提取 15 个附件（winmail.dat → zappa_av1.jpg / bookmark.htm；6 个 `*.tnef` → 其余 13 个，含 AUTHORS、Techlib*.doc、generpts.src、allproductsmar2000.dat、208225_(5_seconds)_Voice_Mail.mp3） |
| 2 | `diff results data`（逐字节比对） | ✅ 无差异 |
| 3 | `PR_MESSAGE_DELIVERY_TIME` = `Tuesday June 17, 2003 3:23:00 pm` | ✅ |
| 4 | `PR_TNEF_CORRELATION_KEY` = `[00000000CFF233DD7623274EB78A4912C247A0E464532700.]` | ✅ |
| 5 | `PR_RTF_SYNC_BODY_CRC` = `872404792` | ✅ |
| 6 | `PR_RTF_SYNC_BODY_COUNT` = `90` | ✅ |
| 7 | `PR_RTF_COMPRESSED` 含 `\pard Casdasdfasdfasd\par` | ✅（grep 打印 `stray \ before p` 警告，上游脚本本身如此，不影响匹配） |
| 8 | 畸形输入 `ytnef-oob-TNEFVersion-SwapWord` → `ERROR: Field with size of 0` | ✅ |

**通过率：8/8（100%），失败项：0，上游用例未做任何修改。**
（口径说明：上游 `test.sh` 在 `set -ex` 下可失败的检查点为 8 个 —— 1 组附件提取 + 1 组 `diff results data` 字节比对 +
5 组 ytnefprint 字段断言 + 1 组畸形输入健壮性；上表按同一口径列 8 行，与 `reports/pr-body.md`、
`test_package/MANIFEST.yml` 的计数一致。提取步骤中 7 个夹具分两次 `ytnef` 调用完成，故不单列。）

## 验证结果
```bash
conan create archives/y/ytnef/2.1.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → build 全绿；build() 内 test.sh 8/8 通过
# → test_package: cmake + ctest 1/1 Passed（库 API 8 断言）+ ytnef -h / ytnefprint -h 可执行

python3 scripts/ohc-run.py conan-verify ytnef 2.1.2
# → G0/G1/G2/G3/G4 PASS + L2/L4/L5 PASS（报告: reports/conan-verify-report.md）

python3 scripts/pre_pr_audit.py report --audit-result <audit-result>.json ...
# → W4 Pre-PR 独立审计 PASS：verdict=pass，P0=0 / P1=0 / P2=0 / P3=5（全部非阻塞，见 reports/audit-result.json）
```

**W4 独立审计遗留 P3 处置**：① 运行时改写 `autoreconf` 生成的 configure/config.guess/config.sub —— 审计判定
可接受（生成文件不在 pristine tarball 中，无法走 conandata 补丁，且不涉及平台宏）；② 本文件 R51 计数口径已统一
（8 组，与 pr-body.md / MANIFEST.yml 一致）；③④ 本地残留 `conandata.yml.ghfast-bak`、`test_package/build/`、
`test_package/CMakeUserPresets.json` 已删除（三者本就未入库）；⑤ `url = ""` 为全仓模板约定（CI 填充）。

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | autotools 配方：tool_requires automake/libtool；`_bootstrap_configure()`（perl 统一 + autoreconf）；`_apply_harmonyos_autotools_fix()`（E007）；`_harden_configure_tmpdir()`（E114）；`_run_upstream_tests()`（R51） |
| conandata.yml | 官方 codeload 源 + filename + sha256；无补丁 |
| test_package/ | CMake 消费者测试：test.c 链接 libytnef 做 8 项断言 + 运行已安装 CLI；MANIFEST.yml 声明上游测试；夹具以上游 `one-file.tnef`（2272 B）的 **base64 文本** `one-file.tnef.b64` 分发，test() 内还原（避免二进制文件导致 CI `git apply pr.diff` 失败） |
| ../commands.json | 软件级 CLI 声明（R38，type=tool，versions.2.1.2.ref=ytnef/2.1.2） |
| reports/ | conan-verify-report.md、test-report.md 等 |

## 注意事项
- **不可用 `--build/--host` 绕过 config.guess**（E007/E205）：本包改用注入 HarmonyOS 分支的正当路径，
  构建设置为 native（build==host==`aarch64-unknown-linux-ohos`，`checking whether we are cross compiling... no`）。
- config.guess/config.sub 的补全**必须发生在 `autoreconf` 之后**；补丁管线（`refresh-patch --auto`）不会
  为生成文件产出补丁（编辑追踪器只跟踪 baseline 内文件的哈希变化）。
- `make` 必须 `-j1`（E074）；test.sh 必须在含构建产物与夹具的同一目录运行。
- **PR 中不得新增任何二进制文件**：GitCode 的 MR `.diff` 端点不输出二进制补丁数据（无 `GIT binary patch` 段），
  而 CI 的 `checkout-pr` 用 `git apply pr.diff` 重建工作区 —— 只要 PR 含新增二进制文件，该步必然失败
  （报 `missing binary patch data`，并误导性地提示"PR 与 main 存在冲突"），整个构建约 5 秒即终止
  （本轮实测 build #50321）。上游测试夹具须转为文本（base64）随配方分发，运行时还原。
- 知识条目: E007（config.guess HarmonyOS）、E114（HMDFS umask 077/0700 目录不可写）、E074（make jobserver FIFO）、
  E205（禁止 --build/--host 绕过）、E533（config.guess 缺 HarmonyOS 分支的同类案例）。

---
**编译结束**: 2026-09-18 12:2x
**最终状态**: published
---

**编译结束**: 2026-09-18 13:56
**最终状态**: published
