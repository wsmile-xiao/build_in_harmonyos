# rs 20200313 适配笔记（HarmonyOS PC / OHOS aarch64）

> 执行：主理-75 窗执行棒（构建主机 = B 机）· 编译日期 2026-09-27
> worktree `~/qzy/主理-75-rs-20200313`，分支 `feat/rs-20200313`，基线 `48d9cee684`
> 本文所有数字与 `manifest.yaml`、`test_package/MANIFEST.yml`、构建日志同源。
> 日志目录（设备侧 B 机绝对路径）：`/storage/Users/currentUser/tmp/uc2/z75-rs/`

## 最终状态

**最终状态**：上游源码零修改、零补丁，`conan create` 通过，13 条上游回归用例全部
真实执行（12 PASS + 1 条上游用 `category:` 自声明"仅 MirBSD 成立"的 SKIP，0 FAIL），
消费者测试 7 组断言全过。**两条 P1 分列**（第 3 轮独立重审计判决 P0=0 / P1=1 / P2=1 / P3=6，
判决件已入本归档 `reports/z75d-audit-result.json`，sha256 前缀 `f50fb400100e`）：
①**许可证字段缺第三项**——独立审计 P1，整改轮 2 已闭环（`conanfile.py:66` 与软件级
`manifest.yaml` 的 license 补齐三项，一手依据见「许可证」节、读数见 §7.9）；②**R39/PF7 取源 URL**——
preflight 源URL硬闸命中，本棒（收口整改棒）已按派发首选路径 (a) 换成上游官方直链闭环，PF7 命中由
2 归 0，端点实测、两树逐文件对账与换源后的门禁读数见 §7.10。【2026-09-28 收尾-8 更正：本句结论已被 **§7.11** 取代——CI worker 对 `mbsd.evolvis.org` 两轮同错 `[Errno 111] Connection refused`（build#63232/CI-022、build#63490/CI-007，/rebuild 未消），取源已换回 `deb.debian.org` 的 pristine `.orig`（curl -L 实测 200/12571B、sha256 与官方件逐字相等、`cmp` 逐字节相同 ⇒ 三方同哈希，**sha256 一字未动**）；PF7 按 R52 记 **P1-已例外处置**，例外署名在 PR 正文。】该判决是**换源前**基线上的读数，
其 P1=1 即上述②；是否复审计由主窗/CIW 决定，本文不作判决声明。

**「零补丁」的准确口径（2026-09-27 整改轮补，消歧）**：**无补丁文件**——
`conandata.yml` 的 `patches: {}`、`patches/` 目录为空、`conanfile.py` 无自定义 patch 逻辑、
上游 7 个文件逐字节未改（本轮重下 tarball 与 conan 缓存实物 56/56 sha256 SAME）；
但**构建期注入 3 个配方侧补充件**，逐个点名：①`compat_defs.h`——经 `-include` 注入
**每一个**编译单元（上游移植开关 + `reallocarray` 声明）；②`compat_reallocarray.c`——
作为**额外链接 TU** 参与最终二进制；③`check_t_runner.py`——作为**测试驱动**在 `build()` 内
执行上游语料。即**无补丁文件 ≠ 无新增文件**。同一口径已校进版本级 `manifest.yaml`
（补丁段 + `shipped_sources` 逐件注释 + `shipped_sources_provenance`）、软件级
`manifest.yaml`（`ohos_adaptation.key_points`）与 `conandata.yml` 取源注释。

**reallocarray 溢出行为的更正（2026-09-27 整改轮实测）**：本包 `compat_reallocarray.c`
与 OHOS musl 运行期实现在溢出时**都返回 NULL**，但 errno 取值**不同**——本实现
`ERANGE(34)`、musl `ENOMEM(12)`（反汇编与同进程双实现探针两条独立证据一致）。原先写在
文件头与本文的「与运行期 musl 版本一致」**不成立，已删**；本包**不承诺 reallocarray 的
errno 取值**。逐条读数与其余三项处置见 §7。

- **适配路径**：路径 A（配方适配）+ 路径 B 判定为**命中既有条目（hit）** ⇒ 本 PR 不附知识
  草稿、不使用知识前缀（曾按 4 项候选机制起草，经读 E287 / E429 / E501 原文复核后判 hit，
  故本 PR 不含草稿）
- **使用知识库**：`knowledge/graph/index.tsv` 按 `strtonum` / `bsd.prog.mk` / `BSDSRCDIR` /
  `check.pl` / `reallocarray` / `openbsd` / `mirbsd` 逐词检索。**主命中 3 条**：
  **E287**（基于上游 fuzzin 语料的确定性 runner ⇒ 覆盖本包「语料在包内、官方驱动 `check.pl`
  在 mksh 树外，故自备 `check_t_runner.py` 全量执行 13 条」）、**E501**（上游只有 Makefile 时
  直接按源文件清单逐 TU 用 profile 编译器编译并处理链接期运行环境 ⇒ 覆盖本包「BSD make 入口
  在 GNU make 下不可用、配方自备等效编译命令」）、**E429**（引用件是**待审草稿件**
  `knowledge/drafts/E429-draft-8B20.md` 第 19 行与 28-29 行：OHOS `sys/cdefs.h` 无
  `__FBSDID`/`__RCSID`/`__dead2`——本棒实测 `knowledge/graph/index.tsv` 里 E429 命中 0 行、
  `knowledge/doc/E429.md` 不存在 ⇒ 它是尚未入库的草稿，不是既有条目；且其处方（草稿 :43-46 用编译
  参数 -D__FBSDID(x)= 一类宏注入缺失宏）与本包做法（打开上游自带的 `MBSDPORT_H` 钩子取 `rs.h` 内
  `<sys/cdefs.h>` 后备）**同根因、异处方**，本包只引它作同一根因的对照，不称它为入库条目）；**E332**
  （启用上游自带的独立测试 runner）方向一致。`reallocarray` 侧另有 1 条**异型**条目仅作对照
  （`archives/b/bsd-mailx` 的 `#ifdef HAVE_REALLOCARRAY` 与 `confuse` 自带 `reallocarray.c`
  属「上游自带兼容源或条件编译」两型，与本包「上游无兼容源 + OHOS 链接桩缺符号」不同型）
- **知识库扩展**：无（B 判定为命中既有条目，本包不新增机制、不落草稿）
- **关联 Issue**：无（B 判定为命中，未建 Issue）

### 门禁复跑读数（2026-09-27，B 机，主理-75 窗门禁止血子代理）

上一棒交接时正式门禁读数缺失，本轮在 HEAD 4f899cb6f82171157e6fc281f0b5a50c5690378e 上把六步
门禁补齐；下列数字全为该轮设备侧实测，日志在 /storage/Users/currentUser/tmp/uc2/z75z-rs/；
**该表属 HEAD 4f899cb6 那一轮的历史留痕，当前唯一有效门禁读数见 §7.10（§7.8、§7.9 起为历史留痕，不作现行证据）**
配方与上游源码本轮**一字未改**（git diff 只命中本 notes 的文档回填）。

| 步 | 命令 | rc | 判决读数 | 日志 |
|---|---|---|---|---|
| 1 | bash ci/scripts/preflight_check.sh rs/20200313 | 0 | [OK] 预检通过（无依赖需要检查） | z75z-01-preflight.log |
| 2 | python3 scripts/ohc-run.py recipe-search rs | 0 | ⚠️ 无相似配方（语料 6173 条）——首稿走 conan-init 模板 | z75z-02-recipe-search.log |
| 3 | python3 scripts/ohc-run.py conan-verify rs 20200313 | 0 | 文字「配方验证通过」+ 报告 **Verdict**: PASS + rc=0（三一致） | z75z-03-conan-verify.log、archives/r/rs/20200313/reports/conan-verify-report.md |
| 4 | python3 scripts/ohc-run.py finish rs 20200313 built | CLI 2 | EXIT_REASON: finish_success、EXIT_CODE: 0、STEP_FAILED: Step6、失败步骤: step5b 与 step8；.ci-result.json 的 exit_code 为 0、step 为 W3_local_ci（**不是 Step5**） | z75z-04-finish.log、archives/r/rs/20200313/reports/w3-local-ci.log |
| 5 | W4/W5：pre_pr_audit.py generate / check / report | 0 / 1→(--force)0 / **2** | 结论: FAIL，统计: P0=0 P1=1 P2=3 P3=4 | z75z-05-generate.log、z75z-05-check.log、z75z-09-w4-report.log；判决件 /storage/Users/currentUser/tmp/uc2/z75z-rs/z75z-w4-audit-result.json（同名副本 .audit-result.json 落归档目录，被 .gitignore:253 排除，不入库） |
| 6 | python3 scripts/ohc-run.py graph validate | 0 | ✅ All checks passed (169 warnings)，169 条全是他包 E 条目（C13 长尾词、C14 空洞 E429/E479），本包 0 条 | z75z-08-graph-validate.log |
| 附 | run_preflight(base=48d9cee684, head=HEAD)，即 PF1–PF9 CI 前置闸 | — | PREFLIGHT_OK= False，3 条：PF9 路径段数×1 + PF7 源 URL×2（conandata.yml:21、版本级 manifest.yaml:27） | z75z-07-preflight.log |

**读数注脚（不粉饰）**

1. 第 3 步报告里 G4 是「⚠️ 无法找到程序包 ID」、L2/L4/L5 是「⏭️ 跳过（无 cache 路径）」，框架
   仍记 ✅ PASS ⇒ 这四项对本包**没有实际覆盖**（G0 同为「无法识别构建系统，跳过预查询」，
   亦无覆盖）⇒ **本包在 verify 里的实际覆盖仅 G1–G3**，本文与 PR 正文一律按此写，
   不许把 G0/G4/L2/L4/L5 写成有覆盖（2026-09-27 整改轮在新 revision 上复核，结论同型，
   见 §7.5）。功能覆盖实由 build() 内 13 条真实回归 +
   test_package 7 组断言 + 第 4 步 Step5 的 W3 本地 CI 模拟承担。
2. 第 4 步 step5b 红在「manifest.yaml: knowledge_count=8 unreferenced=8」——判据实测在
   `scripts/ohc/check_knowledge_gap.py:63-66`：`knowledge_gained` 块内每个 `- ` 项必须**同一行**带
   `ref:`／`knowledge_ref:`／`reference:` 之一才算已引用（另起行或块外的键无效），`:80` 据
   `unreferenced>0` 判 gap 并返 3。该轮 8 条都没有同行标记 ⇒ step5b 红。**收口续棒
   （2026-09-27）已按该判据给 8 条各补同行 `ref:` 注释**（指向本文对应小节，YAML 取值未变、行数未变），
   复跑实测 `knowledge_count=8 unreferenced=0`＋`✅ 知识完整性检查通过`＋退出码 **0**
   （读数件 `~/tmp/uc2/z75y-rs-close2/ckg-02.txt`）；**本棒未重跑 `conan-verify`/`finish`**——
   `manifest.yaml` 不在导出面（§7.0 实测），recipe revision 未变 ⇒ 现行门禁读数仍是 §7.10，
   07:43 那轮日志里的 step5b 仍是**改动前**的历史读数，是否重跑由主窗定夺。原 §5.4 的
   「92.5% 的包同为红」本轮**未复核**，只复核到 check_knowledge_gap 与全仓 1396 条 draft 待审同框出现。
3. 第 5 步 check 读**仓库根** .ci-result.json，而框架 finish 把该件写在**归档目录**（消费方
   submission.py 也读归档目录）⇒ check 直报「W3 未找到」（rc=1）。本轮用 --force 过闸，并另行核对
   归档件 exit_code: 0 + integrity_hash 4e060d36752f1d3f + log_sha256
   fe4e4e87a46b36cc3af3ed4029fc5777f25080244b510df1d776922e561d69df + w3-local-ci.log 末段
   Success: 1 / Failed: 0；**未**在任意位置手工创建该件（该组哈希同为 4f899cb6 一轮的
   历史留痕，当前值见 §7.10——§7.9 那组亦已被 §7.10 取代）。
4. 第 4 步 Step8 gen_summary 抛 'str' object has no attribute 'append'，SUMMARY.md 未生成（框架把
   该步记 True 后仅告警）。本轮未定位到本包数据与该崩溃的因果。

**本轮独立复算（与前棒表述对账）**

- 上游零修改：本轮**重新下载** tarball（sha256 919215dc…bc3f，与 conandata 声明一致），解包后与
  构建缓存内实物逐文件 sha256 对账，7/7 **SAME**（Makefile、rs.c、utf8.c、rs.h、
  .linked/strtonum.c、check.t、rs.1）。
- 五维账本复算（grep 实测 + 构建日志 + 安装包实跑）：N_static=13、N_registered=13、
  N_executed=13、PASS 12 / SKIP 1 / FAIL 0、N_runner=1、N_consumer=1（N_assertion=7）。语料侧
  计数：^name: 13、^---$ 13、arguments: 13、stdin: 13、expected-stdout: 13、expected-stderr: 0、
  expected-exit: 0 ⇒ 与 §1(c)、manifest.yaml 账本、test_package/MANIFEST.yml 同源一致。
- category 全量核对（本轮新增证据）：check.t 第 140/152/164 行共 **3** 条带 category，分别是
  unicode-3-utf8 取反 !os:mirbsd（本平台适用，PASS）、unicode-3-optu8 正向 os:mirbsd（**唯一被
  SKIP 的那条**）、unicode-4 取反 !os:mirbsd（PASS）⇒ 被跳过的不是取反那两条而是唯一正向的一条；
  §2 表的三条标注与语料逐字相符，分母未缩、跳过项未并入通过。
- 编译告警：grep -ci warning 于 reports/conan-create.log = **0**（与 §4 一致）。
- 不可见字符与行尾：本包 28 个盘上文件按 U+00AD / U+200B / U+200C / U+200D / U+FEFF / U+00A0 /
  U+2011 逐码位扫描 **0 命中**，且 CR = 0。
- ⚠ **与前棒表述不一致处（如实标出，判决由主窗作）**：
  ① 本段上方原写「W4/W5 审计 P0/P1 清零」，本轮复跑为 **P1=1 未清零**（R39/PF7 取源 URL），已就地
     校正该句；
  ② compat_reallocarray.c 自称「溢出 errno=ERANGE…与运行期 musl 版本一致」，本轮按手册页口径判为
     表述存疑（该族实现溢出置 ENOMEM），本机未能定位 libc.a 反汇编复核 ⇒ 记 P2，未据此改码；
  ③ test_results.type 标 official 配自研 runner 的标注口径记 P2（语料官方、驱动自研，已多处披露，
     不判 P0）；
  ④「零补丁」在补丁文件意义上为真（patches 为空、无 patches 目录、上游字节未改），但构建期确有 3
     个配方侧文件参与（manifest.yaml 的 shipped_sources 已列），故补一句消歧：
     **无补丁文件 ≠ 无新增文件**。
- ✅ **上述 ②③④ 已于 2026-09-27 整改轮按实测处置**：② 的定位 libc.a 反汇编本轮做成了
  （结论：musl 置 ENOMEM，故"一致"句删除）、③ 的取值分布本轮查完全仓（`official` 为文档化
  取值 + 主流第一位，字段不改、补 `note:`）、④ 的消歧句已落到 4 个载体；
  另按判决把 `compat_reallocarray.c` 认定为 **OpenBSD ISC 派生码**并四处署名，
  取源自证三向本轮重做。全部读数见 §7。**P1（R39/PF7 取源 URL）当轮按派发指令保持不动**（其「保持
  不动」仅到收口轮为止；换源闭环见 §7.10），本轮只补了披露件（§7.5）。

## 0. 软件与取源

rs 是纯 stdin/stdout 文本矩阵重排工具，MirOS/OpenBSD 血统（源码带
`$MirOS: src/usr.bin/rs/… $` 与 `$OpenBSD: … $`），只用 libc，**无第三方依赖**
⇒ W0/R36 天然满足（`preflight_check.sh rs/20200313` 仍留档）。

- 取源：`https://mbsd.evolvis.org/MirOS/dist/mir/rs/rs-20200313.tar.gz`（上游官方 dist 树；与 Debian pool
  里的 pristine `rs_20200313.orig.tar.gz` 整件 sha256 相同、两树逐文件全等 ⇒ 收口整改棒由 pool 换为官方
  直链闭环 R39/PF7，取证见 §7.10）
- sha256：`919215dc9fe85a27a30bf63d56406cfb503f9fc9820323c4bd3bfe75a6a3bc3f`
  （设备侧两次实测一致：本地件 `~/tmp/rs-probe/rs.tar.gz` 与网络下载件）
- 解包顶层目录名就是 `rs`（不是 `rs-20200313`）⇒ `get(..., strip_root=True)`
- 实物 7 个文件：`Makefile rs.c utf8.c rs.h .linked/strtonum.c check.t rs.1`

### PF7 源URL闸：09-27 按 (a) 换上游官方直链；**09-28 已再次换源，现行见 §7.11**（读数见 §7.10/§7.11）

`scripts/ohc/preflight.py` 的 `_PF7_DEBIAN_HOSTS` 含 `deb.debian.org`，判语是「Debian 下游重打包源」
（`:361` 定义、`:379` 命中、`:643` 汇入 findings、`:654` 返回 `not findings` 即 fail-closed；调用点
`scripts/gitcode_pr.py:293-307`（`:298` 调 `run_preflight`、`:302` 判 `not ok`、`:307` `return None`
⇒ 建 PR 在该咽喉点被中止；本棒按提交态实物复验，该范围内**没有** `exit(1)`，原写法「`:296-312` 咽喉
`exit(1)`」的段号与机制名已就地校正）。本包原取 pool 件，实测取证说明该件**并非
重打包**：

| 取证 | 结果 |
|---|---|
| `rs_20200313-1.dsc` 的 `Format` | `3.0 (quilt)` ⇒ `.orig.tar.gz` 是上游原件，Debian 改动全在单独的 `.debian.tar.xz` |
| `debdir/patches/` 是否存在 | **不存在**（无 patch series，上游 7 文件一字节未动） |
| 维护者身份 | `Maintainer: Thorsten Glaser <tg@mirbsd.de>` —— 即 rs 的上游作者本人（`$MirOS:` 署名者 mirabilos） |
| `.dsc` 声明的 `.orig.tar.gz` 摘要 | `919215dc…bc3f`，与我们核验过的实物逐字一致 |
| 官方发布目录（`debian/watch` / `copyright:5` 点名） | `www.mirbsd.org/MirOS/dist/mir/rs/` —— DNS 可解析（A 62.138.145.52 / AAAA 2001:470:6f:94a::1），但 TCP 80/443 超时（`-4`/`-6`/钉 IP 三法一致）；`git.mirbsd.org`、`cvsweb.mirbsd.org`、`ftp.mirbsd.org` 已不可解析 ⇒ 该域名真不可达 |

⇒ **改判与处置**：原「没有可核摘要的官方 URL 可用」的结论只对了半个域名——作者的 `MirOS` dist
树现已托管在其自家 Evolvis 服 `mbsd.evolvis.org`（路径布局与 watch 点名的一致、目录页列出
`rs-20101029 → 20200313` 全部历史发布、`www.mirbsd.de` 的 301 目标即该主机、`.dsc` 的 `Vcs-*` 亦指向
`evolvis.org`），该件与 pool 里的 pristine `.orig` **整件 sha256 相同、两树逐文件全等** ⇒ 本棒按派发
首选路径 (a) **无损换官方直链**，`conandata.yml:21` 与版本级 `manifest.yaml:27` 同步改 URL（sha256 不动）。
换源后 `_pf7_classify` 对新 URL 返回 `None`、整仓 preflight 的 PF7 命中由 2 归 0（端点实测、两树对账与
门禁重跑读数全在 §7.10）。**不再需要** PF7 的「官方托管例外 + `--no-preflight`」通道；本棒不碰 PR、
不跑 `--no-preflight`，是否让渡仍由主窗/CIW 决定。

### 许可证（三合一，逐文件归属）

Debian 的 `copyright`（上游作者本人撰写）明确写 "This is three-fold"，三项各自点名归属：第 12 行
three-clause BSD 管 `rs.c`/`rs.1`、第 46 行 ISC 管 `utf8.c`/`.linked/strtonum.c`、**第 67 行
"The third (MirBSD) applies to rs.h and the packaging"** 管 `rs.h` 与打包。本轮自己重下
`rs_20200313-1.debian.tar.xz` 复算（http=200、5428 字节、sha256 `960147d1c0de6aa9…29676d9f`，
与该包 `.dsc` 的 Checksums-Sha256 自述逐字相等），未抄前棒读数。

⇒ 字段侧本轮（整改轮 2）由 `["BSD-3-Clause", "ISC"]` 补齐为
`["BSD-3-Clause", "ISC", "MirOS"]`：`conanfile.py:66` 与软件级 `manifest.yaml` 的
`license:` 块列表**两处同步**（入字段，不只入披露）。补第三项的直接依据：`rs.h` 确实编译进
二进制（`rs.c:52` include 它），而它的许可文本两头都不沾——实测 `grep -c "Neither the name"`=0、
`grep -c "Permission to use, copy, modify"`=0、独有词 `sublicence` 命中 1（`rs.h:12`），
既非 BSD-3-Clause 亦非 ISC 措辞；本包 `README.md` 与软件级 `manifest.yaml` 早已自称「三合一」，
字段只有两项与自身表述矛盾（独立审计 P1）。第三项取 SPDX 标识符 `MirOS`（＝SPDX License List
的 "MirOS Licence"，即 MirBSD 那条；Debian 侧用词是 MirBSD，已在 `README.md` 与本节注明）。
三项已同步到软件级 `manifest.yaml`、`README.md` 许可段与版本级 `shipped_sources_provenance`；
版本级 `manifest.yaml` 无 `license` 字段，其许可声明处即 `shipped_sources_provenance`。
字段形态未自创：conanfile 侧列表形态全仓 2 份先例（`archives/m/musepack/r475`、
`archives/v/vte/0.74.2`）、单值 ISC 另有 98 份，软件级 manifest 侧 `license:` 块列表全仓 16 份
先例（如 `archives/a/alacenc`），本轮当场复算；`MirOS` 这个标识符本身全仓**无先例**（本包是
第一次使用）。

## 1. 症状 → 根因 → 最小复现 → 最终方案

### 硬点 (a)：上游构建入口在 GNU make 下不可用

- **症状**：`make` 立即失败，什么都不编译。
- **首条真实错误（原文）**：命令 `cd <src> && make`（GNU Make 4.4.1，
  `/data/service/hnp/bin/make`），退出码 **2**：
  ```
  Makefile:13: *** missing separator.  Stop.
  ```
- **根因**：上游 Makefile 是 BSD make 语法。第 13 行就是 `.include <bsd.prog.mk>`；
  另有两处 BSD 专有：第 7 行 `MKSHDIR?= ${BSDSRCDIR}/bin/mksh`（`${BSDSRCDIR}` 只在
  MirOS 源码树里存在）、第 11 行 `perl ${MKSHDIR:Q}/check.pl …`（`${VAR:Q}` 是 BSD
  的引号修饰符）。
- **最小复现**：解包后在源目录直接 `make`（日志 `gnu-make-first-error.log`）。
- **已试过的失败方案**：
  1. 直接 `make`（GNU make）→ 上面那条错误，不可用；
  2. 把 Makefile 改写成 GNU make 语义 → **否决**：`.include <bsd.prog.mk>` 不是
     一行替换能等效的（它带入一整套 MirOS 构建框架：PROG/SRCS/BSDSRCDIR/install 规则），
     改它等于重写上游构建系统，且会污染 `patches/`；
  3. 找 BSD make（`pmake`/`bmake`）→ 制品仓与 SDK 里都没有，且 `${BSDSRCDIR}`
     仍然不存在，装上也跑不通。
- **最终方案**：**不改上游 Makefile 一个字节**，由 `conanfile.py: build()` 逐编译
  单元直接驱动 clang 后链接。等效性依据：这正是上游作者本人在 Debian 里的做法
  —— `rs_20200313-1.debian.tar.xz` 的 `debian/rules` 在 `override_dh_auto_build`
  里逐字写着：
  ```make
  ${CC} ${CPPFLAGS} ${CFLAGS} -c -o rs.o rs.c
  ${CC} ${CPPFLAGS} ${CFLAGS} -c -o utf8.o utf8.c
  ${CC} ${CPPFLAGS} ${CFLAGS} -c -o strtonum.o .linked/strtonum.c
  ${AR} rc librs.a utf8.o strtonum.o ; ${RANLIB} librs.a
  ${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS} -o rs rs.o -L. -lrs ${LDADD}
  ```
  本配方编译同样的三个上游单元（外加一个 reallocarray 兼容 TU）后直接链接，
  归档目标（`.a` + `-lrs`）与直接列目标文件在单二进制输出上等效
  （rs 只有一处 main，utf8/strtonum 全部符号都被 rs.o 引用，不存在归档语义差异）。
  上游的 `PROG=rs`/`SRCS=rs.c utf8.c` 语义保持：产物名 `rs`、上游源集不变。
- **适用边界**：任何 `.include <bsd.prog.mk>`（含 `<bsd.lib.mk>` 等）血统的
  MirOS/OpenBSD/FreeBSD 用户态小包都适用；但**只适用于 SRCS 很短、没有
  cat/cpp 生成步骤**的包。若上游 Makefile 还依赖 `${BSDSRCDIR}` 下的生成物
  （如 mscan 之于 mksh），必须先确认那个生成步骤是否真在构建路径上，否则等效
  改写会漏依赖。

### 硬点 (b)-1：OpenBSD 专有符号 `strtonum(3)` —— 上游自带源 + 上游自带开关

- **症状**：`rs.c` 六处调用（395/405/417/424/463/470 行），OHOS libc 没有该符号。
- **上游自带的兼容实现**：`.linked/strtonum.c`（75 行，`$OpenBSD: strtonum.c,v 1.8`），
  文件里有两处**可选**钩子：`#ifdef MBSDPORT_H / #include MBSDPORT_H` 与
  `#ifdef DEF_WEAK / DEF_WEAK(strtonum)`。
- **首条真实错误（裸编上游 strtonum.c）**：命令
  `clang -c .linked/strtonum.c -o strtonum.o`，退出码 **1**：
  ```
  .linked/strtonum.c:29:9: error: expected parameter declarator
  __RCSID("$MirOS: src/usr.bin/rs/.linked/strtonum.c,v 1.4 2020-03-13 00:26:12 tg Exp $");
          ^
  ```
  同一条命令还带出两个 `error`（`expected ')'`）与一个 `implicit int` warning。
  **实测与任务书预期不符**（任务书假设"musl 的 sys/cdefs.h 一般给空定义"）：
  用 `#pragma message` 在同一 clang 上实测 OHOS musl 的 `sys/cdefs.h`
  → 输出 `NO __RCSID` 与 `NO DEF_WEAK`，两个宏**都没有**。
- **根因**：`__RCSID(...)` 需要由 `<sys/cdefs.h>` 系的后备宏展开成
  `__IDSTRING(...)` 定义；OHOS musl 不提供，于是 `__RCSID("literal");` 被当函数声明
  解析，字符串实参不是合法形参 ⇒ 语法错误。
- **已试过的失败/否决方案**：
  1. 手写 `strtonum` 替身 → **禁止**（任务书红线，且上游已自带实现，属重复造轮子）；
  2. 造一个假 `sys/cdefs.h` 塞进 include 路径 → **禁止**（假头文件红线）；
  3. 删掉上游那行 `__RCSID(...)` → **否决**：那是上游版权/RCS 标识行，不得删；
  4. `-D__RCSID(x)=`（编译期空展开）→ 实测**能过**（与 `-DNEED_STRTONUM` 同用时
     编译干净），但它绕过而不是使用上游预留的移植机制，且把"上游为什么写这行"
     的信息抹掉了 ⇒ 最终不采用，改走下面 (5)；
  5. 引入 `libbsd`/`libmbsdport` 依赖 → 制品仓无此包，且为一个符号拉一个依赖
     违反"依赖最少化"（R1）。
- **最终方案（用上游自己预留的两个开关，零改源码）**：`rs.h` 里带着
  MirBSD `<sys/cdefs.h>` 的后备定义（实测第 55-80 行：`__IDSTRING` /
  `__COPYRIGHT` / `__RCSID` / `__SCCSID` / `__BEGIN_DECLS` / `__dead`），
  并把 strtonum 的原型包在 `#ifdef NEED_STRTONUM` 里（`rs.h:85-86` 的注释
  就写着 `/* .linked/strtonum.c */`）。于是：
  - 打开 `NEED_STRTONUM` ⇒ `rs.c` 六处调用拿到**正确原型**（`long long` 返回值），
    不再走隐式声明；
  - 打开 `MBSDPORT_H="rs.h"` ⇒ `.linked/strtonum.c` 里的 `#include MBSDPORT_H`
    展开成 `#include "rs.h"`，拿到 `__RCSID` 的后备定义。
  这两个开关正是上游作者在 `debian/rules` 里用的同一对
  （`OUR_CPPFLAGS += -DNEED_STRTONUM`、`-I. -DMBSDPORT_H=\"rs.h\"`）。
  本配方把二者放进 `compat_defs.h`，由 `-include compat_defs.h` 注入每个编译单元
  （放头里而不是命令行：`MBSDPORT_H` 的**取值本身要带引号**，走 shell 命令行会变成
  嵌套引号地狱，`-include` 一次解决，见"踩过的坑"）。
- **纳入 `.linked/strtonum.c` 后是否一次通过**：**是**。加
  `-DNEED_STRTONUM -DMBSDPORT_H="rs.h" -I.` 后，上游三个单元一次性编过并链接成功
  （唯一剩下的问题是下面 (b)-2 的 `reallocarray`，与 strtonum 无关）。
- **适用边界**：`NEED_STRTONUM`/`MBSDPORT_H` 是 rs 本项目 `rs.h` 里的私有约定，
  不可当成通用宏名照搬到别的包；通用形态是"先读上游头文件里的
  `#ifdef NEED_X` / `#ifdef X_PORT_H` 移植钩子，再决定要不要写兼容层"。

### 硬点 (b)-2：`reallocarray(3)` —— OHOS「运行期有、链接期无」型缺口

任务书未列出这一项，是实测新发现的**第二个** OpenBSD 专有符号。

- **症状**：`rs.c:345` 的 `p = reallocarray(elem, newsize, sizeof(*p));` 编译期报
  隐式声明 + 指针赋值错误；补上声明后链接期报缺符号。
- **最小复现与逐环节证据**：
  1. 编译：`clang -c rs.c` → `error: call to undeclared function 'reallocarray'`
     紧跟 `error: incompatible integer to pointer conversion assigning to
     'struct entry *' from 'int' [-Wint-conversion]`（rs.c 里已有
     `#define _GNU_SOURCE`，仍无声明 ⇒ 不是 feature 宏问题）；
  2. 头文件：`grep -rn reallocarray <sysroot>/usr/include` → **零命中**；
  3. 链接桩：`nm -D <sysroot>/usr/lib/aarch64-linux-ohos/libc.so | grep reallocarray`
     → **零命中**（同一命令 `grep -c ' malloc$'` = 1，证明 nm 与文件都可信）；
  4. 只补声明去链接：`ld.lld: error: undefined symbol: reallocarray`
     （`>>> referenced by rs.c ... (getfile)`，另有 3 处引用）；
  5. 运行期 libc：`nm -D /system/lib/ld-musl-aarch64.so.1` → `T reallocarray`
     **确实导出**。
- **根因**：OHOS SDK 的**链接桩** `libc.so` 与 sysroot 头相对运行期 musl 有符号缺口
  （不是平台不支持，也不是交叉编译目标不符）。
- **已试过的失败方案**：
  - `-Wl,-Bstatic -lc -Wl,-Bdynamic`（让链接器从 `libc.a` 取 `reallocarray.o`；
    `nm` 实测 `libc.a` 里有该定义）→ **能过链接但产物一跑就崩**：
    `rs 2 2` 冒烟 rc=139，check.t 13 条**全部** rc=139（signal 11），因为 musl 静态
    片段与动态 libc 混链把 malloc 等内部状态劈成两半。该方案已实测否决，
    并把这条反例写进 `compat_reallocarray.c` 与 `knowledge_gained`。
  - 直接写绝对路径 `libc.a` 进链接行 → 硬编码 SDK 路径，CI worker 上必不一致，否决。
- **最终方案**：随配方导出一个独立 TU `compat_reallocarray.c`，配 `compat_defs.h`
  里的声明。上游源码逐字节未改。
  **该 TU 的性质（2026-09-27 整改轮实测更正）**：它是 **OpenBSD
  `src/lib/libc/stdlib/reallocarray.c` v1.3（ISC，Copyright (c) 2008 Otto Moerbeek）的派生码**
  ——函数体 10 行里 9 行逐字符相同、宏名 `MUL_NO_OVERFLOW` 与判定式同形，唯一有意的代码偏差是
  溢出时 errno 由上游 `ENOMEM` 改为 `ERANGE`（对账读数 §7.2）。行为上它与 OHOS musl 运行期实现
  **只在"溢出返回 NULL"上一致，errno 取值不一致**（本实现 34 ERANGE / musl 12 ENOMEM，
  §7.1 探针 + §7.1 反汇编两条独立证据）。⇒ 原先此处写的「规范语义：溢出则 `errno=ERANGE`
  返回 NULL」与文件头的「与 musl 一致」均已按实测降格，**本包不承诺 reallocarray 的 errno
  取值**（调用点 `rs.c:345` 只判 `NULL`；但 `rs.c:346-347` 的 `err(1, "no memory")` 会把
  `strerror(errno)` 打进退出文案，实测两种 errno 分别得 `Out of memory` 与
  `Result not representable`，差异只在文案，不影响成败与退出码）。把 `ERANGE` 改成 `ENOMEM`
  即可与 musl 完全同构，属行为变更，交主理定夺。走 `export_sources` 而不是 `patches/`，
  因为"新增文件"若做成补丁会让 `refresh-patch --auto` 把它再生成成 new-file patch
  （同 `archives/b/bsd-mailx` 对 `vis.c/vis.h` 的处理理由）。
  产物定义优先于共享库定义 ⇒ 行为确定；将来 SDK 若补齐该符号，两实现的**返回值**一致
  （溢出都给 NULL）而 **errno 不一致**（本实现 ERANGE / musl ENOMEM），"语义一致、不会引入
  差异"这句原话过强，已按实测降格为上述口径（§7.1）。
- **适用边界**：只对"链接桩缺符号但运行期有"这一型成立。判别口径（本包实测流程）：
  ① `nm -D` 运行期 `/system/lib/ld-musl-aarch64.so.1` 有没有该符号 →
  ② 有 ⇒ 补独立 compat TU（**返回值语义**可按手册页，**errno 取值必须实测**——本包手册页写
  ENOMEM、本实现置 ERANGE、OHOS musl 实测 ENOMEM，三者两两不同，见 §7.1）；
  ③ 没有 ⇒ 才是真的平台能力缺失，
  按 `env_unsupported` 口径上报，不要在配方里偷偷造能力。
  **不要**用混链静态 libc 蒙过链接器。

### 硬点 (c)：回归语料在包内、驱动脚本在包外

- **症状**：`check.t` 有 13 条声明式用例，但 Makefile 的 `regress` 目标跑的是
  `perl ${MKSHDIR:Q}/check.pl` —— `check.pl` 属于 mksh 源码树，不在本 tarball 内。
  上游一个用例都不执行 = 不可交付。
- **取证**：Debian 侧同样外挂：`debian/rules` 的 `override_dh_auto_test` 写
  `zcat /usr/share/doc/mksh/check.pl.gz | perl - -s check.t -v -p ./rs`，
  `debian/tests/regress` 同理 ⇒ "runner 在包外"是上游生态的既有事实，不是本包特例。
- **最小复现**：`grep -c '^name:' check.t` = 13；`grep -c '^---$'` = 13；
  `arguments:` 13、`stdin:` 13、`expected-stdout:` 13、`expected-stderr:` 0。
- **最终方案**：随配方导出 `check_t_runner.py`（**N_runner = 1**），按语料约定
  在 `build()` 里真实执行 13 条，`self.run` 使逐条 PASS/SKIP/FAIL 与 SUMMARY 原样
  进构建日志（L1c 要的是执行痕迹）。语料约定（解析器已按此实现并对账）：
  - 记录以单独一行 `---` 分隔，顶层 `key:` 在第 0 列；
  - 块值逐行剥**恰好一个**前导 TAB（否则 `stdin` 里的制表符字段会错位）；
  - `key: !a!b!c!` 里的 `!` 是 **argv/env 分词符**（`!-e!0!5!` → `-e 0 5`）；
  - **唯一的例外**：`category:` 借用开头的 `!` 表达**取反**
    （`!os:mirbsd` = 仅非 MirBSD；`os:mirbsd` = 仅 MirBSD）⇒ 必须为它保留原文，
    否则取反信息被分词器吃掉（这一条本地对账时抓到过，已修）；
  - 断言 = 退出码 0 **且** stdout 逐字节相等。语料含非法 UTF-8 字节 0xFF
    ⇒ 解析与比对全程按 bytes 处理，任何环节做编码转换都会假绿。
- **踩过的坑（如实记）**：第一版解析器把 `category` 也走 `!` 分词，导致
  `!os:mirbsd` 与 `os:mirbsd` 无法区分，三条平台标注用例被误判成同一类；
  本地对账脚本（`parse_corpus` + 逐条打印 category）抓到后改为读 `category_raw`。

## 2. 上游 13 条用例逐条实测结果

设备侧 B 机、本配方编译产物、`check_t_runner.py` 真实执行
（日志＝**本地件** `archives/r/rs/20200313/reports/w3-local-ci.log` 第 **191-206** 行：191-203 是 13 条逐条结果（12 PASS + 1 SKIP），204 `UPSTREAM_CHECK_SUMMARY`，205 `UPSTREAM_CHECK_SKIPPED`，206 `UPSTREAM_CHECK_VERDICT PASS`；行号由收口续棒在提交态对该本地件逐行重取——该件现为 §7.10 换源轮重生成，共 284 行、sha256 前缀 `d599a9b4d157`；此前写的 196-211 属整改轮 2 那件实物，换源重跑后整体前移 5 行，已就地校正），下表与 `test_package/MANIFEST.yml` 同源。此处原指设备侧易失件 `z75-rs/17-cc-final.log`，本轮实测该件 **0 字节**（独立审计 P2），故一律改指本地件。

| # | 用例名 | argv | 结果 | 说明 |
|---|---|---|---|---|
| 1 | debian-650029-e | `-e 0 5` | PASS | 每行一条目 + 宽列对齐（期望 172 字节） |
| 2 | debian-650029-ze | `-ze 0 5` | PASS | 同上叠加 `-z`（期望 64 字节） |
| 3 | debian-668306 | `3 3` | PASS | 上游标题即"Check it doesn't immediately segfault" |
| 4 | debian-706717-r1.10 | `-c 0 2` | PASS | 空字段占位、各行等宽（10 字节） |
| 5 | debian-706717-r1.11-1 | `-c 0 2` | PASS | 末列空（期望含行尾两个空格，逐字节） |
| 6 | debian-706717-r1.11-2 | `-c 0 2` | PASS | 同上但 stdin 末行带尾随制表符 |
| 7 | empty-last-line-1 | `0 2` | PASS | 尾随空行基线 |
| 8 | empty-last-line-2 | `0 2` | PASS | 尾随空格不得造出空行 |
| 9 | unicode-1 | `0 3` + `LC_ALL=C.UTF-8` | PASS | UTF-8 显示宽度（`猫`/`マヌル` 按 2 列） |
| 10 | unicode-2 | `-z 0 3` + `LC_ALL=C.UTF-8` | PASS | 同上叠加 `-z` |
| 11 | unicode-3-utf8 | `-z 0 2` + `LC_ALL=C.UTF-8` | PASS | 非法字节 → `?`；上游标 `category: !os:mirbsd`（本平台适用） |
| 12 | unicode-3-optu8 | `-z 0 2` + `LC_ALL=C.UTF-8` | **SKIP** | 上游标 `category: os:mirbsd`（仅 MirBSD 的 OptU8 层成立）。**已真实执行**：实测 `b'\xff  b\nc  \xc0\x80\n'` 期望 vs 实得 `b'?  b\nc  ??\n'` —— musl 把非法序列渲染成 `?`，与其对立项 #11 的期望正好互斥，#11 已 PASS |
| 13 | unicode-4 | `-z 0 2` + `LC_ALL=C` | PASS | 非 UTF-8 locale 下按字节宽度；上游标 `!os:mirbsd` |

**账本（§10.1 口径）**：`N_static=13`、`N_registered=13`、`N_executed=13`、
通过 12、失败 0、上游自声明平台受限 1（#12，逐项具名附技术原因，不并入"通过"、
不从分母删除）；`N_runner=1`（未被用来替代原子用例数）；
消费者测试 `N_consumer=1`（`test_rs_consumer.py`，`N_assertion=7`）。
通过率表述：**执行项 12/12（受限 1 项具名）；静态全量 12/13 + 1 项上游平台声明**。

## 3. 消费者测试（test_package）7 组断言

`test_rs_consumer.py` 从安装包 `bin/rs` 真实调用，全部为行为断言（不是查文件存在）：

| 断言 | 内容 | 为什么值得测 |
|---|---|---|
| C1 | `rs 3 3` 把 9 字段排成 3×3，逐格内容比对 | 基本功能 |
| C2 | `rs -c 0 2` 空字段仍占位、两行**等宽** | rs 的核心对齐语义 |
| C3 | `rs -e 0 5` 每行一条目、宽列不拆、两行**等宽** | `-e` 与列宽计算 |
| C4 | `rs abc 2` 退出码非 0 且 stderr 含 `invalid` | **strtonum 兼容链路真在跑**（不是"能链接"就算过） |
| C5 | `rs 0 99999999999999999999` 退出码非 0 且 stderr 含 `too large` | strtonum 的 ERANGE 分支 |
| C6 | 5000 行 × 6 字段 → 退出码 0 且**字段多重集合守恒** | reallocarray 扩容不丢不截；混链静态 libc 时这里必 SIGSEGV（回归哨兵） |
| C7 | `LC_ALL=C.UTF-8` 下 `rs 0 3` 三行**显示宽度**相等且逐格内容比对 | UTF-8/wcwidth 链路（用 `unicodedata` 独立算宽度，不用字节长） |

## 4. 构建与门禁读数（设备侧 B 机）

- `CONAN_HOME=/storage/Users/currentUser/tmp/ch/home-rs`（`conan config home` 自证；
  `conan remote list` 含 `ohpcd ... Enabled: True`；`extensions/plugins/compatibility`
  已从模板 home 带入；**未**复制 `p/` 缓存）
- 编译器与 flag：`clang -O2 -std=gnu99 -Wall -Wextra -Wformat -I. -include compat_defs.h`
  （`-std=gnu99` 与上游维护者的 Debian rules 一致：严格 `-std=c99` 会置
  `__STRICT_ANSI__`，musl 的 BSD 可见头被挡掉，reallocarray/strtonum 现场更糟）
- 编译告警：**0**（`-Wall -Wextra -Wformat` 下，四个单元全干净）
- 产物：`bin/rs`（实测 31168 字节）+ `share/man/man1/rs.1`
- 日志与证据（设备侧绝对路径，均在 `/storage/Users/currentUser/tmp/uc2/z75-rs/`）：
  `EVIDENCE-01-findings.md`、`gnu-make-first-error.log`、`01-preflight.log`、
  `02-recipe-search.log`、`04-cc-build.log`、`09-cc-switches.log`、
  `12-cc-decl-only.log`（undefined symbol 证据）、`14-cc-decl-static.log`、
  `reports/conan-create.log`（**本地件**，本棒复算 103 行、grep -ci warning＝0，见 §7.10；
  原设备侧 `17-cc-final.log` 本棒实测 0 字节空文件，已不再作证据）、`18-init-archive.log`、
  `13-cc-bstatic.log`（混链 SIGSEGV 证据）

## 5. 已知限制与未覆盖项

1. `check.pl` 的官方实现未在 OHOS 上做过"逐参数等价性"认证：本包 runner 是按
   check.t 语料约定复写的等价器，断言口径（rc=0 + stdout 逐字节）与上游语料可表达
   的信息一致（语料里没有 `expected-stderr:`/`expected-exit:` 字段，实测计数为 0）。
2. `unicode-3-optu8` 按上游 `category:` 声明记 SKIP（详见 §2 表 #12），不是适配缺陷。
3. 上游无 `--version` / `-V`（`getopt` 串里没有），实测 `rs -V`、`rs --version` 均
   退出 1 并打 usage ⇒ L2 冒烟无法用 `--version`，改由 §3 的真实功能调用做等价验证。
4. `finish` step5b 的 `check_knowledge_gap` 判红属全仓存量矛盾（92.5% 的包同为红，该比例本轮未复核），
   本包不改 manifest 形态去凑绿灯，按交付手册 §11.5.1 口径在 PR「未覆盖的检查」披露。
   **本条对「本包 step5b 仍红」已过期**：收口续棒按 `check_knowledge_gap.py:63-66` 的同行 `ref:` 判据
   给 `knowledge_gained` 8 条补齐引用标记，实测 `unreferenced=0`、退出码 0（详见「门禁复跑读数」注脚 2）；
   补的是**引用标记**、不是清单形态，未增删任何一条知识，也未据此宣称 step5b 在 §7.10 那轮里是绿。

## 6. 交付物清单

| 文件 | 说明 |
|---|---|
| `conanfile.py` | 配方（逐单元 clang 编译 + 链接 + build() 内真实跑上游 13 条回归） |
| `conandata.yml` | 取源与 sha256；`patches: {}`（上游零修改）；取源理由与 PF7 处置（09-27 曾换上游官方直链、09-28 因 worker 拒连换回 pristine `.orig`，现行见 §7.11；§7.10 为历史） |
| `compat_defs.h` | 上游移植开关（`NEED_STRTONUM`/`MBSDPORT_H`）+ `reallocarray` 声明，经 `-include` 注入 |
| `compat_reallocarray.c` | **OpenBSD `reallocarray(3)` 的派生实现**（ISC，来源/RCS 版本/版权人已在文件头署名；函数体 9/10 行与上游同形，唯一有意偏差 errno ENOMEM→ERANGE；实测溢出返回 NULL，errno 不承诺；含"勿混链静态 libc"反例说明） |
| `check_t_runner.py` | check.t 等价 runner（`N_runner=1`），逐条 PASS/SKIP/FAIL + SUMMARY |
| `test_package/conanfile.py` | 消费者测试入口（`tested_reference_str`，按 bindir 定位二进制） |
| `test_package/test_rs_consumer.py` | 7 组行为断言（`N_consumer=1`，`N_assertion=7`） |
| `test_package/MANIFEST.yml` | 上游测试声明 + 13 条具名结果 + 五维账本 |
| `manifest.yaml`（两级） | 软件级/版本级元数据，数字与本文同源 |
| `README.md` | 软件说明 + OHOS 适配要点 + 依赖 + 参考 |
| `commands.json` | CLI 声明（R38/L0k/PF8） |
| `notes.md` | 本文 |
| `reports/`（5 件） | 门禁重生成的 3 件（`conan-create.log` / `conan-verify-report.md` / `w3-local-ci.log`，
均取自 §7.10 现行轮重跑）＋第 3 轮独立重审计判决件 2 件（`z75d-audit-result.json`、
`z75d-w4-report.log`，sha256 前缀 `f50fb400100e` / `9b2ef7c90f93`），为 PR 正文行号引用件
（`.gitignore:96` 默认忽略 `reports/`，本归档按全仓 1786 份既有惯例 `git add -f` 入库） |
## 7. 整改轮实测与处置（2026-09-27，主理-75 整改代理）

起点 HEAD `8df8fb1f32`（门禁复跑判决 P0=0 / P1=1 / P2=3 / P3=4 之后）。本轮**只动措辞与
取证**：不改方案、不改构建结构、不碰登记表、不碰平台、不建 PR。
改动提交：`d7c3be6905`（构建输入与披露件）、本文件的第二枚提交。
证据目录（B 机）：`/storage/Users/currentUser/tmp/uc2/z75z-rs-fix/`，判决无关的原始读数
在其 `E/` 子目录（`E1-libc-symbol-probe.txt`、`E3-openbsd-provenance.txt`、
`E4-fetch-selfproof.txt`、`E4b-download-verify.txt`、`E5-err3-visibility.txt`、
`E6-revision-and-reconcile.txt`、`E7-upstream-url-reachability.txt`、
`A3-test_results-type-distribution.txt`、`probe/`、`probe2/`）。

### 7.0 改动是否作废旧证据（实测，不靠推断）

`conan export` 三遍读数一致：

| 树 | recipe revision |
|---|---|
| 改前（`8df8fb1f32` 的 recipe 文件抽到独立目录导出） | `rs/20200313@ohpcd/stable#ec5b64d8e6b09463b186eebdc0026b47` |
| 改后（当前树） | `rs/20200313@ohpcd/stable#ecac6a0492c1b0f4e85677fadb886e53` |

⇒ **revision 变了，旧 W3/verify 证据整批作废**，本轮已重跑（§7.5）。
**本轮没改一行代码（实测，不靠叙述）**：`compat_reallocarray.c` 截到 `#include` 之后的
**代码部分 sha256 改前改后逐字符相同**
（`a8b5b56d3cf8e565e85bb6eb7ca49fd0704a436fd5170fb64aca51cb4bb0a51f`），变掉的只有注释体
（748 → 2364 字节）；`git diff --name-only 8df8fb1f32 HEAD -- archives/r/rs/20200313/`
只命中 5 个文件 + 3 份 `reports/`，**未碰 `check.t` 语料、未碰上游源码、未碰 test_package**。
⇒ 旧证据是**程序上**因 revision 变化而作废（故本轮重跑），不是行为发生了变化。

导出面实测：缓存 `e/` 目录只有 `conandata.yml` / `conanfile.py` / `conanmanifest.txt`，
`export_sources` 带三个补充件；`reports/`、`__pycache__`、`.ci-result.json`、
`notes.md`、`manifest.yaml`（两级）都**不在导出面内**——改它们不动 revision，
改 `compat_reallocarray.c` / `conanfile.py` / `conandata.yml` 会动。

### 7.1 ① `reallocarray(3)`：把未实测断言换成实测口径（P2/P3）

**符号存在性**（任务 1-a；上一棒称"未能定位 libc.a"，本轮定位到了）：

| 探针 | 命令 | 读数 |
|---|---|---|
| 运行期 libc | `nm -D /system/lib/ld-musl-aarch64.so.1 \| grep -i reallocarray` | `0000000000183258 T reallocarray`（**存在**） |
| SDK 链接桩 | `nm -D <sysroot>/usr/lib/aarch64-linux-ohos/libc.so \| grep -i realloc` | 只有 `T realloc`，**无 reallocarray**；同命令 `grep -c ' malloc$'` = 1（证明 nm 与文件可信） |
| sysroot 头 | `grep -rl reallocarray <sysroot>/usr/include \| wc -l` | **0** |
| 静态 libc.a | `nm <sysroot>/.../libc.a \| grep reallocarray` | `reallocarray.o:` + `0000000000000000 T reallocarray` |
| 反汇编 | `ar x libc.a reallocarray.o && objdump -d`（sha256 `07…`，见 E1） | `bl ___errno_location` → `mov w9, #0xc` → `str w9,[x8]` → `mov x0, xzr` ⇒ **errno=12、返回 NULL**；非溢出分支 `mul` + `b realloc` |
| errno 常量 | 自写 `ec.c` 编译运行 | `ENOMEM=12 ERANGE=34` |

**行为实测**（任务 1-b：两个实现同进程并跑，各自打印 `/proc/self/maps` 归属，排除符号遮蔽）：

| 实现 | 解析地址与归属 | 3 组溢出（2^40×2^40 / SIZE_MAX×2 / 2^32×2^32） | 正常 16×8 |
|---|---|---|---|
| 本包 compat TU（编成 `libcompat_ra.so` 后 dlopen） | `0x5bcc0017ac` ∈ `r-xp …/z75z-rs-fix/probe2/libcompat_ra.so` | 3/3 `ret=NULL errno=34 ERANGE`（`Result not representable`） | `ret=NONNULL errno=0` |
| OHOS musl 运行期实现（`dlsym(RTLD_DEFAULT, "reallocarray")`） | `0x5b4a89d258` ∈ `r-xp /system/lib/ld-musl-aarch64.so.1` | 3/3 `ret=NULL errno=12 ENOMEM`（`Out of memory`） | `ret=NONNULL errno=0` |

⇒ **两个实现只在"溢出返回 NULL"上一致，errno 取值不一致**（本实现 ERANGE=34 / musl ENOMEM=12），
与反汇编独立吻合。另测 `err(3)`（E5）：`./errprobe 12` → `no memory: Out of memory`、
`./errprobe 34` → `no memory: Result not representable`（两者 rc=1）⇒ 调用点 `rs.c:345`
的控制流只判 `NULL`，但 `rs.c:346-347` 的 `err(1, "no memory")` 会把 `strerror(errno)`
拼进退出文案，所以 errno 差异**影响文案、不影响成败判定与退出码**。
据此把文件头与本文的措辞降格为实测得到的那部分（原文→新句见 §7.6）。
`ERANGE`→`ENOMEM` 是行为变更，超出本轮授权，留主理定夺（§7.7-1）。

### 7.2 ①-d 出处与许可：判定为**派生码**并四处披露

- 抓取上游原件：`https://raw.githubusercontent.com/openbsd/src/master/lib/libc/stdlib/reallocarray.c`
  → HTTP 200 / 1387 字节 / sha256
  `813952c9ae8a0d699d86024e4d1b9ec23efb762a6064fb5fe2592c420b509348`；
  文件头 `/* $OpenBSD: reallocarray.c,v 1.3 2015-09-13 08:31:47 guenther Exp $ */`、
  `Copyright (c) 2008 Otto Moerbeek <otto@drijf.net>`、**ISC 许可**原文在件内。
- 函数体逐行对账（位置对齐）：OpenBSD 10 行 vs 本实现 10 行，**9/10 逐字符相同**；
  唯一差异 `- errno = ENOMEM;` / `+ errno = ERANGE;`。宏名 `MUL_NO_OVERFLOW` 同名，
  阈值写法 `sizeof(size_t) * 8 / 2` 与上游 `sizeof(size_t) * 4` 数值相同；
  上游另有 `DEF_WEAK(reallocarray);` 本实现未沿用（OHOS musl 不定义 `DEF_WEAK`，硬点 b-1 实测）。
- 手册页：`https://man.openbsd.org/reallocarray.3` → HTTP 200 / 40781 字节，
  正文 `ENOMEM` 命中 2 次、`ERANGE` 命中 **0** 次 ⇒ 上一棒"该族实现溢出置 ENOMEM"成立。
- **结论：构成派生码，不是"独立实现"**。披露已落到四处：`compat_reallocarray.c` 文件头
  （来源 + RCS 版本 + 版权人 + ISC + 唯一有意偏差 + 实测行为）、版本级 `manifest.yaml` 新增
  `shipped_sources_provenance`（三个补充件逐个披露，含 `compat_defs.h` 与
  `check_t_runner.py` 的来源说明）、软件级 `manifest.yaml` 增加同口径 key_point、
  本文 §6 清单行与 §7.6。⚠ `conanfile.py` 的 `license = "BSD-3-Clause"` **该轮未动**（§7.7-2）。
  ⚠ 该「未动」只到整改轮为止：收口轮追加 ISC、整改轮 2 再补 `MirOS`，现行是 `conanfile.py:66`
  的三值列表 ⇒ 本句不作现行许可读数，现行归属见「许可证」节与 §7.10。

### 7.3 ② 「零补丁」措辞消歧（P3）

结构证据（本轮）：`patches/` 目录存在但**为空**；`conandata.yml` 解析后 `patches = {}`、
`sources` 1 条且 url/sha256 与声明逐字相同；`conanfile.py` 内 `grep -n "patch("` **0 命中**
（只有 `apply_conandata_patches` / `export_conandata_patches` 两个通用调用）。
⇒ 字节级"上游源码零修改"为真，但**无补丁文件 ≠ 无新增文件**：构建期确有 3 个配方侧补充件
参与——`compat_defs.h`（经 `-include` 注入**每一个**编译单元）、
`compat_reallocarray.c`（**额外链接 TU**）、`check_t_runner.py`（**测试驱动**）。
该口径已统一写进 4 个载体：本文「最终状态」段新增口径、`conandata.yml` 取源注释、
版本级 `manifest.yaml` 补丁段 + `shipped_sources` 逐件行内注释、软件级 `manifest.yaml`
`ohos_adaptation.key_points`。

### 7.4 ③ `test_results.type: official` 的取值口径（P2）——**不改字段**

- 文档化枚举：`knowledge/operations/build-systems.md` §9.4
  `type: official  # official | manual | skipped`（没有第四值；
  `docs/TEST_QUALITY_SPEC.md` 内 grep `official` 0 命中）。
- 全仓实际用值分布（**收口整改棒第三次独立重算**，基线 = 本分支换源后的 HEAD `5133d39bfb`；
  逐档脚本与 26 份「首词≠YAML 值」清单见 `~/tmp/uc2/z75c-rs-close/E2-dist-yaml.txt`）：
  `archives/*/*/*/manifest.yaml` 共 **7467** 份，其中 **992** 份带顶层 `test_results:` 块；块内第一个
  非注释 `type:` 取值按 **YAML 标量语义**（引号包裹取引号内；裸值截到未加引号的「空格+#」行内
  注释）排行 **`official` 183**、**`manual` 142**、`passed` 45、`consumer` 26、`conan-verify` 25、
  **`upstream` 15**、`explicit` 13、`passed_with_exclusions` 13，其余长尾；另有 **258** 份块内无 `type:`
  键、**1** 份写成 `type: ""` 空串（合计 259 份无有效取值）⇒ 有有效取值的分母 = 992−258−1 = **733**。
  本节原记的 `manual` 145 / `upstream` 17 与前一轮的 991/182/140/257 都不是"不可复现"，而是**另一套
  取值规则**，两处成因本棒已逐件定位：
  ① 把值**截到首个空白词** ⇒ 145/17，差异件恰 5 份：`archives/f/fcheck/2.7.59`（manual + realmachine）、
  `archives/z/zig/0.16.0` 与 `0.16.0.1`（manual + OHOS runner）、`archives/c/ccls/0.20250306.8`
  （upstream + test_package）、`archives/m/mstch/1.0.2`（upstream + consumer）；
  ② 旧扫描用严格锚点 `^test_results:\s*$` + 不归一引号 + 不剥行内注释 ⇒ 991/182/140：严格锚点漏掉
  同行带注释的 `archives/b/box2d/2.4.1`（本棒实测该行是 `test_results:  # Windows host 与 …`，
  故 992 而非 991），不归一引号漏掉 `archives/s/scalapack/2.2.3` 的 `type: "official"`（本棒实测该行
  原文如此，故 official 183 而非 182）。⇒ 各套口径**自身可复现**，属口径分歧，不作造假认定；
  本条以 YAML 语义口径为唯一现行（两套口径下 `official` 均居第一位，§7.4 结论不变）。
  ⇒ `official` 既是**文档化取值**又是**既有具体取值里的第一位**，不是自创枚举。
- 处置：**保持 `type: official`**，在版本级 `manifest.yaml` 的 `test_results` 下补
  `note:` + 4 行注释，明确 `official` 描述的是**用例语料来源**（13 条全部来自上游 tarball
  自带的 `check.t`，逐字节未改），而**执行驱动在配方侧**（`check_t_runner.py`，
  `N_runner=1`，因上游官方驱动 `check.pl` 属 mksh 源码树、不在本 tarball 内）；
  本文 §5.1 既有的等价性披露保持不动。

### 7.5 ④ 取源自证（本轮**重做**，未抄上一棒读数）+ 门禁重跑读数

**（本节表格是整改轮 revision 的历史留痕；配方文件在收口轮与其后的换源整改轮再改，
当前唯一有效读数见 §7.10。下文「三向同哈希」是以 Debian pool 件为被测实物做的：自收口整改棒换成
上游官方直链后，pool 址只作版本与摘要核验的旁证，不再是取源位——现行取源见 §0 与 §7.10。）**

**三向同哈希**：

1. HTTP 一次探测：`curl -I https://deb.debian.org/debian/pool/main/r/rs/rs_20200313.orig.tar.gz`
   → `HTTP/1.1 200 OK`、`Content-Length: 12571`、
   `Last-Modified: Fri, 13 Mar 2020 22:22:52 GMT`、`Content-Type: application/x-gzip`；
   `curl -r 0-1023` → `HTTP/1.1 206 Partial Content`、`Content-Length: 1024`、
   `Content-Range: bytes 0-1023/12571`。
2. 摘要逐字相等：完整下载 `http=200 bytes=12571`，
   `sha256sum` = `919215dc9fe85a27a30bf63d56406cfb503f9fc9820323c4bd3bfe75a6a3bc3f`，
   python hashlib 复算 `BYTE_FOR_BYTE_MATCH = True`，与 `conandata.yml:22` /
   版本级 `manifest.yaml:28` 声明值一致；`rs_20200313-1.dsc`（HTTP 200 / 1950 字节）的
   `Checksums-Sha256` 对同一件写同一摘要，其 `Files:` 里 md5
   `cc6a310b7f3bae98ea6296fbee0f85b4` 与本地件 `md5sum` 一致。
3. 树对账：本轮重下解包 `fetch/tree/rs/` 与 conan 缓存实物逐个 sha256 比对 ——
   4 个 source 目录 + 4 个 build 目录，共 **56/56 文件 SAME、DIFF=none**
   （7 个上游文件的基准 sha256：`Makefile 406eeb83…`、`rs.c a818271e…`、
   `utf8.c 0269fcb8…`、`rs.h 83082b58…`、`.linked/strtonum.c 69fedab5…`、
   `check.t 8d1a0e68…`、`rs.1 5007a206…`；全串见 E6）。

**官方上游 URL 本轮再核**（E7）：`http(s)://www.mirbsd.org/MirOS/dist/mir/rs/rs-20200313.tar.gz`
与 `…/cgi-bin/cvsweb/src/usr.bin/rs/` 均 `curl (28) Connection timed out`（25s，http=000）、
`git.mirbsd.org` 为 `curl (6) Could not resolve host` ⇒ "官方站不可达"本轮复现。
⚠ **该结论只对了半个域名，已由 §7.10 改判**：作者的 `MirOS/dist/mir/rs/` 树整体迁到其自家 Evolvis
服，`https://mbsd.evolvis.org/MirOS/dist/mir/rs/rs-20200313.tar.gz` 实测 200 / 12571 字节且与 pool 的
pristine `.orig` 字节级同一 ⇒ 本包「没有可用官方址」的前提不成立，取源已换官方直链（端点穷举见 §7.10(1)）。
顺带实测 `https://sources.debian.org/api/src/rs/20200313-1/` 返回 200（Debian 侧另有可核入口）。
**换源与否当归主理判（以下为本轮当时的状态）**：按派发指令 `conandata.yml:21` 与版本级 `manifest.yaml:27` 的 URL
一字未动（换源会再改 revision，且已有 304+ 份合入先例）。**该「未动」仅到本轮为止**：收口整改棒按派发首选路径 (a)
已把这两处 URL 换成上述官方直链、sha256 一字未动，新 revision 与门禁读数见 §7.10。判据本轮自己开仓复核：`scripts/ohc/preflight.py:385-426`——:396 只收 `conandata.yml`/`manifest.yaml` 两类文件、:407-408 取行内 `url:` 的引号值、:361 与 :379-381 把 `deb.debian.org` 判为 Debian 下游重打包源；软件级 `archives/r/rs/manifest.yaml` 全文没有 `url:` 键（其 :30 是 compat_reallocarray.c 的派生码披露行，:27 现为 check.t 那条 ⇒ 本节原写「:27 是派生码披露行」的行号已过期，收口续棒按提交态实物校正），故第二处命中只可能是版本级 `archives/r/rs/20200313/manifest.yaml:27` 的 `source.url`。

**门禁重跑（顺序：gate → build → conan-verify → finish；改动已先提交）**：

| 步 | 命令 | rc | 判决读数 | 日志（B 机 `~/tmp/uc2/z75z-rs-fix/`） |
|---|---|---|---|---|
| 0 | `sh ~/tmp/uc2/gate.sh --light` | 0 | `GATE_PASS:probe=clang MemAvailable=5983MB … swap余=49104MB … 编译器进程=0` | `G0-gate-light.log` |
| 1 | `python3 scripts/ohc-run.py build rs 20200313` | **2** | 首条真实错误 `❌ 源码目录不存在: <repo>/archives/r/rs-20200313/src` ⇒ `EXIT_REASON: init_build_failed`、`STEP_FAILED: Step1`。该驱动的 Step1 会去搜索引擎取 `rs-20200313.tar.gz`，命中的是 savannah / waterlan 上**另一个同名软件**（与本包 Debian pool 的 MirOS rs 无关）⇒ **本步对本归档不适用**：强行续跑要么改构建结构、要么换错源，两者都超出本轮授权。真实构建由第 2/3 步的 `conan create` 承担 | `G1-build.log` |
| 2 | `python3 scripts/ohc-run.py conan-verify rs 20200313` | **0** | 三一致：文字「✅ 配方验证通过: rs 20200313」+ 报告 `**Verdict**: PASS` + rc=0；G1/G2/G3 真 PASS，G2 实际执行 `conan create …/archives/r/rs/20200313 -pr:h/-pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable` | `G2-conan-verify.log`、`reports/conan-verify-report.md` |
| 3 | `python3 scripts/ohc-run.py finish rs 20200313 built` | CLI **2** | `EXIT_REASON: finish_success`、`EXIT_CODE: 0`、`STEP_FAILED: Step6`、`失败步骤: step5b, step8`（仓库级/工具已知问题，本轮未"顺手修"）；`.ci-result.json` `exit_code: 0`、`step: W3_local_ci` ⇒ **失败步骤不是 Step5 三条**；`integrity_hash ac5c7ff11b049128`、`log_sha256 5db361304fda4425d707ae5cf21bb3df081a908a4042577ad3df5831d0686ea7` | `G3-finish.log`、`reports/w3-local-ci.log` |

**W3 账本读数（新 revision 上重跑）**：
`UPSTREAM_CHECK_SUMMARY N_static=13 N_executed=13 pass=12 skip=1 fail=0`、
`UPSTREAM_CHECK_VERDICT PASS`、`UPSTREAM_CHECK_SKIPPED unicode-3-optu8`、
`CONSUMER_SUMMARY cases=7 pass=7 fail=0`、`CONSUMER_VERDICT PASS`；
`Full package reference: rs/20200313#304cf3207e2b3be61761bad8c8265505:6b129b068851896169fae42d399fa922d239ce8a#28caaf370f0f28cb45fcd83a6497f324`；
create 日志 `grep -ci warning` = **0**。
**账本只准降不准涨** ⇒ 与改前逐项相同：`N_static=13 / N_registered=13 / N_executed=13 /
PASS=12 / SKIP=1`（具名 `unicode-3-optu8`，即唯一 `category: os:mirbsd` 的正向那条）、
`FAIL=0`、`N_consumer=1`（内含 7 组断言）、`N_runner=1`。未缩分母、未把 SKIP 并进 PASS、
未改 `check.t` 语料一个字。

⚠ **verify 实际覆盖的如实口径**：本轮报告与上一棒同型——`G4 ✅ PASS` 实为
「⚠️ 无法找到程序包 ID」，`L2/L4/L5 ✅ PASS` 实为「⏭️ 跳过（无 cache 路径）」，
`G0 PASS` 实为「无法识别构建系统，跳过预查询」⇒ **本包在 verify 里实际覆盖仅 G1–G3**，
G0/G4/L2/L4/L5 五项**均无覆盖**，本文与 PR 正文都不许把这四项写成有覆盖。功能覆盖由
build() 内 13 条真实回归 + test_package 7 组断言 + Step5 的 W3 本地 CI 模拟承担。

### 7.6 本轮改了哪几句（原文 → 新句）

1. `compat_reallocarray.c` 文件头（删表+替换）：
   原「`语义严格按 OpenBSD reallocarray(3) 实现（溢出则 errno=ERANGE 并返回 NULL），
   与运行期 musl 版本一致；上游 rs 源码保持逐字节不动，本文件只是额外 TU。`」→
   新「**溢出行为（B 机本轮实测）**：本实现溢出返回 NULL/errno=34 ERANGE，OHOS musl 运行期
   实现溢出返回 NULL/errno=12 ENOMEM，正常分配两者均非 NULL；两者**只在返回 NULL 上一致，
   errno 取值不一致**，原"与 musl 一致"不成立已删除；**本实现不承诺 errno 取值**（调用点
   `rs.c:345` 只判 NULL，但 `err(1,"no memory")` 会把 strerror(errno) 拼进退出文案，差异仅在
   文案）」，并在文件头新增「实现来源（1-d 披露）」段（OpenBSD v1.3 / Otto Moerbeek / ISC /
   9-10 行同形 / 唯一有意偏差 ENOMEM→ERANGE / 未沿用 DEF_WEAK）。
2. `conanfile.py` 文档串：原「由 ``compat_reallocarray.c`` 按 OpenBSD 语义补一个独立 TU
   （上游源码仍零修改）」→ 新「移植自 OpenBSD 的 ISC 实现（派生码，来源与许可在文件头披露），
   溢出时与 musl 同样返回 NULL（实测），但 errno 取值不承诺（本实现 ERANGE=34，OHOS musl
   ENOMEM=12）。上游源码逐字节未改，但构建期另有 3 个配方侧补充件参与 ⇒ 无补丁文件 ≠ 无新增文件」。
3. `conanfile.py: _cflags()` 注释：原「`-std=gnu99` 与上游维护者 Debian rules 一致：rs.c 需要
   musl 的 BSD 可见头（reallocarray 现场），严格 `-std=c99` 会把它们挡掉」→ 新「与上游 Debian
   rules 一致；**更正**：reallocarray 与 `-std` 无关——实测 OHOS sysroot 的 `usr/include` 全树
   grep reallocarray **0 命中**，gnu99 下同样没有该声明，声明由 `compat_defs.h` 经 `-include`
   提供」。
4. `notes.md` 硬点 (b)-2 最终方案：原「（OpenBSD `reallocarray(3)` 规范语义：溢出则
   `errno=ERANGE` 返回 NULL）」与「将来 SDK 若补齐该符号，本兼容实现语义一致，不会引入差异」
   → 改为实测口径 + 「**不承诺 errno 取值**；"与 musl 一致"原句不成立已删；将来 SDK 若补齐该
   符号，两实现**返回值**一致而 **errno 不一致**，是否把 `ERANGE` 改成 `ENOMEM` 交主理定夺」。
5. `notes.md` 硬点 (b)-2 适用边界：原「② 有 ⇒ 补独立 compat TU（语义按手册页）」→
   「② 有 ⇒ 补独立 compat TU：**返回值语义**可按手册页，**errno 取值必须实测**（本包手册页写
   ENOMEM、本实现置 ERANGE、musl 实测 ENOMEM，三者两两不同，见 §7.1）」。
6. `notes.md`「最终状态」段：新增 7.3 的零补丁消歧口径（逐个点名 3 个补充件 + 4 个载体）。
7. `notes.md` §6 交付物清单：`compat_reallocarray.c` 行改为「OpenBSD `reallocarray(3)`
   的**派生实现**（ISC 来源署名 + 溢出返回 NULL 实测；errno 不承诺；含"勿混链静态 libc"反例）」，
   并新增 `reports/` 行说明三份判决件为正文行号引用件。
8. `conandata.yml` / 两级 `manifest.yaml`：见 §7.3、§7.4、§7.2 的对应披露（URL 与 sha256
   一字未动）。

### 7.7 本轮**未能证实**与留给主理的点（不糊）

1. **`reallocarray` 的 errno 该不该改成 `ENOMEM`**：实测本实现 ERANGE(34) 与 OHOS musl
   ENOMEM(12) 不一致。本轮只删掉不成立的"与 musl 一致"表述、**未改代码**（改常量是行为变更，
   超出"措辞与取证"授权）。**请主理定夺**。（收口轮裁定：**不改** —— 改常量是行为变更，
   且调用点 `rs.c:345` 只判 `NULL`，两实现在"溢出返回 NULL"上一致，本包已声明不承诺 errno
   取值；详见 §7.8 第 1 项（本轮未动函数体与 errno 常量）。）
2. **配方 `license` 字段**：`compat_reallocarray.c` 判定为 OpenBSD **ISC 派生码**后，
   `conanfile.py` 的 `license = "BSD-3-Clause"` 是否要补 ISC（软件级 `manifest.yaml` 的
   `license` 同理）属交付口径变更，本轮**未自行改**，只在文件头 / 两级 manifest / 本文四处
   做了来源与许可署名。（收口轮已按主理指令把 ISC 追加进 `conanfile.py` 与软件级
   `manifest.yaml` 的 license 字段并同步三处措辞载体，见 §7.8 第 1 项。）
3. **G2 与 W3 两次导出 revision 数字不同**（`#ecac6a0492c1b0f4e85677fadb886e53` vs
   `#304cf3207e2b3be61761bad8c8265505`）而 package_id `6b129b06…` 与包 revision `28caaf37…`
   逐字符相同。机理（是否与 `--user/--channel` 引用写法有关）**未查证**，本轮只如实记两组读数；
   实物唯一性由相同的 package_id + 包 revision 支撑。
4. **W4/W5 独立审计本轮未重跑**（不在派发的四步门禁内）⇒ 上一棒的
   `P0=0 / P1=1 / P2=3 / P3=4` **不得当作本轮读数**。本轮只保证被点名的 3 项 P2/P3
   措辞与取证已按实测处置；**P1（R39/PF7 取源 URL）当轮按派发指令保持 URL/sha256 不动**（该「不动」仅到收口整改棒为止：URL 已换官方直链、sha256 仍一字未动，见 §7.10），
   只补了 §7.5 的取源自证与 §7.5 的官方站不可达复核（后一句的前提已在收口整改棒被 §7.10(1) 推翻：
   官方 dist 树迁至 `mbsd.evolvis.org` 且可达，本包取源已改为该官方直链）。
5. **`ohc-run.py build` 对本归档不适用**这一步只核到"首条真实错误 + Step1 会去搜索引擎取
   同名别家软件"两层；**未验证**该驱动是否另有正规模式（`--project-dir` 未试，试它等于改
   构建结构，超出授权）。真实构建证据由 G2 的 `conan create` 与 Step5 W3 承担。
6. **「`-std=c99` 会挡掉 musl 的 BSD 可见头」** 这一原有说法本轮**无法证实**：实测 sysroot
   `usr/include` 全树 `reallocarray` 0 命中，与 `-std` 无关 ⇒ 已从 `conanfile.py` 注释删除。
   未跑 `-std=c99` 反例实验（不必要，且会再动构建输入）。
7. **「混链静态 libc 会让产物 SIGSEGV」** 沿用上一棒实测（本文硬点 b-2、`knowledge_gained`
   第 5 条、`13-cc-bstatic.log`），本轮**未复核**。
8. **`check.pl` 官方驱动与本 runner 的逐参数等价性**仍未认证（本文 §5.1 原口径不变）：
   本轮只复核了语料侧计数与 13 条执行痕迹，未拿 `check.pl` 跑对照。

### 7.8 收口轮（2026-09-27 04:2x–04:40，主理-75 收口代理）：两件事落定 + 该轮 revision 上的门禁读数（已被 §7.10 取代，历史留痕）

**本节是收口轮的留痕，现行门禁读数见 §7.10**：§7.5 表格与首段「门禁复跑读数」表里的哈希/时间戳是
各自那一轮的历史留痕（§7.9 同已被 §7.10 取代）。本节证据目录
`/storage/Users/currentUser/tmp/uc2/z75r-rs-close/`（`E/E1-before-license-and-precedents.txt`
改前实物与先例复算、`E/E2-gate-rerun-readings.txt`、`E/E2b-w3-marker-readings.txt`、
`E/E2c-revisions.txt` 本轮读数），只读取证、不覆盖前棒目录。

1. **许可证补 ISC（实质合规，已改）**：`compat_reallocarray.c` 判定为 OpenBSD
   `reallocarray.c` v1.3 的 ISC 派生码（§7.2 对账）后，**许可声明字段**本轮补齐：
   `conanfile.py:62`（该轮行号；现行 license 已在 :66）由 `license = "BSD-3-Clause"` → `license = ["BSD-3-Clause", "ISC"]`（**当时两项**；
   整改轮 2 再补第三项成 `["BSD-3-Clause", "ISC", "MirOS"]`，见「许可证」节与 §7.9/§7.10）；软件级
   `manifest.yaml` 的 `license:` 同步为三项块列表、`README.md` 许可段与版本级 `manifest.yaml` 的
   `shipped_sources_provenance` 同步（本棒实测：软件级 `manifest.yaml` 现列 BSD-3-Clause / ISC / MirOS
   三项，`README.md` 许可段亦已按三项归属撰写 ⇒ 本行的「两项」是该轮历史动作，不是现行口径）。
   口径：**ISC 在配方侧只覆盖唯一的派生件 `compat_reallocarray.c`**；在上游侧它对应本就属 ISC 档的
   `utf8.c` 与 `.linked/strtonum.c`（Debian `copyright` 三合一判定，撰写者是上游作者本人），
   `rs.c`/`rs.1` 仍 BSD-3-Clause、`rs.h` 与打包仍 MirBSD。字段形态未自创：conanfile 多值**列表形态
   全仓 2 份**（`archives/m/musepack/r475`、`archives/v/vte/0.74.2`）、单值 ISC 另有 98 份、BSD-3-Clause
   单值 488 份；本行原记「软件级 `manifest.yaml` 的 `license:` 块列表 16 份」**与本棒复算不符**——本棒按
   YAML 结构实测（`license:` 之值为列表者）全仓仅 **3 份**：`archives/a/alacenc/1.0`、
   `archives/b/box2d/2.4.1`、`archives/m/musepack/r475`（本包软件级 manifest 取同一形态）。原行未写明
   计数口径，故此处只落本棒实测值、不猜前轮算法；版本级 `shipped_sources_provenance` 实测仍 6 份（未变）。
   **未动**：函数体一字未改，溢出 errno 仍 `ERANGE`（§7.7 第 1 项裁定不改）。⚠ 实读新发现并上报：该文件头
   只有**中文转述**的 ISC 署名（`Copyright (c) 2008 Otto Moerbeek <otto@drijf.net>` + ISC 许可字样），
   **没有** OpenBSD 原件那段逐字 permission 句——实测 `grep -c "Permission to use, copy, modify" = 0`；
   逐字补写是新的裁定事项，本窗未自行添加（原文全文已抄进 `E1`）。
2. **B 判定口径由 create 改 hit（已改）**：`最终状态` 段的 3+2 四行与本文「许可证」节按 hit 重写
   —— `适配路径`＝路径 A + 路径 B 命中既有条目（本 PR 不附知识草稿、不使用知识前缀）、
   `使用知识库`＝主命中 E287 / E429 / E501（E332 方向一致，逐条写明各自覆盖本包哪一手）、
   `知识库扩展`＝无、`关联 Issue`＝无（B 判定为命中，未建 Issue）。历史起草过程改写成结论式句子。
   **本轮复算**：本文与全归档的**起草占位串计数均为 0**（Issue 回填位形态与“尚未创建”形态两类，
   复算命令与各计数原样记在 `E/E1-before-license-and-precedents.txt` 第 9 段与
   `E/E2b-w3-marker-readings.txt`，正文里不留这些字面串以免被门禁再扫到）；`knowledge/drafts/`
   未新建本包件、未动他人草稿。
3. **框架 `ohc-run.py build` 对本归档不适用（本轮未跑该步，实测依据见 §7.5 表第 1 行）**：该驱动
   Step1 找的是 `archives/r/rs-20200313/src`（本归档是 `archives/r/rs/20200313/` 布局），实测
   `EXIT_REASON: init_build_failed`，且它会去搜索引擎抓 savannah / waterlan 上的**同名异构软件**
   ⇒ 不伪造目录、不换错源、不改结构绕它；真实构建由 `conan-verify` 的 G2 `conan create` 与
   finish 的 Step5 W3 本地 CI 承担。故本轮顺序为 gate → conan-verify → finish。
4. **门禁重跑（两件事的文本先提交 `307708bb5e`，随后重跑；B 机，`CONAN_HOME=~/tmp/ch/home-rs`，
   每步先过 `gate.sh --light` 再经 `build-slot.sh --kind short --wait 1800`，未绕槽）**：

| 步 | 命令 | rc | 判决读数 | 日志/实物 |
|---|---|---|---|---|
| 0 | `sh ~/tmp/uc2/gate.sh --light` | 0 | `GATE_PASS:probe=clang MemAvailable=5567MB swap余=47998MB 编译器进程=0`；槽位读数 `SLOT_STATUS: 长杆 0/2 · 机动 1/3`、`SLOT_OK 04:30:34` | `G-runs.log` |
| 1 | `ohc-run.py conan-verify rs 20200313` | **0** | **三一致**：文字「✅ 配方验证通过: rs 20200313」+ 报告 `**Verdict**: PASS` + rc=0；G1/G2/G3 真 PASS（G2 实跑 `conan create … -pr:h/-pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable`）。⚠ 报告图标仍会与文字相反：G0/G4/L2/L4/L5 记 ✅ 实为「跳过 / 无法找到程序包 ID / 无法识别构建系统」⇒ **实际覆盖仍只有 G1–G3**（§7.5 与注脚 1 的口径不变，本文不写“全绿”） | `R1-conan-verify.log`、`reports/conan-verify-report.md`（04:31:57）、`reports/conan-create.log`（04:31:52）、`.conan-verified` `verified_at=2026-09-27T04:31:57.722318` |
| 2 | `ohc-run.py finish rs 20200313 built` | CLI **2** | `EXIT_REASON: finish_success`、`EXIT_CODE: 0`、`STEP_FAILED: Step6`、`失败步骤: step5b, step8`（仓库级/工具已知噪声，本轮未顺手修）；三条判据齐：finish 日志含「✅ W3 本地 CI 模拟通过」×2 + 归档 `.ci-result.json` `exit_code: 0`、`step: W3_local_ci`（**不是 Step5**）+ w3 日志 `Success: 1 / Failed: 0` | `R2-finish.log`、`reports/w3-local-ci.log`（04:39:55） |

**本轮新读数（旧值就此作废，本节只留这一套；全文现行读数见 §7.10）**
`2026-09-27T04:39:55.158780`、`integrity_hash 7a90b79a35d5cc9f`、`log_sha256`
`01a619173df0633bb2cb86084c60ddd45c21d748b2ff1a9f9949bfeb54099475`（三件 `reports/` 均为本轮
重生成，mtime 04:31:52 / 04:31:57 / 04:39:55 晚于本轮提交 04:29，已按 `git add -f` 随第二枚
提交入库）。

**recipe revision 随 `conanfile.py` 改动变化**（这是“旧 W3/verify 证据作废”的机理，与 §7.0 同口径）：
改前 `#ecac6a0492c1b0f4e85677fadb886e53` / `#304cf3207e2b3be61761bad8c8265505`，本轮 G2 侧
`rs/20200313@ohpcd/stable#217f8e3a3ff444297bb4319b95b320f0`、W3 侧
`rs/20200313#b8e3adcc0f5bdc3f24c5df82455a203b`；而 package_id
`6b129b068851896169fae42d399fa922d239ce8a` 与包 revision `28caaf370f0f28cb45fcd83a6497f324`
**逐字符未变** ⇒ 产物未变（本轮改的是许可元数据与注释/文档）。“G2 与 W3 两处导出 revision 数字
不同而实物相同”的现象与 §7.7 第 3 项同型，机理仍**未查证**。

**W3 账本（本轮复算，与改前逐项相同，账本未动）**：`UPSTREAM_CHECK_SUMMARY N_static=13
N_executed=13 pass=12 skip=1 fail=0`、`UPSTREAM_CHECK_VERDICT PASS`、`UPSTREAM_CHECK_SKIPPED
unicode-3-optu8`（唯一 `category: os:mirbsd` 的正向那条，仍真实执行后按上游自声明记 SKIP）、
`CONSUMER_SUMMARY cases=7 pass=7 fail=0`、`CONSUMER_VERDICT PASS`；`N_registered=13` 记于
版本级 `manifest.yaml:141` 与 `test_package/MANIFEST.yml:89`（两处数值未变；本节原写 `manifest.yaml:131`，
该块此后补了 `type:` 取值口径注释而整体下移 10 行 ⇒ 收口续棒按提交态实物校正行号）；create 日志
`grep -ci warning` = **0**。未缩分母、未把 SKIP 并进 PASS、未改 `check.t` 语料一个字。

**本轮仍未做/未证实**：①W4/W5 独立审计**未在本窗重跑**（派发给主理窗口投审计），§7.7 第 4 项
口径不变；②PF7 取源 URL 当轮一字未动、仍按派发指令交主理定夺（收口整改棒已按 (a) 换官方直链闭环，见 §7.10）；③`ohc-run.py build` 的“另有正规模式
否”仍未验证；④逐字 ISC permission 句要不要补进 `compat_reallocarray.c` 文件头，待主理裁定
（见本节第 1 项的实读发现）。

**§7 轮次索引（各轮留痕落在哪一节；全文现行门禁读数只有 §7.10 一处）**：
①整改轮（2026-09-27，构建输入与披露件提交 `d7c3be6905`）→ 读数 §7.5、未证实点 §7.7；
②收口轮（2026-09-27，许可证追加 ISC + B 判定口径改 hit，文本提交 `307708bb5e`）→ 该轮 revision 上的
verify/finish 读数 §7.8；
③整改轮 2（2026-09-27，许可证第三字段 + 派生件许可块重排，门禁读数绑定提交 `8070ed47e8`）→ 读数 §7.9；
④收口整改棒（2026-09-27，R39/PF7 换上游官方直链，门禁绑定提交 `5133d39bfb`）→ **现行**读数 §7.10；
⑤收口续棒（2026-09-27，代号 z75y）**只动文档载体**：§7.8 标题与轮次索引、残留措辞改判、引用行号提交态
复验（§2 的 w3 日志 196-211→191-206、`manifest.yaml:131`→141、软件级 `manifest.yaml:27`→30）、
`knowledge_gained` 8 条补同行 `ref:` ⇒ **未动任何构建输入、未触发重跑**，recipe revision 仍是 §7.10 的
`8b0e7e3eb8908be52b8c996337798127`，全文现行门禁读数仍只有 §7.10 一处。

### 7.9 门禁读数（整改轮 2：许可证第三字段 + 派生件许可块重排后重跑；已被 §7.10 取代，历史留痕）

触发重跑的构建输入改动两处（都会改 recipe revision）：①`conanfile.py:66` 的 `license`
由两项补齐为 `["BSD-3-Clause", "ISC", "MirOS"]`（独立审计 P1；一手依据与逐文件归属见
「许可证」节，本轮自己重下 `rs_20200313-1.debian.tar.xz` 复算，未抄前棒读数）；
②`compat_reallocarray.c` 头部的逐字 ISC 许可块从署名句中移出、独立成段（该件是
`export_sources` 的 shipped source）。软件级 `manifest.yaml` 的 `license:` 块列表与 ①
同批同步为三项（非构建输入，不改 revision）。

- 门槛与槽位（未绕槽）：`gate.sh --light` 两次均 `GATE_PASS:probe=clang`（`MemAvailable=5487MB` /
  `5501MB`、`编译器进程=0`；决定性判据是 clang 探针，故同时留 MemAvailable 原值供复核）。设备现版
  `~/tmp/uc2/gate.sh`（2026-09-26 起）已解析 `--light`：:33-34 定 `TH_MEM_DEFAULT=6000` /
  `TH_MEM_LIGHT=3000`，未识别的 `--*` 旗标一律 `GATE_FAIL:unknown_flag` 退出 3，`TH_MEM` 到 :53-54
  才落值 ⇒ 轻档 3000MB 门槛**真正生效**。本条此前写「gate.sh 第 25 行 `TH_MEM=${1:-6000}` 把 `--light`
  当数值参数用、内存档位的数值比较并未真正生效」对现版已不成立（外部工具漂移，非门禁项），故改为按
  现版复算，行号取自本棒 `grep -n TH_MEM` 的实测输出，不复用旧行号。构建走机动短槽
  `build-slot.sh --kind short --mem 2500 --wait 1800`：`SLOT_OK 06:14:08`（verify）、
  `SLOT_OK 06:14:47`（finish）；长杆槽 1-2 未占用。
- conan-verify：**判绿三一致全过**——正文文字「✅ 配方验证通过: rs 20200313」＋报告第 3 行
  `**Verdict**: PASS`＋rc=0。报告各节**实测原样**（⛔ 抄图标）：G0=✅ PASS｜📦 构建系统:
  unknown；G4=✅ PASS｜⚠️ 无法找到程序包 ID；L2/L4/L5=✅ PASS｜⏭️ 跳过（无 cache 路径）
  ⇒ 本包判定不变：**实际覆盖仅 G1–G3**，其余为跳过/未取到，不作覆盖声明（§「读数注脚」1）。
- finish：`EXIT_REASON: finish_success`、`EXIT_CODE: 0`、`STEP_FAILED: Step6`、`失败步骤: step5b, step8`（仓库级他人 drafts 与框架 gen_summary 已知噪声，本窗未顺手修）；判绿三条齐：finish 日志含「✅ W3 本地 CI 模拟通过」＋归档 `.ci-result.json` `exit_code: 0` 且 `step: W3_local_ci`（**不是 Step5**）＋w3 日志第 285-286 行 `Success: 1 / Failed: 0`（这两个行号属该轮实物，即门禁读数绑定提交
  `8070ed47e8` 里的那件；该件此后被 §7.10 那轮重生成覆盖，本地件现为 284 行、`Success: 1` /
  `Failed:  0` 落在 280-281 行 ⇒ 现行判据见 §7.10(6)，本棒已逐行复核两组行号）。CLI rc=2 是框架 Step6
  的字面量，不作失败判据。
- **本节读数**（上一组 timestamp 04:59:10 / `integrity_hash 9177ac2a329dc2bf` 就此作废；本文不声称「旧值
  0 残留」——该串在本节仅作**历史留痕**出现 1 处，语义不误导）：`.ci-result.json` 的 timestamp
  `2026-09-27T06:23:38.331467`、`integrity_hash 46c2b81c0d1b1b32`、`log_sha256`
  `818538b4fdee42339b13d68394baaa2fafcdbd7df03801a518d043dd7471232b`。两值都**自算复现**而非照抄：按
  `scripts/ohc/finish.py` 的 `_write_ci_result`（raw = 时间戳:软件:版本:exit_code，取 `sha256(raw)[:16]`），
  raw = `2026-09-27T06:23:38.331467:rs:20200313:0` → 得 `46c2b81c0d1b1b32` ✓；`log_sha256` 与
  `sha256(reports/w3-local-ci.log)` 逐字相等 ✓。
- recipe revision（第 3 轮审计 P3 补记）：本轮 W3 导出 `rs/20200313#a3287cad5a2309942dd9fc42bef6d0f9`、
  package_id `6b129b068851896169fae42d399fa922d239ce8a`、包 revision
  `28caaf370f0f28cb45fcd83a6497f324`；复算式 = 提交态 `8070ed47e8` 的 `reports/w3-local-ci.log:115`
  （Exported）与 `:222`（Full package reference）——该两行在换源重跑后已被 §7.10 的新 revision 覆盖，
  故此处直接落串，免得读者再去日志里推。
- 三件 `reports/` 均为该轮（本节当时）重生成并随本节一起 `git add -f` 入库：`conan-create.log` 与 `conan-verify-report.md` mtime 06:15、`w3-local-ci.log` 06:23；换源重跑后在库五件的现行 mtime 见 §7.10 第 (9) 项。
- 未变量（本轮逐项复算）：`compat_reallocarray.c` 函数体与 errno 逻辑一字未动——与设备原件（OpenBSD v1.3，sha256 `813952c9ae8a0d69…b509348`）逐行对账仍是 **10 行函数体里 9 行逐字符相同**，唯一差异是第 6 行 `errno = ENOMEM;` ↔ `errno = ERANGE;`；两常量 B 机两口径实测 `ERANGE=34`、`ENOMEM=12`（`python3 errno` 与 clang 编译探针一致）；账本 13/13/13、**12 PASS / 1 SKIP / 0 FAIL**（SKIP 是 `check.t:152` 的 `category: os:mirbsd` 正向用例，未并入 PASS、分母未动）、消费者 7/7、编译告警 0。
- §7.8 及更早各节（含本节此前那组 04:59 数）一律为**历史留痕**，只记当时读数，不作现行证据。

### 7.10 门禁读数（收口整改棒：R39/PF7 换上游官方直链后重跑 verify+finish；**已被 §7.11 取代，历史留痕**——本节的取源结论与「PF7 命中归 0」只对 2026-09-27 那轮有效）

触发重跑的构建输入改动：`conandata.yml:21` 与版本级 `manifest.yaml:27` 的取源 URL 由 `deb.debian.org` pool
换为上游官方 dist 直链 `https://mbsd.evolvis.org/MirOS/dist/mir/rs/rs-20200313.tar.gz`（sha256 一字未动）
⇒ recipe revision 变 ⇒ 重跑 `conan-verify` 与 `finish`。门禁绑定 HEAD `5133d39bfb`（换源提交）；本轮
文档与判决件提交只动 docs，不再动构建输入。§7.9 那组读数（`46c2b81c0d1b1b32` / 06:23:38）就此作废。

**(1) 官方上游端点穷举实测**（B 机 2026-09-27 07:2x–07:4x，逐条 `curl -I/-i` 带 `--connect-timeout`/`--max-time`；
原始头文件 `z75c-rs-close/probe-*.hdr`、`pB-*.hdr`）：

| 端点 | HTTP 码 / 字节数 | 判定 |
|---|---|---|
| `http://www.mirbsd.org/MirOS/dist/mir/rs/rs-20200313.tar.gz` | rc=28 code=000，8003ms 超时 | DNS 可解（A 62.138.145.52 / AAAA 2001:470:6f:94a::1）、TCP 不可达 |
| 同 URL `https`（80/443、`-4`、`-6`、钉 IP `62.138.145.52` 复测） | 全部 rc=28 code=000（12003ms） | 换协议/换栈/钉 IP 三法一致 ⇒ 真不可达，不是 DNS 假象或超时误判 |
| `git.mirbsd.org` / `cvsweb.mirbsd.org` / `ftp.mirbsd.org` / `mirbsd.org` | rc=6 code=000（`getaddrinfo` 同报 -2/-3） | 子域已不可解析；cvsweb 另挂 HTTP Basic Auth（第 3 轮实测 401） |
| `https://www.mirbsd.de/MirOS/dist/mir/rs/rs-20200313.tar.gz` | 200 但正文 28339 字节、`text/html`、`Location: https://mbsd.evolvis.org/` | **不是发布物**：该域 catch-all 301 到站点首页 |
| `https://mbsd.evolvis.org/MirOS/dist/mir/rs/rs-20200313.tar.gz` | **HTTP/1.1 200**、`Content-Length: 12571`、`application/octet-stream` | ✅ 采用（作者自家 Evolvis 服上的官方 dist 件） |
| `https://mbsd.evolvis.org/MirOS/dist/mir/rs/` | 200、2135 字节目录页，列出 `rs-20101029 / 20120325 / 20120414 / 20140609 / 20181225 / 20200313` | 同一棵 dist 树、完整历史发布 ⇒ 非搬运站 |
| `…tar.gz.asc` / `.sha512` / `.sha256`、`SHA512SUMS`、`MD5SUMS` | 全 404 | dist 目录不附签名件 ⇒ 摘要靠与 `.dsc`/pool 实物对账 |
| `mirror.evolvis.org` / `www.evolvis.org` | rc=6 不可解析 | 无第二官方镜像 |

判「官方托管而非第三方搬运」的四条一手依据：①`debian/watch`（`http://www.mirbsd.org/MirOS/dist/mir/rs/` +
`rs-(.*)\.tar\.gz`）与 `debian/copyright` 第 5 行点名的发布目录就是 `MirOS/dist/mir/rs/`，本 URL 路径与文件名
逐字相同，只是主机名迁移；②`rs_20200313-1.dsc` 的 `Vcs-Browser`/`Vcs-Git` 指向 `evolvis.org` 的
`alioth/rs.git`（作者 forge，与 `mbsd.evolvis.org` 同域）；③作者域名 `www.mirbsd.de` 的 301 目标即
`mbsd.evolvis.org`；④整件摘要与 `.dsc` 的 `Checksums-Sha256` 及 pool 实物逐字相等。上游作者本人即
Debian 维护者（`Maintainer: Thorsten Glaser <tg@mirbsd.de>`，`$MirOS:` 署名者 mirabilos），源码 `rs.c:54` 的
RCSID 原文为 `$MirOS: src/usr.bin/rs/rs.c,v 1.16 2020-03-13 19:01:00 tg Exp $`（本棒自解包件实测）
⇒ `MirOS/dist/mir/rs/` 就是上游发布位，dist 树与源码署名同源自证。

**(2) 等价性复算（不是只看大小）**：下载件 12571 字节，`sha256sum` =
`919215dc9fe85a27a30bf63d56406cfb503f9fc9820323c4bd3bfe75a6a3bc3f` ⇒ 与 pool 里的 pristine
`rs_20200313.orig.tar.gz` **整件同一**；两树分别解包后 `diff -rq` **零差异**，7 个文件逐个
`sha256sum` 全等（表：`z75c-rs-close/sha-evo.txt` 与 `sha-deb.txt` 逐行相同）——
`Makefile` 406eeb83…、`check.t` 8d1a0e68…、`rs.1` 5007a206…、`rs.c` a818271e…、
`rs.h` 83082b58…、`utf8.c` 0269fcb8…、`.linked/strtonum.c` 69fedab5…（无 `+dfsg`、无删文件、
无改行尾）⇒ 换源是无损的，URL 变而实物不变。

**(3) 闸侧复算**：直接调仓内实现 `preflight._pf7_classify` ——
新 URL → `None`（放行）；旧 pool URL → 「Debian 下游重打包源」；同主机明文 `http` 版 → 「明文 http
源（R39 要求 https）」（故必须用 https）。整仓闸复跑 `python3 scripts/ohc/preflight.py $PWD origin/main HEAD`
⇒ **PF7 命中由 2 归 0**，`PREFLIGHT_OK=False` 仅剩 1 条 PF9（软件级 `archives/r/rs/README.md`、
`commands.json`、`manifest.yaml` 三份路径段数 <5，属分层产品布局与 PF9 闸的既有冲突，
**不在本条 P1 范围**，如实交主窗处置）。本棒未跑 `--no-preflight`、未碰 PR。

**(4) 门槛与槽位（未绕槽，B 机）**：W0 与每步构建前均先过 `sh ~/tmp/uc2/gate.sh --light`，三次全
`GATE_PASS:probe=clang`——`MemAvailable` 依次 5388MB（W0 前）、5438MB（verify 前）、5375MB（finish 前），
`编译器进程=0`；现版轻档门槛 3000MB 真实生效（见 §7.9 的复算式），另留整机原值供复核：
`load=21.2`、`PSI_full avg10≈74`、`MemFree≈800MB`（队友窗口占用，本棒未动任何他人进程）。槽位一律
`build-slot.sh --kind short --mem 2500 --wait 1800`：`SLOT_OK 07:41:20`（conan-verify）、`SLOT_OK 07:42:06`（finish），
长杆槽 1-2 全程未占。W0：`ci/scripts/preflight_check.sh rs/20200313` rc=0「预检通过（无依赖需要检查）」。

**(5) conan-verify（HEAD `5133d39bfb`，日志 `z75c-rs-close/R1-verify.log`）**：判绿**三一致**全过
——正文「✅ 配方验证通过: rs 20200313」＋报告第 3 行 `**Verdict**: PASS`（`Date: 2026-09-27T07:41:33.382325`）
＋rc=0。G1/G2/G3 真 PASS，G2 实跑 `conan create … -pr:h/-pr:b=ohos-aarch64 --build=missing
--user=ohpcd --channel=stable` **从新官方直链取源并构建成功**（这是换源可用性的端到端证据）。
报告图标仍会与文字相反：G0=✅ PASS｜📦 构建系统 unknown；G4=✅ PASS｜⚠️ 无法找到程序包 ID；
L2/L4/L5=✅ PASS｜⏭️ 跳过 ⇒ **实际覆盖仅 G1–G3**，不作全绿声明（与 §7.9 同口径）。

**(6) finish（同 HEAD，日志 `z75c-rs-close/R2-finish.log`）**：`EXIT_REASON: finish_success`、
`EXIT_CODE: 0`、`STEP_FAILED: Step6`、`失败步骤: step5b, step8`（框架与仓库级已知噪声，本棒未顺手修）；
CLI rc=2 是 Step6 字面量、不作失败判据。判绿三条齐：finish 日志含「✅ W3 本地 CI 模拟通过」×1、
归档 `.ci-result.json` `exit_code: 0` 且 `step: W3_local_ci`（不是 Step5）、
`reports/w3-local-ci.log:280-281` = `Success: 1` / `Failed:  0`。

**(7) 本轮现行读数**（§7.9 的 `46c2b81c0d1b1b32` / 06:23:38 就此作废，取代关系就地标注）：
`.ci-result.json` timestamp `2026-09-27T07:43:21.984912`、**`integrity_hash 621df58e9c867c84`**、
**`log_sha256 d599a9b4d15796e84da46e3dd110e14977f3a7b3545be57a3079776110ab1937`**。两值本棒自算复现而非照抄：
按 `scripts/ohc/finish.py` 的 `_write_ci_result`（raw = 时间戳:软件:版本:exit_code，取 `sha256(raw)[:16]`）
raw = `2026-09-27T07:43:21.984912:rs:20200313:0` → 得 `621df58e9c867c84` ✓；`log_sha256` 与
`sha256sum(reports/w3-local-ci.log)` 逐字相等 ✓（原始读数 `z75c-rs-close/out-27.txt`）。

**(8) 新 revision 三串**：`rs/20200313#8b0e7e3eb8908be52b8c996337798127`（在库
`reports/w3-local-ci.log:109` Exported、`:217` Full package reference，导出时刻
2026-09-26 23:43:15 UTC = 本地 07:43:15）、package_id `6b129b068851896169fae42d399fa922d239ce8a`、
包 revision `28caaf370f0f28cb45fcd83a6497f324`。**后两串与 §7.9 那轮逐字符相同** ⇒ 产物未变，
与「换源是字节级同一」互为交叉印证；变的是 recipe revision（`conandata.yml` 属配方文件）。

**(9) `reports/`（5 件）与在库交付物 18 件**：三件门禁件本轮重生成——`conan-create.log` mtime 07:42:48
（103 行，`grep -ci warning` = 0，sha256 前缀 `19dc619dd043`；§4 的 0-warning 指针已改指该本地件）、
`conan-verify-report.md` 07:42:52（`6b0642af6cb7`）、`w3-local-ci.log` 07:43:21（`d599a9b4d157`，
即 `log_sha256`）；另两件是第 3 轮独立重审计判决件 `z75d-audit-result.json`（`f50fb400100e98d1…22c302`）
与 `z75d-w4-report.log`（`9b2ef7c90f93898b…6687d`），按 `.gitignore:96` 的 `reports/` 忽略惯例以
`git add -f` 入库 ⇒ 本归档在库交付物由 16 件增至 **18 件**。

**(10) 未变量（本棒逐项复核）**：上游 7 文件实物与两树对账同 §7.5/§7.10(2)；账本 13/13/13、
**12 PASS / 1 SKIP / 0 FAIL**（SKIP 仍是 `check.t:152` 的 `category: os:mirbsd` 正向用例，未并入 PASS、
分母未缩）；消费者 7/7；`compat_reallocarray.c` 函数体与 errno 逻辑一字未动；许可三合一字段
（`BSD-3-Clause`/`ISC`/`MirOS`）与 `patches: {}` 未动；`sha256` 取源摘要未动。
---

**编译结束**: 2026-09-28 13:02
**最终状态**: built

### 7.11 现行门禁读数（2026-09-28 收尾-8：换源 + 撤 3 件 .log 后重跑；**本节为全文唯一现行，取代 §7.10**）

#### (0) 为什么又换源——CI worker 侧拒连，`/rebuild` 未消（一手读数）
- 两轮**同一第一真实错误**：build#63232 / worker `CI-022`（09-28 02:17 判决）与 build#63490 / worker `CI-007`（09-28 12:08 判决），
  conan `source()`（`conanfile.py:90` 的 `get(...)`）均首错
  `Error downloading file https://mbsd.evolvis.org/MirOS/dist/mir/rs/rs-20200313.tar.gz`
  → `Failed to establish a new connection: [Errno 111] Connection refused`（各重试 2 次同错）。
- 同轮日志另证 `build_and_test.sh` 的 pre-download 在该类 worker 必落空：
  `[fail] [Errno 2] No such file or directory: 'curl'` → `[WARN] Failed to pre-download … will rely on conan's download`
  ⇒ 只能靠 conan 自身下载，镜像 fallback 与预取两道都不在场。
- **出口并非整体不可用**（同为无 curl 的 worker `CI-018`）：sff 的 `codeberg.org` 拿到 **HTTP 429**（连接与请求均成功、只被限流）、
  `ncurses/6.6` 二进制从 `ohpcd` 远端 `Downloaded package revision` 成功 ⇒ 定性＝**只有 evolvis 这台主机拒连本 worker**，
  ⛔ 不是「源码站全挂」、也不是「我方两端网络问题」（A 机与 B 机 `curl -L` 同址均 **200 / 12571 B**）。

#### (1) 新旧 URL 与三方同哈希（**sha256 一字未动**；收尾-4 ②批准）
- 旧 `https://mbsd.evolvis.org/MirOS/dist/mir/rs/rs-20200313.tar.gz`
- 新 `https://deb.debian.org/debian/pool/main/r/rs/rs_20200313.orig.tar.gz`
- 实测：两件各 **12571 B**，sha256 同为 `919215dc9fe85a27a30bf63d56406cfb503f9fc9820323c4bd3bfe75a6a3bc3f`
  （＝本文件 `conandata.yml` 声明值，＝ `rs_20200313-1.dsc` 的 `Checksums-Sha256`），`cmp` **逐字节相同** ⇒ 三方同哈希。
- 同批改两处 `url`：`conandata.yml` 的 `sources[0].url` 与版本级 `manifest.yaml` 的 `source.url`；
  `debian/source/format = 3.0 (quilt)` ⇒ Debian 改动全在独立 `.debian.tar.xz`，此 `.orig` 即 pristine 上游件。
- **PF7**：pool 属 `_PF7_DEBIAN_HOSTS` 拉黑面 ⇒ 按 R52 记 **P1-已例外处置**（⛔ 不记 P3、⛔ 不改 sha256、⛔ 不换版本），
  「官方托管例外 + 两端读数」署名落在 PR 正文；`run_preflight` 的 PF7 命中因此**由 0 回到 2**，属**已知且已例外**，不是新回归。

#### (2) 撤出 PR 的 3 件 `.log`（第 19 条 / review-memory §三.19，收尾-4 ①批准；**文件仍在本地**）
工作区绝对路径前缀 = `<worktree>/archives/r/rs/20200313/reports/`（worktree = B 机 `~/qzy/主理-75-rs-20200313`）：

| 本地件 | 行数 | sha256 |
|---|---|---|
| `conan-create.log` | 103 | `a0721da464789693bacbdd5d6315672dc7fb21f7631c77a55dd233c52b51469f` |
| `w3-local-ci.log` | 285 | `a9e20e0f6286f691589b9673e1364b00cc3886b3914f76b4e3bd210033a4393a` |
| `z75d-w4-report.log` | 144 | `9b2ef7c90f93898b1421453dff56e03cf4332b1d5647afdb7ec349bda376687d` |

⇒ 全文凡称「本地件 `reports/*.log`」的行号引用一律按**上表本轮实物**取用；本节 (3) 给出 09-28 重生成后的行号，
**旧轮行号（§7.8/§7.9/§7.10 及正文引用）全部属历史**，勿再据此开文件核对。`.gitignore` 仍忽略 `reports/`，
三件以 `git rm --cached` 移出索引、**工作区文件保留未删**。

#### (3) 本轮门禁读数（绑定提交 `568a5858d0`；recipe revision `3b024f3cb837cd63f710aa01abad51cd`）
- `ohc-run.py conan-verify rs 20200313`（12:51 首跑、13:02 finish 内复跑同 rrev）：**VERIFY_RC=0**，G1/G2/G3 PASS，报告 `**Verdict**: PASS`；
  日志 `Exported: rs/20200313@ohpcd/stable#3b024f3cb837cd63f710aa01abad51cd`（两次同值 ⇒ 本轮构建输入自 verify 起未再变）。
- `ohc-run.py finish rs 20200313 built`（13:02–13:03）：`EXIT_REASON: finish_success`、`EXIT_CODE: 0`、`STEP_FAILED: Step6`，
  实际失败步骤 = `step5b`（`check_knowledge_gap`，全仓 92.5% 同态的存量现象）+ `step8`（`gen_summary` 报 `'str' object has no attribute 'append'`，**框架缺陷，按 §8 不在本包 PR 修**）。
- `.ci-result.json`：`timestamp=2026-09-28T13:03:18.226357`、`exit_code=0`、`step=W3_local_ci`、
  `integrity_hash=bc0562892d1d7f2f`、`log_sha256=a9e20e0f6286f691589b9673e1364b00cc3886b3914f76b4e3bd210033a4393a`
  （与 `w3-local-ci.log` 实算**逐字相等** ✓）。
- `w3-local-ci.log`（285 行）本轮关键行号：`:179` `Calling build()`；`:205` `UPSTREAM_CHECK_SUMMARY N_static=13 N_executed=13 pass=12 skip=1 fail=0`；
  `:206` SKIPPED `unicode-3-optu8`；`:207` `UPSTREAM_CHECK_VERDICT PASS`；`:255` `CONSUMER_VERDICT PASS`；`:281-282` `Success: 1 / Failed: 0`。
- W2 原子性：仅含配方变更 **16 文件**、无框架文件。
- 已知未就绪 1 项（既有态，非本轮引入）：`submit` 预检要 `reports/test-report.md`。
- 本节只覆盖门禁与取源；测试账本（13 上游 + 7 消费者）、许可证三合一、`patches: {}` 零补丁口径均未变。

