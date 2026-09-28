# snap 2013-11-29 适配笔记

适配执行：主理-73 子代理（Windows 编排 + 鸿蒙 PC A 机真机构建），2026-09-27。
SNAP = KorfLab Semi-HMM-based Nucleic Acid Parser（DNA 序列基因预测器），
裸 Makefile 的 C 项目，零外部库依赖，产物为 5 个 CLI 工具
（snap / fathom / forge / hmm-info / exonpairs）+ 上游自带的 stock HMM 参数库。

## 编译环境

- 构建系统: 裸 Makefile（无 configure；`ohc-run.py conan-verify` 全门禁 PASS）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（profile `ci/conan/profiles/ohos-aarch64`，conf 注入
  `/data/service/hnp/bin/clang`）
- 状态: built（conan-verify Verdict=PASS 后 finish）

## 编译步骤

探索构建（源码树 `~/builds/snap-2013-11-29.work`，双闸 gate.sh --light +
build-slot.sh --kind short 内）：

```bash
make CC=clang CFLAGS="-O2 -fcommon" snap fathom forge hmm-info exonpairs -j1
```

要点：上游默认目标链 `make gcc` 硬编码 `CC="gcc"` 且带 `-Werror`（设备/CI 只有
clang），**不改 Makefile**，直呼五个 app 目标让 `%.o: %.c` 模式规则吃
`$(CC)/$(CFLAGS)` 覆盖；`include depend` 与顶层 `Zoe/*.o` 目标路径一致，
无 VPATH 问题。配方 `build()` 与此逐字同源（R33：编译器/flags 全部取自
Conan conf，不读裸 shell env）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首次链接失败：`ld.lld: duplicate symbol: zoeFunction/zoeConstructor/zoeMethod`（snap.o 与多个 Zoe/*.o 冲突） | clang≥11 默认 `-fno-common`，Zoe 库在 snap.c 与 Zoe/zoeTrellis.c 等多处重复的 file-scope tentative 定义不再合并（与上游 2022 年 "gcc10-fix" 提交修的是同一类问题，2013 源没有该修复；Debian arm64 包由 gcc 旧语义构建） | CFLAGS 加 `-fcommon`（flag 级最小修，不改源码；`-O2 -fcommon` 与设备探索构建、conan-verify、CI 三处同源） |
| 2 | `snap --help` 报 `zoeParseOptions: unknown option (--help)` | zoe 选项解析器（Zoe/zoeTools.c:91）按注册表精确匹配单横线选项，上游只注册了 `-help`，无任何 `--version` | 最小补丁 `patches/0001-snap.c.patch`（K0 CLI 契约）：注册 `--help`/`--version` 各两行 + `--version` 输出 `snap 2013-11-29` 后 exit(0)，无平台宏 |
| 3 | test_package 报 `HMM not found at <pkg>/res/HMM/minimal.hmm` | `copy()` 默认 keep_path=True 保留 `HMM/` 前缀，dst 又写了 `res/HMM` → 双层嵌套 `res/HMM/HMM/` | dst 改为 `package/res`，产物 `res/HMM/*`，test_package 经 `cpp_info.resdirs` 定位 |
| 4 | finish 首跑被 JC 杂物闸拦（Junk Files: 2） | ①先前 conan-verify 在 test_package 目录内联生成 conanrun.sh/conanbuild.sh 等 7 个 env 生成物（已清）；②分支 0 提交使 `git diff origin/main...HEAD` 为空，junk_check 退化 **full 模式**全仓扫描，撞上 **main 既有基线**的 3 个白名单外隐藏文件（archives/c/cloog/0.21.1/.build-closed、.staging-verified，archives/k/kics/2.1.20/.staging-verified——均已在 origin/main 跟踪，非本任务引入，不碰） | ①清生成物；②按流程先做精确首提交，使 junk_check 走 incremental 模式（只看本 PR diff）后自然豁免基线文件 |

## 货源三向核验（★本节为 conandata.yml 取源例外的完整证据链）

conandata.yml 使用 Debian 池 `.orig`（PF7 例外申报，经裁决 A 方案批准，
与 ink/0.5.3 PR #13035 同型先例）：

1. **GitHub KorfLab/SNAP 任何提交都不含 2013-11-29 内容**。git 历史始于
   2017-05-17：首提交 e11204c（"initial setup"）仅 1 个文件 README.md（12 字节）；
   二提交 a89d68e（"still setting up"，同日）导入的源码树 95 文件，对比
   2013-11-29 快照（Debian .orig 106 文件）**缺 00README、cds-trainer.pl、
   noncoding-trainer.pl、hmm-info.c、patch-hmm.pl、example.zff、exonpairs.c**
   等 9+ 文件且 README.md↔00README 改名（GitHub API git/trees 逐项清点）。
   master HEAD 4ad1e95（2022-10-22，含 gcc10-fix/training update）差异更大
   （新增 DATA/、snap.c/zoeTools.c 内容不同）。无 tag、无 release。
2. **官方原件权威 URL 已死**：Debian watch + copyright 双证官方分发地址为
   `http://korflab.ucdavis.edu/Software/snap-2013-11-29.tar.gz`；korflab.ucdavis.edu
   （128.120.143.145，DNS 可解析）在 Windows 与鸿蒙 PC 设备双侧 http+https
   全部 `curl rc=28` 超时（15s×6 探测）。实验室新站 korflab.github.io（200）
   无软件分发页，SNAP 条目只指回 GitHub 仓。
3. **镜像面清点为空**：Wayback（archive.org / web.archive.org）双侧不可达
   rc=28；distfiles.macports.org、distfiles.gentoo.org、sourceforge 全 404；
   bioconda 只包 2017 git master（版本 2017_03_01，git_rev=4ad1e95），不覆盖
   本版本。
4. **存活副本只有 Debian 系三域且字节同一**（设备侧实测）：deb.debian.org /
   mirrors.tuna.tsinghua.edu.cn / launchpad.net 三处同取
   `snap_2013-11-29.orig.tar.gz` 均 688858 字节，
   sha256=`0ebcd8bb45da54588a81f392baede387fd5ec2a5feb259f3db4b8b8f410abe9c`
   （与任务登记/SCT 索引逐字一致）。
5. **`.orig` 带 `Files-Excluded: .*`（剔点文件）但不是代码重打包**：与 GitHub
   master 的全部内容差异均可归因"上游 2013 年后自行演进"（DATA/ 目录、
   snap.c 2019 溢出修复、gcc10-fix 等），无任何 Debian 引入的代码改动；
   官方 2013 原件与 .orig 的差异仅限点文件（如 macOS .DS_Store）。
6. **CI 侧现实**：`ci/conan/build_and_test.sh` 镜像回退白名单不含
   korflab/ucdavis/archive.org ⇒ 把已死官方 URL 写进 conandata.yml 必红 CI。
   故按 PF7「官方托管例外」申报取池址（本节即 PR 说明的证据正文）。

## 归档层 sha 为什么与 GitHub 不等（参 mstpd 先例口径）

GitHub 归档 tarball（codeload 生成的 SNAP-<sha>.tar.gz）与 Debian .orig 的
sha256 **必然不等**：目录名（SNAP-4ad1e95…/ vs snap-2013-11-29/）、gzip 压缩
参数、且两者内容本就不同版本（见上节第 1 条）。本包以 **内容级清单比对**
（106 文件逐文件 sha256）替代归档层 sha 相等性：.orig 的内容 = 官方
2013-11-29 快照剔除点文件，构建相关文件无一字改动。

## 源码修改

- `patches/0001-snap.c.patch`（refresh-patch --auto 生成，与探索阶段手改逐字
  等价）：注册 `--help`/`--version` 长选项（K0 CLI 契约；上游 zoe 解析器只认
  单横线）。共 4 行新增，无平台宏（PF5 合规）。
- 无其他源码改动；Makefile 未改（CC/CFLAGS 经 make 变量覆盖注入）。

## K0 实测证据（主命令 snap）

| 探针 | rc | 输出 |
|---|---|---|
| `snap -help` | 0 | 51 行帮助页，首行 `The general form of the snap command line is:` |
| `snap --help` | 0 | 与 `-help` 输出 `cmp` 逐字节一致 |
| `snap --version` | 0 | 恰一行 `snap 2013-11-29` |
| `snap`（无参） | 1 | usage + `SNAP - Semi-HMM-based Nucleic Acid Parser (version 2006-07-28)`（2006-07-28 是 Zoe 库版本日期，非包版本） |

注：上游 2013 代码没有任何版本选项，`--version` 为 0001 补丁新增（K0 口径
"名匹配走最小补丁"，已留证）。探索采样文件：
`~/tmp/uc2/snap-2013-11-29/exp/k0_*.txt`。

## 上游测试台账（R51 三步法）

1. **清点**：源码树无 tests/ 目录；Makefile 仅 default/gcc/clean/depend/tar
   五个目标，无 check/test；无 ctest/pytest/meson 注册；唯一"测试性"资产是
   example.zff（ZFF 样例标注）与 DNA/ 示例序列，供人工验证。**上游可执行
   测试 = 0 个**（申报表见 test_package/MANIFEST.yml）。
2. **实跑**：上游无测试可跑（0/0）；"无测试"结论附清点证据如上。
3. **回填**：消费者测试自行设计（见下）。

## 消费者测试（test_package，9 项断言全 PASS）

`test_package/test.sh`（VirtualRunEnv + bash 直执行，OHOS mksh 不能直接跑
ELF）：

1. `snap --version` rc=0（断言 1）且输出恰为 `snap 2013-11-29`（断言 2）；
2. `snap -help` rc=0（断言 3）且含 `The general form of the snap command line is`（断言 4）；
3. `snap --help` rc=0（断言 5）且与 `-help` 输出一致（断言 6）；
4. **真实基因预测**：`snap <pkg>/res/HMM/minimal.hmm sample.fa -gff` rc=0
   （断言 7），stdout 逐字等于确定性预期行
   `sample\tSNAP\tEinit\t1010\t1387\t10.597\t+\t.\tsample-snap.1`（断言 8）；
   sample.fa 为内嵌的拟南芥 DNA 前 1500bp（纯 ACGT 构造输入，linuxinfo
   喂构造 cpuinfo 同款思路）；同输入双跑 `cmp` 逐字节一致（确定性已证）；
5. `hmm-info <pkg>/res/HMM/minimal.hmm` rc=0（断言 9，该 HMM 上游即为空输出，
   rc=0 即语义正确）。

conan-verify G2 内 test_package 实跑：6 项 CLI 断言 PASS 在案
（reports/conan-create.log，HMM 路径修复后全 9 项 PASS）。

## 依赖版本

零外部依赖（W0 preflight：无依赖声明，preflight_check PASS）。
构建工具：make 4.4.1 / clang 15.0.4（设备自带）；Conan 2.29.1（OHOS 适配版）。

## 验证结果

```
$ python3 scripts/ohc-run.py conan-verify snap 2013-11-29
G0 ✅ PASS（预构建风险评估）
G1 ✅ PASS（配方完整性）
G2 ✅ PASS（conan create 干净构建 + test_package 9 断言）
G3 ✅ PASS（系统同名库隔离 R26）
G4 ✅ PASS（产物完整性）
L2 ✅ PASS（平台功能矩阵 smoke test）
L4 ✅ PASS（静态安全扫描 checksec）
L5 ✅ PASS（产物基线对比）
**Verdict**: PASS（reports/conan-verify-report.md）
```

产物：`bin/`（snap 145792B、fathom 166272B、forge 154048B、hmm-info 133504B、
exonpairs 137600B）+ `res/HMM/`（28 个 .hmm + 别名/README 共 33 文件）。

## B 判定终判：none

SCT 初判 none，本轮复核维持 **none**。终判依据（按"当轮第一条真实错误 +
KB 覆盖面"口径）：

- 本任务仅有的两条可知识化问题：①clang `-fno-common` 链接冲突——知识图谱
  在 G2 阶段自动命中 E540（评分 10041，shadow-ci/runner-path-prepend 族），
  且 -fno-common 类问题在 KB 属已知同层条目（gcc10-fix 为上游界公共知识），
  不满足「KB 无同层条目且可跨库复用」；②JC full/incremental 模式退化与
  conan 生成物落 test_package——均为本仓框架自身的操作面知识（L1 平台真理
  已在 AGENTS/手册层覆盖），非跨库可复用的编译配方知识。
- 结论：无可创建的新机制条目，不升 create，不出 DRAFT 成对草稿。
---

**编译结束**: 2026-09-27 02:08
**最终状态**: built
