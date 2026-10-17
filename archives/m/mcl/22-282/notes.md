# mcl 22-282 — 适配工作笔记（Windows 阶段 1，2026-09-26）

任务：ohpcd 平台 mcl 22-282 · 分支 `feat/mcl-22-282`（以平台实际显示
为准，提交前核对绑定与截止时间）。

## W0 依赖分析

**（真机首验修正，2026-09-27）**：原判"无外部 conan 库依赖"错误。
上游 Makefile.am 无条件 `LDADD = … -ltingea`，且 src/impala/ivp.h
`#include <tingea/types.h>` —— libtingea 来自姊妹库 **cimfomfa**
（ micans 同作者，非随源码捆绑；干净环境 conan create 死于
ivp.h:16 fatal error: 'tingea/types.h' file not found，真机
mcl-create9.log 实测）。修正：require cimfomfa/21-361（上游已归档，
status=built 2026-09-08，静态库 libtingea，cpp_info 带
system_libs=["m"]），generate() 加 AutotoolsDeps 注入 -I/-L/-l。
R35 依赖检查 = {cimfomfa/21-361}。

核心聚类库（src/mcl、src/impala、src/gryphon 等）仍为随源码捆绑的
noinst 静态库；configure 仅 ACX_PTHREAD + AC_CHECK_LIB([m],[ceil])
（系统提供）。可选 `--enable-rcl`（上游默认关闭）不启用。

MateBook 注入验证（不作干净环境验证依据，仅证明其余环节就绪）：
注入本地构建的 cimfomfa 产物后 build() 自检两簇划分通过、消费者
6/6 全绿——依赖补上后，预期干净环境可直达同等结果。

构建/运行时工具：无 bootstrap 需求（configure 预生成）；doc/ man 页
预生成分发，zoem/troff 不需要（见下）。

## W0b 历史知识核验

- 标准 automake + 预生成 configure 先例：本批 pspg/ivar 同期模式。
- E114（umask 077→022 替换）先例：zzuf/0.15、jailkit/2.23；E074
  （-j1）：tarsnap 等；§12.38① env -u CONFIG_SHELL + 绝对路径：
  gtypist/2.10.1。

## 源码要点（官网 tarball 22-282 实测）

- sha256 `291f35837b6e852743bd87e499c5a46936125dcdf334f7747af92e88ac902183`
  （micans.org 官网为 mcl 官方分发渠道；GitHub micans/mcl 不发布版本
  归档）。
- 自带预生成 configure；configure.ac 无 AC_CANONICAL → 无需
  config.guess/--build；GPL-3.0-or-later（COPYING 为 GPLv3）。
- 版本输出：`mcl --version` 首行 `mcl 22-282`（impala/app.c
  app_report_version，`%s %s` + mclDateTag="22-282"）；套件各工具
  （mcx/mcxload/mcxdump/...）同框架。
- **二进制落点**：automake 子目录 bin_PROGRAMS → src/shmcl/mcl、
  src/shmx/{mcx,mcxsubs,mcxmap,mcxarray,mcxdump,mcxload}、
  src/shcl/clm、src/shmcx/mcxi；顶层无 bin/（make install 才落
  $(bindir)）。
- **无 test/check 目标**（全部 Makefile.am 无 TESTS；grep 实测）；
  testing/ 为交互式人工观察 harness（硬编码 /usr/local/bin/{bash,perl,
  mcl}）→ build() 以确定性数据集自检（mcxload→mcl 两簇精确划分），
  消费者测试覆盖 mcxload/mcl/mcxdump。
- **doc/ man 页**：34 个预生成产物 + 36 个 .azm 源全部随 tarball 分发；
  实测逐对核验每个产物 mtime 晚于对应 .azm（mclindex.7 与 index.in.azm
  同核验）→ `make`/`make install` 不会触发 zoem/troff 重建，doc 子目录
  install 直接可用，无需占位补丁。
- 选项核验：mcxload `-abc`/`-write-tab`/`-o`（mcxload.c:247）；
  mcl `-I <num>`（procinit.c:106）/`-use-tab <tab>`（alg.c:358，输出
  标签聚类）；mcxdump `-imx`/`-tab`/`-tabc`。
- configure 含 2 处 autoconf 标准 `umask 077` 段 → E114 替换（jailkit
  同款 _unmask：configure 于 configure 前、config.status 于 configure
  后各处理一次）。

## 测试计划

- 构建自检（配方 build()，1 项）：确定性 5 节点两簇 abc 数据 →
  mcxload → mcl -I 1.4 -use-tab → 断言 cls 恰为 {a1,a2,a3} 与 {b1,b2}
  两行（顺序不敏感）。
- 消费者（test_mcl.sh，6 项）：见 README。全部离线、确定性；断言 5
  与构建自检同数据集，但走的是**已安装包内**二进制（安装位与 PATH
  隔离验证，R33/R34）。

## 留给 MateBook 的验证项

1. R35 依赖检查：空集（无 conan 依赖），记录即可。
2. conan create + conan test 完整跑通（configure → make -j1 → build()
   自检 → make install → 消费者测试）。
3. 关注点（失败时按下列顺序排查）：
   - `make -C doc` 是否在真机 mtime 粒度下仍不触发 zoem 重建（Windows
     解包核验过时间戳；若 tar 解包丢失 mtime 导致重建触发，按首个真实
     错误处理：先试 `touch` 对齐，勿直接改 Makefile.am）。
   - 断言 5 的 cls 输出格式：-use-tab 下 cls 每行一簇标签（字段分隔
     符空格/tab 均已归一化）；若 mcxdump/cls 行序或字段序与预期不符，
     以首个真实输出为准调整断言而不是放松簇划分语义。
   - ACX_PTHREAD 在 OHOS clang 下的探测结果（-pthread 标志透传）。
   - mcxarray 等依赖不到的组件若编译失败（未在 Windows 预演编译），
     记录首个真实错误；所有组件均应可编译（无平台特有依赖）。
4. `ohc-run.py finish mcl 22-282 built` → W4 审计（不跑 submit）。

## CI 复验修正（2026-09-28，MR !13455 CI #63497 configure 失败）

任务分支已真机全绿（SHA a62d2403，回写 c53e886e），但 MR CI
（worker OpenHarmonyPCDeveloper-CI-035，同一 SHA c53e886e）的
conan create 死在 configure：
`autofoo/config.guess: can't create .../.cache/tmp/.../dummy.c:
Permission denied` → `cannot guess build type; you must specify one`。

根因：generate 的 configure 在 build 类型探测阶段执行
autofoo/config.guess（Windows 阶段 W0 误判"configure.ac 无
AC_CANONICAL_* 不需要 config.guess"——生成脚本里 ACX_PTHREAD 之前
就有标准 canonicalization 段）。CI worker 的临时目录（HOME/.cache/tmp）
不可写，config.guess 编译 dummy.c 失败；MateBook 上该目录可写所以
同样脚本侥幸通过——环境差异，非代码缺陷。

修复：configure 显式 `--build/--host=aarch64-unknown-linux-musl`
（tarsnap/1.0.41 先例同款手法）。选型依据：
- 自带 config.sub 为 2022-05-25 版，不识别 ohos 后缀（实测
  Invalid configuration），ivar/mgard 的 aarch64-unknown-linux-ohos
  方案在此不适用（ivar 的 config.sub 由 autoconf/2.72 bootstrap
  安装，版本新）；
- musl 后缀实测可识别，且 configure 的 host_cpu/host_os 分支只特判
  solaris/aix/freebsd/darwin/osf/hpux，linux 无差异分支；
- 显式 --build 后 config.guess 不再执行（configure L5511 只在
  build_alias 为空时调用），host 默认继承 build。
MateBook 与 CI 行为收敛：不再依赖临时目录可写性。

### 第 4 轮（SHA 678c8c91 复验构建全绿、审计 FAIL 后修正）：审计 P1×3 清零

MateBook 对 678c8c91 复验：R35 依赖解析、conan create（--build/--host
生效、config.guess 零执行）、build() 自检两簇精确划分、消费者 6/6、
finish（.ci-result.json exit_code=0）全部通过；W4 审计 FAIL（P0=0 /
P1=3，report exit=2），均为「声明与实际不符」类。修复：

1. 软件级 README.md 三处过期：依赖改为 cimfomfa/21-361（原「无外部
   conan 库」与 requires 冲突）；适配要点 #1 改为显式三元组方案（原
   「无需 --build」与本轮 CI 修复核心冲突）；版本表说明改为真机已验
   证据口径（原「待真机验证」过时）。
2. 22-282/manifest.yaml configure_options 补记 --build/--host 三元组
   及选型依据（原注释「不需要 config.guess/--build」与实际传参冲突）。
3. conanfile.py 自检注释更正：管线止于 mcl（-use-tab 下 cls 直接以
   标签落盘），mcxdump 不在自检内、由消费者测试第 6 项覆盖（原注释
   虚指 mcxdump 转储步骤）。

conanfile.py 属配方文件，改动虽限注释仍须 MateBook 对新 SHA 全量重走
create → test → finish → 审计。

### 第 5 轮（SHA 0225726e 复验全绿 + finish 过、审计 FAIL P1×1）：软件级 manifest L11 同步

MateBook 对 0225726e 复验：构建/自检（两簇精确划分）/消费者 6/6/finish
全绿，CI #63497 修复未回退；上轮 3 项 P1 全部清零。W4 审计 FAIL
（P0=0 / P1=1）新发现：软件级 archives/m/mcl/manifest.yaml:11
key_points[0] 仍写「无需 config.guess/--build」+「无外部 conan 依赖」，
与配方显式三元组 + requires("cimfomfa/21-361") 直接冲突（第 4 轮只改
了 README 与版本级 manifest，漏掉软件级 manifest 的同一声明）。

修复：仅改 manifest.yaml L11 一行——key_points[0] 改为三元组口径
（--build/--host=aarch64-unknown-linux-musl，config.guess 探测背景与
CI #63497 实测）+ 唯一外部依赖 cimfomfa/21-361（libtingea），与版本级
manifest/README 表述一致。

manifest 不默认视作纯文档 → 新 SHA 需 MateBook 全量重走 create →
test → finish → 审计。MateBook 工作区 manifest.yaml/notes.md 的 M 为
finish 回写生成物（stash@{0} 有备份），不提交、不覆盖。
---

**编译结束**: 2026-09-28 19:00
**最终状态**: built
