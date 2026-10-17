# maloc 1.5 — HarmonyOS PC 适配记录

## 结论（截至本棒）

补丁与配方已就位。第 2/3 棒的两处卡点（F-a 壳不匹配、F-b config.status 临时目录拒写）已在本棒按 E386 capability-tested 口径与 E011/E114 家族先例在**配方层**解决，conan create 与 conan-verify 均已跑通（见"第 4 棒构建段"节）；本文只登记一手实测读数。

## 取源

- 官方址（唯一）：http://www.fetk.org/codes/download/maloc-1.5.tar.gz — HTTP 200，794138 字节
- 实物 sha256（本棒 sha256sum 复算：设备缓存件 ~/tmp/uc2/z64-maloc/m-http.tar.gz 与重新 curl 下来的 ~/tmp/uc2/z64-maloc/pf7-r10/http-fresh.tar.gz 两值相同，已写入 conandata.yml 与本级 manifest.yaml）：58e1197fcd4c74d3cbb1d39d712eb0a3c5886a1e6629f22c5c78ce2bac983fc0
- **https-only 不可得**：https://fetk.org/codes/download/maloc-1.5.tar.gz 与 https://www.fetk.org/codes/download/maloc-1.5.tar.gz 均返回 000（证书 CN 不覆盖 www.fetk.org，TLS 握手无法完成）。本包唯一官方址就是明文 http，未使用任何镜像或搬运址。
- preflight 的 PF7 源 URL 分类器对这条官方原址返回原文：**明文 http 源（R39 要求 https）**。这是上游事实与规则要求的冲突，不是取源手法问题；是否走例外由主理与用户定调，本棒未注入 --no-preflight、未关闭 OHC_PREFLIGHT。

## 版本串与许可证事实

- configure.ac:100 是 AC_INIT(maloc, 1.0, mholst@math.ucsd.edu)，configure.ac:126 的 AM_INIT_AUTOMAKE(maloc, 1.0) 处于注释状态；而归档目录、分支、conanfile version 与 tarball 名均为 **1.5**。版本串未做归一化，如实保留 1.5，差异在此登记。
- 许可证一手证据：src/aaa_inc/maloc/maloc.h 头注释写明 Copyright (C) 1994-- Michael Holst 与 GNU Lesser General Public License version 2.1 or (at your option) any later version → LGPL-2.1-or-later；maloc.spec:39 的 Copyright: GPL 是上游粗写，按库头取 LGPL-2.1-or-later。

## 旧式 config 脚本与 OHOS 锚点（本棒一手实测）

判别口径取自 DRAFT-E564 的 approach 段，实测读数：

```
grep -c "^GUESS=" config/config.guess            → 0      （旧式 echo 风格）
grep -c ":Linux"  config/config.guess            → 24
grep -n "aarch64" config/config.guess            → 零命中（表内没有 aarch64 分支）
sh config/config.guess                            → rc=1   unable to guess system type
sh config/config.sub aarch64-unknown-linux-ohos   → rc=1
  原文：Invalid configuration `aarch64-unknown-linux-ohos': machine `aarch64-unknown-linux' not recognized
设备 uname：-s = HarmonyOS，-m = aarch64，UNAME_RELEASE = HongMeng Kernel 1.12.0
```

四处锚点落地结果（一手；本补丁实测 40 行 / 4 个 hunk / 新增 6 行、删除 2 行）：

1. config.sub 锚点 1（maybe_os kernel-libc 行，锚 knetbsd*-gnu* 与 netbsd*-gnu* 那一行）→ **hit: True**，插入 linux-ohos* 分支。
2. config.sub 锚点 2（basic os 列表 -linux-gnu* / -linux-newlib* / -linux-uclibc* 行）→ **hit: True**，追加 -linux-ohos*。但**仅这两处仍不够**：config.sub 的 machine 别名表（约第 1294 行）里那一条 | z8k | z80 | ... 不含 aarch64，同一命令仍报上面那句 Invalid configuration（这正是 notes 开头第 29 行所抄的报错）⇒ 必须补第 4 处锚点把 aarch64 加进该别名；四处齐后 sh config/config.sub aarch64-unknown-linux-ohos → 输出 aarch64-unknown-linux-ohos，rc=0（未打补丁时同一命令 rc=1）。
3. config.guess 的锚点**必须改**：第 1 棒推给设备的 build-r3.sh 用 "^case $1 in$" 作锚 → 打印 hit: False（config.guess:70 的 case $1 in 带前导空格且属另一个函数）；DRAFT-E564 记的 aarch64:Linux:*:*) 分支在本包 config.guess 里不存在（上面 grep aarch64 零命中）。本棒改在 config.guess 主 case 行（第 144 行 case "${UNAME_MACHINE}:${UNAME_SYSTEM}:${UNAME_RELEASE}:${UNAME_VERSION}" in）之后插入 aarch64:HarmonyOS:*:*) 分支回显 UNAME_MACHINE-unknown-linux-ohos，实测：
   - sh config/config.guess → 输出 aarch64-unknown-linux-ohos，**GUESS_RC=0**（打补丁前同一命令 rc=1）
   - 四处锚点合成 40 行补丁（wc -l 实测；4 个 hunk，新增 6 行、删除 2 行）： patches/0001-oldstyle-config-scripts-ohos-anchors.patch，在净解包树上 patch -p1 --dry-run → **rc=0**（config/config.guess 与 config/config.sub 两个文件均 patching 成功）

配方侧同时按 aalib/1.4p5 先例显式传 --build=aarch64-linux-ohos --host=aarch64-linux-ohos，使 configure 不依赖本机猜测。

## 依赖（W0）

preflight_check.sh maloc/1.5 报"未找到依赖声明"，maloc 无 conan 侧依赖 → 无"依赖未发布"风险，未做 block。

## 构建段（第 2 棒记录）：被设备闸阻断的一手读数

取槽姿势：sh ~/tmp/uc2/build-slot.sh --kind short --mem 2500 --wait 5400 -- sh ~/tmp/uc2/z64-maloc/build-r3.sh
槽位取到：SLOT_OK 07:38:49（机动槽空闲，长杆 0/2 · 机动 0/3）；随后 build-r3.sh 内置闸循环，逐次原文在设备 ~/tmp/uc2/z64-maloc/r4-slot2.out：

```
GATE_TRY=0  rc=1 GATE_FAIL:MemAvailable=5517MB < 6000MB（可用内存不足，fork 可能失败） load=20.466 PSI_full=avg10=74.99
GATE_TRY=5  rc=1 MemAvailable=5353MB
GATE_TRY=14 rc=1 MemAvailable=5365MB
```

未调门槛阈值、未加 --no-preflight、未用 pkill。configure / make / make install 三步因此**未执行**，conan-verify 与 W3 未取。第 1 棒留下的 make -n check 与 make check 原文属 configure 失败后的连锁报错，本棒不采信，也不据其下"上游无测试"结论。

### 对话 #1：本棒断点与动作

从第 1 棒断点续做：其 build-r3.sh 自述的三处锚点（指该脚本，非本补丁最终形态的 4 个 hunk）里 config.guess 那处未命中（上面第 3 点），本棒用主 case 行重定锚并实测通过；随后进入取槽与 gate 退避，20 次内未过闸，构建段未执行。


### 对话 #2：上游测试清点（净解包树实测；make 侧两式本包未实跑，统一口径见 :83 与文末棒6）

- 命令与读数（设备侧 find/tar/grep 于 ~/tmp/builds/maloc-1.5.orig 与 ~/tmp/uc2/z64-maloc/m-http.tar.gz）：
      tar tzf m-http.tar.gz | wc -l                     = 312 条
      find . -type f | wc -l                            = 253 个文件
      find . -iname test* -not -path */CVS/* | wc -l    = 1
      find . -type d -iname res | wc -l                 = 0
      find . -iname *RUNTEST* | wc -l                   = 0
      ls -d tests（find -type d -name tests | wc -l）    = 1
      grep -rn TESTS --include=Makefile.am | wc -l      = 0
      grep -rn noinst_PROGRAMS --include=Makefile.am    = 4 行

- noinst_PROGRAMS 一手原文（4 行）：
      tools/tests/aloc/Makefile.am:40:noinst_PROGRAMS  = goc
      tools/tests/psh/Makefile.am:40:noinst_PROGRAMS  = govmpi govcom
      tools/tests/vsh/Makefile.am:40:noinst_PROGRAMS  = go
      tools/tests/zfence/Makefile.am:40:noinst_PROGRAMS  = eftest tstheap

- 读法：上游只把 6 个 noinst 测试程序放在 tools/tests/ 下，全树 Makefile.am 里 TESTS 声明 0 行、无 check_PROGRAMS、无 res 语料目录，automake 的 make check 因此没有登记用例。本包未实跑 make -n check 与 make check（构建以 conan create 的 configure + make + make install 为止，测试面由 test_package 三条断言在真机执行承担），因此不下「上游无测试」的结论、不虚构分母，只登记上面那批一手读数；同一句话已写进 archives/m/maloc/1.5/test_package/MANIFEST.yml:8 与文末棒6 条，三载体口径一致。

### 对话 #3：交付物清单

- 已就位：conanfile.py（source/generate/build/package/package_info，apply_conandata_patches，OHOS 显式三元组）、conandata.yml（单值官方址 + 实物 sha256 + 补丁登记）、patches/0001-oldstyle-config-scripts-ohos-anchors.patch（实测 40 行 / 4 个 hunk / 新增 6 行、删除 2 行，patch -p1 --dry-run rc=0；同一读数见 :33 与 :39，本行此前漏改一处载体）、test_package 四件（main.c / conanfile.py / CMakeLists.txt / MANIFEST.yml，3 条断言）、软件级 README.md + manifest.yaml。上游 tools/Makefile.am:40 的 bin_PROGRAMS = malocbridge 未构建、不随包提供：本包只有 lib/libmaloc.a + include/maloc/*.h、无 bin/，cpp_info.bindirs 为空，故按 R38 纯库包不保留软件级 commands.json（该件已删，判据与原字节备份见 :113 与 :114，本节不重复论述）。
- test_package 断言一手出处：VPORTNUMBER 定义在 src/vsys/maloc/vio.h:53（值 14916）；VNULL 定义在 src/base/maloc/maloc_base.h:242（VNULL = NULL）；Vio_start 声明在 src/vsys/maloc/vio.h:176（VEXTERNC void Vio_start(void)），上游 malocbridge 自己在 tools/main.c:83 首调该函数。三条断言已在真机 conan create 的 test_package 里执行且全 PASS：执行读数一手出处为 :96（CREATE_RC=0）与本 PR 内 reports/w3-local-ci.log:782（L1_RESULT=pass: test_package executed）；本行前半段是断言的符号定义出处。
- 未做（第 2 棒当时的诚实登记，现已被后续棒次推翻并改正）：ohc-run.py conan-verify、finish maloc 1.5 built、W3 三值三项**均已取到**——conan-verify 于 2026-09-26 09:06 出 reports/conan-verify-report.md:3「**Verdict**: PASS」；W3 于 09:08 出 reports/w3-local-ci.log（62093B、mtime 09:08:39）与 .ci-result.json（step=W3_local_ci、exit_code=0），判决与互锁读数原文见 :96，本节与其互相指认、不留矛盾。⇒ reports/ 目录不空，且两份证据件已随本 PR 跟踪；packaging/ 目录仍空（纯静态库包无打包产物）。本棒未提交任何点前缀状态件（.ci-result.json 等永不入 PR）与运行期 .so。

- **适配路径**：路径 A + 路径 B（**hit**，终判由主理拍板并已入登记表）——A＝conan 配方 + 上游旧式 config.guess/config.sub 的 OHOS 锚点补丁 + 配方层 CONFIG_SHELL 与 config.status 临时目录绕行；B＝复用池内既有条目，本 PR 不新增知识条目、不交草稿对、不使用知识前缀
- **使用知识库**（条目号与行号均为本棒在 B 机 worktree 以 awk/sed 对当前原文实取，非转抄）：knowledge/graph/E011.kv:8-12（error_signature 含「cannot create.*subs[0-9]*\.awk.*Permission denied」）、:16-20（match_keywords）、:22-30（root_cause：HMDFS UID 重映射，29-30 为 setgid 02700）、:40-41（rec_approach edit-umask-in-configure）、:75-91（fallback 段，86 行 mktemp 换 mkdir -p、88 行 umask 000）；knowledge/graph/E052.kv:12（「can't create \./confXXXXXX/subs1\.awk: Permission denied」）、:17、:20、:26-28（rec_approach modify_tmpdir）；knowledge/graph/E386.kv:9（title）、:24-28（verification_cmd 的 capability 探测口径）、:32-39（rec_description，**36 行原文「Set CONFIG_SHELL and SHELL for」**）；knowledge/drafts/DRAFT-libftdi-0.20-cmake-vs-autotools-and-libusb-config-shim.kv:16（error_signature 逐字含「print: command not found」）、:19-23（match_keywords 含 ECHO、print -r --、ksh builtin、CONFIG_SHELL）、:37-40（root_cause 第 (3) 条）；knowledge/drafts/DRAFT-E564-oldstyle-config-guess-ohos-reanchor.kv:13（match_keywords 含「双锚点」；条目号定位另见其 :7 的 id 行）、:17-25（GUESS= 判别与 config.sub 双锚点法，:20-22 为锚点 1/锚点 2 原文）；knowledge/graph/E007.kv:8-10；knowledge/graph/E072.kv:5、:13-14、:18-25
- **知识库扩展**：**未扩展——本 PR 无新增知识条目、无新增草稿对、无扩展 Issue**（路径 B 终判 hit）。hit 的理由按机制逐条对到条目与覆盖面：①「HMDFS 上 config.status 以 umask 077 + mktemp 建的临时目录写不进自己（subs1.awk Permission denied）」——症状层与解法层都已被 **E011** 写尽（:8-12 与 :16-20 命中签名与关键词，:22-30 给出 owner 重映射 + setgid 根因，:75-91 连「chmod 改不动 HMDFS 目录权限、改用 mkdir -p 固定目录」这一步都在内，本包 conanfile.py:143-151 就是该形态）；**E052** 覆盖同一症状的识别层（:12 的签名与本包实际报错逐字同串），其 rec modify_tmpdir（:26-28）本包未采用，故只作识别复用、不充当解法依据。②「CONFIG_SHELL/SHELL 必须是 capability-tested 的壳」由 **E386** 覆盖（:36 逐字「Set CONFIG_SHELL and SHELL for」，:24-28 探测口径，:32-39 方案）；本包额外使用的「该壳还得有 print builtin」判据不是新机制——它已由 DRAFT-libftdi-0.20 的 :16 逐字签名 print: command not found、:19-23 关键词（ECHO/print -r --/ksh builtin/CONFIG_SHELL）与 :37-40 根因第 (3) 条记载，属命中在池条目而非扩展。③「pre-2016 旧式 config.guess/config.sub 需手工换锚点」由 **DRAFT-E564**（:17-25）覆盖，三元组识别面与验证面由 **E007**（:8-10）、**E072**（:5,13-14,18-25）覆盖。三条机制没有一条用到「既有条目未记载的另一条解法」，因此不升 create
- **关联 Issue**：无——hit 口径不建「知识库扩展」Issue，本包也没有其它关联 Issue（平台与 Issue 操作归主理，本棒未碰平台）

状态：本棒 gate 与短槽一次放行（gate-r10.log GATE_OK attempt=1，MemAvailable 7772MB，属本棒 gate-r10 轮次读数），conan create 到 CREATE_RC=0（create-r10.log），conan-verify G0/G1/G2/G3 全 PASS 且 VERIFY_RC=0（verify-r11.log）。W3 锚 reports/w3-local-ci.log 现存、已随本 PR 跟踪且对当前 HEAD 有效（2026-09-26 本棒实算）：文件 62093B、mtime 2026-09-26 09:08:39，晚于终点提交 e4669e6d 的 2026-09-26 09:04:28 +0800；[step] 标记 48 条、判决行 8 条且一律带前缀（该件 :23 G0_RESULT=pass、:63 KC_RESULT=pass、:90 JC_RESULT=pass、:781 L0_RESULT=pass: all checks passed、:782 L1_RESULT=pass: test_package executed、:783 L2_RESULT=skip: no bin/ dir、:784 L4_RESULT=warn: dangerous functions in patches、:785 L5_RESULT=pass: lib/ has content；日志内不存在裸 _RESULT= 行，本棒按行首实跑 grep 计数为 0）。.ci-result.json 记 step=W3_local_ci、exit_code=0、timestamp=2026-09-26T09:08:39.392775、log_sha256=e063c018b8ef30af161c7999dced8579621f0610da4100d0f86ae4f35da9880e，与 sha256sum reports/w3-local-ci.log 实算值 e063c018b8ef30af161c7999dced8579621f0610da4100d0f86ae4f35da9880e 同串（互锁成立）；该 json 为设备本地状态件、不随 PR，故此处只抄字段值。runner 日志 finish-r12.log 同为设备本地证据件、不随 PR，其被引两行的原文值已整句抄录在此：「  ✅   ✅ 本地 CI 模拟通过 (日志: /storage/Users/currentUser/qzy/主理-64-maloc-1.5/archives/m/maloc/1.5/reports/w3-local-ci.log)」与「  ✅   ✅ W3 本地 CI 模拟通过」，读者据抄录值即可复核。reports/conan-verify-report.md:3 为「**Verdict**: PASS」（mtime 2026-09-26 09:06:18，亦晚于提交；该件亦已随本 PR 跟踪）。⇒ W3 本地 CI 模拟已取到绿、按已过门登记，最终状态见文末 built 行；本段与 :89 互相指认（:89 旧述「三值未取、reports/ 空」已按上述一手读数改正）。
---

**编译结束**: 2026-09-26 09:06
**最终状态**: built


## 棒4（文档整改）一手锚点补记 2026-09-26
本棒只改文档，未重跑 finish/conan create/conan-verify；下列读数取自盘上既有证据件与补丁件。
- [K-SHELL] E386 口径落地：CONFIG_SHELL/SHELL 绑到"从真实构建目录探测通过"的壳（pwd rc=0、stderr 空、stdout == 构建目录）；/bin/sh 通过且有 print builtin，profile 的 /data/service/hnp/bin/bash 探测失败。
- [K-MKTEMP] E011/E114 家族落地：HMDFS 重映射新建 0700 mktemp 目录的 owner，config.status 写不进自己刚建的目录（subs1.awk）；配方层以模板自带 mkdir + umask 000 取代 mktemp 分支。
- [K-PACKSHAPE] 产物形状：包内仅 lib/libmaloc.a + include/maloc/*.h、无 bin/（本 PR 内 reports/w3-local-ci.log:783 L2_RESULT=skip: no bin/ dir、:785 L5_RESULT=pass: lib/ has content）；上游 tools/ 的 bin_PROGRAMS malocbridge 未建 ⇒ cpp_info.bindirs 为空是如实登记。
## 棒5（交付文本整改）一手锚点补记 2026-09-26

本棒只改交付文本（上面 3+2 四行、本节、以及 archives/m/maloc/commands.json 的 description），未重跑 finish/conan create/conan-verify，未动 conanfile.py/conandata.yml/patches 与 binary/type 字段；下列行号均为本棒在 B 机 worktree 以 awk/sed 对当前原文实取。

- [E129 判定] **不引**。核过 knowledge/graph/E129.kv：它覆盖的是 config.status/umask 077 的症状识别面（:9 error_signature、:14 match_keywords）与 setgid 根因（:17 原文「HMDFS filesystem always sets setgid bit on new directories; umask 077 creates drwx--S--- which blocks even the owner from writing files inside it」），其方案层是 rec_approach sed-replace——把 umask 077 换成 022 且保留 mktemp 分支（:23-25）。本包实跑的解法是「mktemp 分支整体换成 mkdir + umask 000」（conanfile.py:143-151，:135-137 实测记录放宽 umask 无效、模式被强制），与 E129 记载的解法不同；同一机制的症状与解法两面已由 E011.kv:8-12/16-20/22-30/75-91 覆盖，故本包不引 E129，以免同族混引。
- [commands.json 一致性] 该件原 description 把本包对外写成「libmaloc 最小抽象层（对象化 C）附带的 malocbridge 套接字桥接工具」，与实物不符：本包只有 lib/libmaloc.a + include/maloc/*.h、无 bin/（判据见本 PR 内 reports/w3-local-ci.log:783（L2_RESULT=skip: no bin/ dir）与 :785（L5_RESULT=pass: lib/ has content）），上游 tools/Makefile.am:40 的 bin_PROGRAMS malocbridge 未构建，conanfile.py:170 的 cpp_info.bindirs 为空。处置分两步：先把 description 改为如实（见本节末条），再按 R38 整件删除——库形包不保留该件。
- [已决并执行] 纯库包不保留 commands.json。依据：SKILL.md R38「库类型不需要 commands.json」；scripts/ohc/preflight.py:523-525 把「纯库包不应有 commands.json（R38：库误加）」计入 findings；仓内既有形状一致——archives/z/zlib/ 与 archives/l/libftdi/ 的软件级目录只有 README.md + manifest.yaml。CI 侧 ci/conan/build_and_test.sh 的 L0k 对该情形只打 [warn] 不置 L0_FAILED，故不阻塞判决，但仍按成文规则移除。删除不触碰配方目录 archives/m/maloc/1.5（recipe revision 面）⇒ 本轮 W3 证据 e063c018b8ef30af… 不作废。原字节留存在设备 ~/tmp/uc2/z64-maloc/heldout-r14/commands.json.bak（sha256 c35ed65e0c9773bd24a556ee49ca26cd2056ea4800694f5bca58c7850db2660f），未销毁、可原样取回。
## 棒6（独立审计 r1 整改）一手锚点补记 2026-09-26
本棒只改交付文本（本文件、archives/m/maloc/1.5/manifest.yaml、archives/m/maloc/1.5/test_package/MANIFEST.yml 的 description 行），并把盘上既有证据件 reports/w3-local-ci.log 与 reports/conan-verify-report.md 以 git add -f 纳入本 PR（仓内先例口径本窗重算（收口窗 2026-09-27，git ls-tree -r --name-only origin/main 全量、按结尾匹配）：reports/w3-local-ci.log = 17 条路径 / 16 个包根，conan-verify-report.md = 167 条路径 / 164 个包根（此前本行写的『26 份』不可复现，已按实算更正；份数一律给『路径数 + 按包根去重数』两种口径，⛔ 只报分子））。未动 conanfile.py / conandata.yml / patches 等任何构建输入 ⇒ recipe revision 不变、本轮 W3 证据 e063c018b8ef30af…d9880e 不作废；未重跑 finish / conan create / conan-verify / preflight。点前缀状态件（.ci-result.json、.knowledge-done）一律未入 PR。
- [E490 不适用] verify 报 G0 段「⚠️ 已知风险 E490 未在配方中处理」对本包不适用，理由与判据：E490 的处方是 chmod +x 恢复 configure/config.guess 等件的执行位，而本包不靠执行位驱动脚本、一律显式 sh 调用（一手依据：本棒对 archives/m/maloc/1.5/conanfile.py 实跑 grep -c chmod 结果为 0；调用形态读数见本文件 :24-:31 的 sh config/config.guess 与 sh config/config.sub）。故该风险在本包无落点，本棒未为了让它变成「已处理」去改 conanfile.py（那是构建输入，改动作废 W3 证据）。
- [上游测试口径统一，与 test_package/MANIFEST.yml:8 同一句话] 静态读数：全树 Makefile.am 的 TESTS 声明 0 行 ⇒ automake 的 make check 没有登记用例；本包未实跑 make -n check 与 make check（构建到 make install 为止），故不下「上游无测试」结论、不虚构分母，只登记 :68-81 的一手读数（tar tzf 312 条 / find -type f 253 个 / test* 1 / res 目录 0 / *RUNTEST* 0 / TESTS=0 行 / noinst_PROGRAMS 4 行 6 程序）。
- [行号级引用可解析性] PR 可见文本里按行号引用的件，现全部可在本 PR 或仓内解析：archives/m/maloc/1.5/reports/w3-local-ci.log:23,63,90,781-785、archives/m/maloc/1.5/reports/conan-verify-report.md:3、conanfile.py:143-151 与 :170、knowledge/graph/E011.kv、E052.kv、E386.kv、E007.kv、E072.kv、knowledge/drafts/DRAFT-E564-oldstyle-config-guess-ohos-reanchor.kv:13,17-25 与 knowledge/drafts/DRAFT-libftdi-0.20-cmake-vs-autotools-and-libusb-config-shim.kv。仓外设备路径（~/tmp/uc2/z64-maloc/ 下各日志、~/tmp/builds/maloc-1.5.orig、~/tmp/uc2/build-slot.sh 与其产物）不删、不改证据，一律按本地证据件处理：只抄原文值、不再带行号。