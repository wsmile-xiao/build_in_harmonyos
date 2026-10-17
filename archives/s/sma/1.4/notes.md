# sma 1.4 适配笔记

## 编译环境
- 构建系统: makefile（裸 Makefile，无 configure / CMake / Meson）
- 编译日期: 2026-09-25
- 编译器: clang（OHOS 镜像无 gcc；`make CC=clang` 覆盖上游硬编码）
- 状态: built（本地真机 B 机；`conan create` 已出包，test_package 见下）
- 构建主机: B 机（HarmonyOS aarch64），worktree `~/qzy/主理-32-sma-1.4`，分支 `feat/sma-1.4`
- CONAN_HOME: `~/tmp/ch/home-sma`（profile：`ci/conan/profiles/ohos-aarch64`）
- 证据目录: `~/tmp/uc2/z32-sma/`（第 1-2 棒）与 `~/tmp/uc2/z32-sma-r3/`（第 3 棒：
  `measure/` 暂定定义实测、`scan93.txt` 双向差集、`work/` 补丁后构建树、`after*.txt` 单点
  定义证据、`patch/` 补丁原件、`verify-r3.log` 门禁日志）

## 0. 先更正台账：本包不是 X11 系统监视器

`archives/s/sma` 的上一轮读码已否证"X11 监视器 / 运行时需 DISPLAY / 计数来自
/proc·sysfs·ioctl"的整段描述。本轮复核到的实物：`conf.h` 的
`COMMENT "Sendmail Log Analysis Report"`、`BOUNCE_ADDR "MAILER-DAEMON"`，
上游站点标题 "SMA - Sendmail log analyser"，源码只读普通文本文件。
⇒ 不存在 DISPLAY 问题、不存在 /proc·sysfs 能力墙、不存在"缺依赖制品"，也不该 `$P block`。

**并更正上一轮的一处偏差**：BSD 正则源码 `regex/` 只在 `_WIN32` 下被使用
（`sma.h:39-45`：`#ifdef USE_REGEXP` → `#if defined _WIN32` → `#include "regex/regex.h"`
`#else` → `#include <regex.h>`）。主 Makefile 的 `OBJS` 不含任何 `regex/*.o`
（只有 Makefile.w32 / Makefile.msvcp 编它们），所以 OHOS 走的是 **libc 自带的
regcomp/regexec**，`regex/` 在本平台是死代码（不是"源码级编进来"）。

## 1. 取源定案（PF7/R39）

| 通道 | 字节 | sha256 | md5 | 顶层目录 | 判定 |
|---|---|---|---|---|---|
| 上游官方站发布位 | — | — | 页面登记 `f7fc3f4fc16ae13f15cc6f3313c958a3` | — | **已失效**：`https://www.klake.org/sma/download.html` 200/4612 B，全文只剩 1 枚锚点 `<a href="/">Home</a>`，"Download the latest SMA source code" 等条目的链接已丢失；`<站点>/sma/dl/<任何候选文件名>` 一律 301 → `https://www.klake.org/`（3310 B HTML，sha256 `31fa9f24383024022f0c09700c0d8de5e91d351318e1c7fb6a029f1394152449`）。⇒ 登记 MD5 无从核对 |
| Debian pool `.orig` | 121902 | `865042635a62e8f0fa08a1a536f163c74a267e507749139d6d6881bf6bdae476`* | `33da00a4c4de94596e4c73f2340b5aca` | `sma-1.4.orig/` | 顶层目录被改名 ⇒ 下游重打包；`_pf7_classify` 对 `deb.debian.org` 判"Debian 下游重打包源"（`scripts/ohc/preflight.py:361,379-381`），不作构建输入 |
| **pkgsrc（NetBSD）distfile 缓存**（采用） | 121365 | `a5b5afbb2a8081f72a22e3dc4f2fe75e977d56883dd2466311fb16f3f07e30af` | `8b3e78589811afff2e552bc5da0db0bf` | `sma-1.4/` | 按 `pkgsrc mail/sma/Makefile` 的 `MASTER_SITES`（即上面那个已失效的官方发布位）原样抓取的上游原始 tar，pkgsrc 不重新打包 ⇒ 权威镜像 |

\* Debian `.orig` 的 sha256 与台账逐字一致（本机 `sha256sum` 复算）。

- `cmp` 结论：**两枚容器不可能逐字节相同**（121902 vs 121365）。按任务书"不等"分支改做内容级对撞：
  两棵解包树 `diff -rq <pkgsrc>/sma-1.4 <orig-extract>/sma-1.4.orig` ⇒ **输出 0 行、rc=0**
  （逐文件同内容）。差异只在打包层 ⇒ 两条通道送进编译器的源码同一份。
- 其它候选已实测排除：`distcache.FreeBSD.org`、`mirrors.dotsrc.org`（rc=000 连接失败，
  按"超时≠不可达"口径记录，未穷尽重试）；`distfiles.gentoo.org` 404；
  driver 的搜索引擎另给的 `waterlan.home.xs4all.nl` 属个人镜像 ⇒ R39 禁，不采用。
- ⛔ 未改 sha256 迁就校验、未用 `file://`/镜像代理域、未用 `--no-preflight`。
  采用件的 sha256 就是对那枚 121365 B 文件的实测哈希。

## 2. 编译步骤（实测）

```bash
cd <src>/sma-1.4
patch -p1 < patches/0001-sma.h-sma.c-globals-extern.patch   # build() 里由 apply_conandata_patches 施加
make -j1 CC=clang CFLAGS="-Wall -O -DUSE_REGEXP"            # rc=0（clang-15 默认 -fno-common）
```

### 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首次链接即红：`ld.lld: error: duplicate symbol: curr`、`duplicate symbol: wflag`（too many errors emitted, stopping now），`make` rc=2 | `sma.h` 把 **93 个**文件作用域全局（`char *pname;` / `time_t tval;` / `struct tm tp;` / `regex_t csef;` / `struct host first;` …）以**暂定定义**写在头文件里，8 个 TU 各带一份。1998 年 C 靠 `-fcommon` 时代的 COMMON 合并才链得动；OHOS clang-15（实测 15.0.4）默认 `-fno-common` ⇒ 同一符号在 8 个 `.o` 里各成强符号，链接期重复。**范围是实测的不是估的**：`nm --defined-only -g` 扫 8 个 `.o` 得 93 个跨 TU 重复符号，脚本对 `sma.h`/`conf.h` 的文件作用域暂定定义静态扫描同样 93 条、93 个名字，**两个集合双向差集均为 0**（`~/tmp/uc2/z32-sma-r3/scan93.txt`），另 8 个 `.c` 文件作用域同名定义 = 0 处 | 按 E491 `:21` 处方（replace tentative definitions with extern declarations plus one definition）出 `patch_type: portability` 源码补丁 `patches/0001-sma.h-sma.c-globals-extern.patch`（247 行 / 3 hunk / 4655 B，原样解包树上 `patch -p1 --dry-run` rc=0）：`sma.h` 的 93 条声明一律前缀 `SMA_G`——默认展开为 `extern`，只有在 `#define SMA_GLOBALS_DEFINE` 的那一个 TU（`sma.c`）展开为空、成为唯一真定义。**单点定义的证明**：8 个 `.o` 的 `nm --defined-only -g` 汇总里 `uniq -d` 零重复，且 93 个名字全部恰好出现 1 次、全部落在 `sma.o`（`~/tmp/uc2/z32-sma-r3/after.txt` `after_smao.txt`）。配方命令行**不再传** `-fcommon`（`E491:33-35` 明令禁用），`-DUSE_REGEXP` 仍显式带回，避免整串覆盖 CFLAGS 把正则过滤路径悄悄关掉 |
| 2 | 上游 `install` 目标写共享系统前缀且依赖 `./install-sh` | Makefile `BINDIR/MANDIR` 烧死系统前缀（PF6 禁在配方里出现该字面量）；本机 `install(1)` 不可用：`ls -l /bin/install` ⇒ **Permission denied**，`which install` ⇒ PATH 无 | 配方**不跑 `make install`**，`package()` 直接 copy `sma`→`bin/`、`docs/sma.8`→`share/man/man8/`、文档/配置→`doc/sma/`、`COPYRIGHT`→`licenses/` |
| 3 | `ohc-run build` Step1 rc=2 `init_build_failed` | 驱动去找 `archives/s/sma-1.4/src`（码路错配，与 `archives/s/sma/1.4/` 目录形制不一致），并顺手打印它自己的搜索结果 URL；`--resume-from=Step2` 仍报"源码目录不存在 / 未找到 .build-context" | 按既有教训**不重跑 init-build**（会覆盖手写配方），改用直连 `conan create` 出证据：见 §3 |

> 取舍依据（主窗 2026-09-25 已裁定；前一轮「保留 `-fcommon`」的口径作废并已撤回）：本包改走 E491 处方。
> 条目原文逐行核对（B 机 `knowledge/graph/E491.kv`）：
> - `:21` rec_description 要求 "replace tentative definitions with extern declarations
>   plus one definition"（优先级 1 处方）；
> - `:33` forbid_1_pattern 是 `(^|\s)-fcommon(\s|$)`；
> - `:34` forbid_1_reason："A global compiler compatibility flag hides invalid
>   declaration/definition relationships in old source code"；
> - `:35` forbid_1_consequence："Duplicate or ambiguous global state remains and can
>   fail again under another compiler or link mode"。
> ⇒ 全局兼容开关在本仓属**明令禁用形态**，W4 只要读 KB 就会撞上（旧 `conanfile.py:79` 与
> 本文件旧文本都带过它，现已撤）。
> **改上游源码 ≠ 路径 C**：补丁只改全局符号的声明形态，不动任何功能逻辑、不加不减能力面，
> 属本仓通用的 `patch_type: portability` 源码补丁（同仓先例形制见 `archives/a/anubis/4.3/patches/`）。
> COMMON 合并与本补丁产出的对象布局等价 ⇒ 行为不变：同一份 test.sh 在补丁后产物上 25/25。

## 3. 验证结果

```bash
# 依赖预检（无依赖声明）：rc=0
bash ci/scripts/preflight_check.sh sma/1.4
# conan create（干净构建，走 gate.sh + build-slot --kind short --mem 2500）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --user=ohpcd --channel=stable --build=missing
#   → sma/1.4@ohpcd/stable: Full package reference ... / Packaged 1 '.conf' file: sma.conf
#   → test_package: 随 create 一起跑；create rc=0 即 test.sh 全绿（旧轮此处是 24/25、A22 红、create 随之失败）
python3 scripts/ohc-run.py conan-verify sma 1.4        # VERIFY_RC=0
#   reports/conan-verify-report.md（1065 B / mtime 07:33）：**Verdict**: PASS，
#   G0/G1/G2/G3/G4/L2/L4/L5 均 PASS（旧轮的 G2 FAIL 与 L2 skip 已不再存在）
```

- 补丁后原生复跑（产物 `~/tmp/uc2/z32-sma-r3/pbin/sma`，B 机 07:31）：**25/25 PASS，rc=0**。
- A22 定案（r3 任务书 §1 三条候选逐条一手读数，两条 `[diag]` 已在 harness 里打印）：
  1. **CWD 差 ⇒ 否证**：`[diag] TMPD=/storage/Users/currentUser/tmp/_sma_tp.50686 pwd=[同一路径] pwdP=[同一路径]`；两臂在同一次 `cd "$TMPD"` 之后跑，`./sma.conf` 的
     相对查找不可能分叉（且 A14/A15 已单独断言默认配置查找行为）。
  2. **两臂输入字节差 ⇒ 否证**：`[diag] mail.log sha256=eb429ab3ed13b452490cd6a7e1610b90262c00e0d7f4204b0b9d1a637e2bc1c6`——stdin 臂与 `-f` 臂
     喂的是同一枚 `mail.log` 文件本身，不存在尾换行 / CRLF 分叉面。
  3. **env 差 ⇒ 也否证**：`[diag] TZ=unset LANG=C.UTF-8 LC_ALL=unset TMPDIR=…`，两臂同进程
     同环境，白名单无差。
  第一条真实差异（`cmp` 出来的那一行）：ASCII 报告第 2 行 `Generated at <asctime(当前时刻)> by SMA, version 1.4`（`ascii.c:52-59` 取 `time(2)` +
  `localtime`，**秒粒度**）⇒ 这是一条跨两次进程调用的**时钟抖动**比对：原生连跑快、两臂落在
  同一秒 ⇒ 绿；conan `create` 在 A6 与 A22 之间还夹了打包/校验耗时、两臂跨秒 ⇒ 红。
  结论：**是 harness 的可比性前提缺失，不是被测逻辑差异**。
- 修法落在 harness、不放宽判据：A12/A22/A23 三条跨进程逐字节比对断言改读 `hdr.conf` 的
  `HeaderText "sma-testpackage-fixed-header"`（`ascii.c` 里 `htchar` 一旦置值就整体替换掉时钟
  行），两臂才存在逐字节可比的前提；比对仍是 `cmp -s` 全文一致，**判定点数 25 一字未减、
  判据未降级**。修后 conan 侧 `G2: PASS`（`conan create` 默认跑 test_package，test() 非零 rc
  必使 create 失败——上一轮正是 `G2: FAIL` 对应 A22 红）。
- W3（`ohc-run finish`）按硬规则排在 commit 之后执行，判决与 `.ci-result.json` 以新 HEAD 为
  准；本文件停在提交态，故 W3 的具体判决行不写在这里（提交态无该日志），交回与 PR 正文从
  `reports/w3-local-ci.log` 复取。

## 4. 测试账

- 上游官方用例 = **0**，六形实测证据逐条写在 `test_package/MANIFEST.yml` 顶部
  （tar 清单 / Makefile 目标只有 sma·clean·install / 无 CI 文件 / 无语料 / 无自测入口 /
  `contrib/spam-graph.pl` 与 `contrib/mailwrapper.sh` 都不是断言型用例）。
- 适配层断言 = **25 个判定点**（标签 A1-A23，其中 A11、A17 各含 a/b）：
  文本进 → 报告出，逐字回读抬头、`Server: mailhost`、榜单条目与计数；
  覆盖 `-h/-c/-C/-o/-p/-F/-f/-O` 与 stdin 通道；`-DUSE_REGEXP` 用
  `EnvelopeSenderFilter ^alice@` 做正反两向断言（`^` 锚点非子串匹配可复现）；
  A23 以"换日志必换报告"自检可证伪性。
- 数字同源：`test_package/test.sh`（打印合计 25）、`test_package/MANIFEST.yml`
  （`assertion_count: 25`）、本文件三处已对齐；PR 正文与登记表由主窗从提交态复取，须同为 25。
- 未过项：无（A22 根因是跨秒时钟行，已按上法在 harness 侧消除；计数仍 25/25）。

## 5. 能力面（不编造探针）

`sma` 只读普通文本文件，唯一写路径是 `-o <file>`。`fopen` 目标全集（4 处）：
`sma.c:158` 读 `-f` 指定配置、`sma.c:165` 读 `DEFAULT_CONF`（`./sma.conf`，**相对当前目录**）、
`sma.c:261` 写 `-o`、`sma.c:428` 读日志文件参数。全文无 `/proc`、`/sys`、`/dev/`、
`socket()`、`ioctl`、`getifaddrs`、`getloadavg`，无缓存/临时文件写入
⇒ 无 OHOS 能力墙可谈，本轮**未**为其编造 errno 探针。
可复用的环境事实（不是能力墙，只是本机形态）：`/tmp` 只读；`install(1)` 不可用（§2 问题 2）；
conan `test()` 里 `getcwd` 不可靠（`pwd` 返空 ⇒ test.sh 工作目录取 `${TMPDIR:-$HOME/tmp}`，不用 `$(pwd)`）。

## 6. 路径 B 判定

- 适配路径：**A（直接适配 + 1 枚可移植性补丁，补丁数 1）；**路径 B 判定 = hit（E491）****。
- 使用知识库：
  - `knowledge/graph/E335.kv:41-43`（改用发行版 distfiles 镜像分发 tarball）——
    与机制同族：官方发布位失效 ⇒ 换 distro distfile 权威缓存；
  - `knowledge/drafts/DRAFT-13501-libamrnb-3gpp-waf-uppercase-url.kv:34`、
    `knowledge/drafts/DRAFT-8425-libusbsio-2.1.13-upstream-deleted-equivalent-source.kv:10`
    （死源时按"发行版缓存 + 独立公布哈希交叉核对"）；
  - `knowledge/graph/E491.kv:21,33-35`（tentative definitions / 禁用全局 `-fcommon`；
    本包按 `:21` 出 extern + 单点定义补丁，取舍见 §2 末）。
- 知识库扩展：**无新增草稿**。四范围同批扫过
  （`knowledge/graph/*.kv`、`index.tsv`、`knowledge/drafts/*.kv`、`archives/**/notes.md`），
  检索式按机制特征词（`pkgsrc|distfiles|MASTER_SITES|netbsd`、
  `fcommon|duplicate symbol|tentative definition`、`install`、`regex.h`）；
  取源机制已被 E335 + 两枚草稿覆盖 ⇒ 判 hit、不重复主张知识；
  `regex.h` 与 `USE_REGEXP` 四范围 0 命中，但那是"本平台不触发"的死代码事实，不构成本包撞到的机制，
  故不为其开草稿（不为凑知识位编造）。
- 关联 Issue：不适用（路径 B 判定 = hit ⇒ 无【知识库扩展】Issue）。机制一句话：
  **上游官方发布位失效（页面在、tarball 301 回首页）时，改用 pkgsrc/NetBSD distfile
  权威缓存，并用与 Debian `.orig` 的 `diff -rq` 零差异 + 独立公布的 MD5 做交叉验证后换源。**

## 交付物

| 文件 | 说明 |
|------|------|
| `archives/s/sma/README.md` / `manifest.yaml` / `commands.json` | 软件级三件套（`commands.json` 含 `versions."1.4".ref = sma/1.4`，`type: tool`） |
| `1.4/conanfile.py` | 裸 Makefile 配方：`basic_layout`、`export_conandata_patches` +`apply_conandata_patches` 两条字面判据（1 枚 portability 补丁，非空操作）、编译器取`tools.build:compiler_executables`（R33）、`-j1`（R9）、不跑 `make install`、CFLAGS 内无全局兼容开关 |
| `1.4/conandata.yml` | 单一真相源：pkgsrc distfile URL + 实测 sha256 + 取源三方对撞 |
| `1.4/patches/0001-sma.h-sma.c-globals-extern.patch` | 93 条暂定定义 → `SMA_G`（extern 声明 + `sma.c` 单点定义），247 行 / 3 hunk |
| `1.4/manifest.yaml` | 版本级（`build_system: makefile`、`dependencies: []`、`patches_applied` 列出 0001 补丁） |
| `1.4/test_package/{conanfile.py,test.sh,MANIFEST.yml}` | 25 个判定点 + 上游 0 用例六形声明 |
| `1.4/notes.md` | 本文件 |

## 注意事项
1. 版本串一律 `1.4`，未做归一化；包名 `sma`、目录 `archives/s/sma/1.4`、分支 `feat/sma-1.4` 一致。
2. 全局兼容开关已按 `E491:33-35` 撤下，改走 `:21` 的 extern + 单点定义补丁；补丁属
   portability（只改声明形态），不动上游功能逻辑。
3. A22 已定性为跨进程比对遇到秒粒度时钟行（harness 缺陷），修法是给三条跨进程断言固定
   `HeaderText`；**判据与 25 的分母都未动**，时钟行以外的内容仍逐字节比对。
4. 上游站点若哪天恢复发布位，`conandata.yml` 应换回官方 URL ⇒ recipe revision 变，
   旧验证证据全部作废，需重跑门禁。
---

**编译结束**: 2026-09-25 10:13
**最终状态**: built
