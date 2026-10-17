# DRAFT-autotools-tarball-in-tree-residue-vpath-configure

> 上游 tarball 携带 in-tree configure 残留（config.status/config.log/config.h/stamp-h1/Makefile）时，Conan VPATH 构建必触发 `source directory already configured`，应在 source() 按清单清理残留。

- 状态：草稿（Curator 判定产出，未审核；最终编号 Exxx 由知识库主编确认）
- 申报域：**构建系统语义**（八分类之一）
- 机理分层：**L2 跨库工程模式层**——第二实例：advancescan/1.18 notes 记录同一 error signature；配方树 grep 出 103 个 conanfile.py 含同样的 "config.status" 清理实践（≥3 门槛大幅超过）
- 阻塞面：**构建失败**（configure 硬错误退出 1，命中常见阻塞面判据）
- 来源：didiwiki/3.0.5 run CI 第 4 轮真实失败

## 问题特征（真实失败证据）

- 本 run：`builder/ci-run-4.log:175` → `configure: error: source directory already configured; run "make distclean" there first` → conan create 失败（build() 内 autotools.configure() 报 Error 1）。
- 第二实例：`archives/a/advancescan/1.18/notes.md`（对话 #1，2026-06-16）：`ohc-run.py build advancescan 1.18` 因"源码目录已有旧配置残留"报同一 `source directory already configured`。
- 机理侧证：同一 generated autoconf 宏见 `archives/a/advancescan/1.18/patches/0008-configure.patch:3762-3764`（`test to see if srcdir already configured` → `as_fn_error ... "source directory already configured..."`）。

## 根因（完整因果机理链）

1. **上游发布习惯**：部分 autotools 项目直接从已构建的源码树打 tarball 发布；didiwiki 3.0.5 tarball（112 条目）自带 config.h、config.log、config.status、stamp-h1、顶层与 src/scripts/docs 三级 Makefile 全套残留。
2. **触发命令**：Conan basic_layout/VPATH 约定下，源码复制到 build folder，在 build 目录执行 `sh <src>/configure`。
3. **失败点**：generated configure 检测到 srcdir 存在 config.status，判定源目录已按另一构建目录配置过，直接 `as_fn_error` 退出 1 → conan build 失败。
4. **归类**：上游归档卫生 × autoconf VPATH 检测语义 × Conan VPATH 构建约定的确定性冲突。
5. **修复依据**：残留文件全部由本次 configure 重新生成（config.status/config.h/stamp-h1/Makefile 均为 configure 输出），按清单删除不损失任何上游语义。

## 修复方案（rec）

1. recipe source() 解包后按固定清单删除残留（本 run 落地形态：`archives/d/didiwiki/3.0.5/conanfile.py` source() 内 residues 列表：config.status、config.log、config.h、stamp-h1、Makefile、src/Makefile、scripts/Makefile、docs/Makefile），逐项存在性判断后 os.remove。
2. 清单按 tarball 实际内容定制（解包后 ls / tar 清单核对），不盲目 rm -rf。

## 回退方案（fallback，诚实权衡）

- 手动 `make distclean`。权衡：依赖残留 Makefile 本身完好且 distclean 目标行为由上游定义；E434 copystamp 先例证明个别包的 distclean 会连带删除需保留的分发文件，确定性不如按清单删除，仅作退路。

## 禁止策略（forbid）

- **禁止**为迁就残留改用 in-tree 构建（源目录直接 configure/make）或用 `--build/--host` 绕过配置。
  reason：in-tree 构建与 Conan basic_layout/VPATH 约定冲突，E434 已证 in-tree 下 copystamp 类目标 cp 同文件失败；`--build/--host` 绕过触发 P-AUTOTOOLS-001 自动拒绝。
  consequence：二次 configure 互相污染、构建产物混入源目录与打包层，跨轮次缓存复用时报错漂移，进入不可收敛修复循环。

## verification_cmd（自包含，已固化实测输出）

```sh
# error signature 已由两个 run 真实日志证实（ci-run-4.log:175、advancescan/1.18 notes）。
# 2026-09-10 Builder 在 ohpc2 真机 fresh sandbox 实测（tarball SHA-256
# 290aee7fe2efc8f1c2612b6aff2bb832d3c8129e6fd9dd9e6adbdb02d1f19aef，与官方双源核验一致）。

# (1) 门禁复现：带残留的源目录上 VPATH configure → 首行即败
tar xzf ciwiki-3.0.5.tar.gz && mkdir b && cd b && sh ../ciwiki-3.0.5/configure --prefix=/tmp/probe
# → configure: error: source directory already configured; run "make distclean" there first
#   （任何 checking 输出之前，configure 退出 1）

# (2) 残留核验：解包后顶层即见全套 8 件 in-tree 产物
ls ciwiki-3.0.5/
# → Makefile  config.h  config.log  config.status  stamp-h1 …（另有 src/ scripts/ docs/ 三级子目录 Makefile）

# (3) 清理残留（逐个明确路径）后同命令 → 门禁消失、正常进入 checking
rm ../ciwiki-3.0.5/config.status ../ciwiki-3.0.5/config.log ../ciwiki-3.0.5/config.h \
   ../ciwiki-3.0.5/stamp-h1 ../ciwiki-3.0.5/Makefile ../ciwiki-3.0.5/src/Makefile \
   ../ciwiki-3.0.5/scripts/Makefile ../ciwiki-3.0.5/docs/Makefile
sh ../ciwiki-3.0.5/configure --prefix=/tmp/probe
# → checking for a BSD-compatible install... / checking whether build environment is sane... yes / …
#   （实测不再出现 already configured：9 项 checking 正常输出；显式 CC 时推进到
#    "configure: creating ./config.status"；裸 PATH 探针 shell 无 C compiler 时止于编译器检测——
#    尾部差异均为探针沙箱环境因素，与残留门禁无关）
```

## 知识沉淀价值

- **可复用问题类别**："上游从 in-tree 构建树直接打包发布"的归档卫生问题在 VPATH 构建约定下的必踩面；小项目 tarball 常见（didiwiki、advancescan 两例均命中）。
- **适用库/构建链**：任何 autotools 库 + Conan 2.x basic_layout/Autotools helper；对非 Conan 的 VPATH 构建同样成立（机理在 autoconf）。
- **对未来诊断的改进**：configure 一开场就报 `source directory already configured`（而非跑完若干 checking 后失败）即可秒判为残留问题，直接查 srcdir 的 config.status，避免误判为工具链/平台问题。
- **为何不是一次性补丁**：机理在 autoconf generated 脚本与发布习惯（跨库可复现），配方树 103 处同模式实践证明是持续性工程惯例而非单库特例。

## 确认去重证据（实际检查范围、检索词、命令与逐项差异）

- 检查范围：设备 baseline 仓 `knowledge/graph/`、`knowledge/drafts/`（987 个文件）、`knowledge/doc/`；经验仓 `ophs_ci_review/` 全目录。
- 检索词与命令（设备端 grep，2026-09-10）：
  - `grep -rn 'already configured' knowledge/` → **零命中**；
  - `grep -rli 'distclean\|already configured' knowledge/` → 仅 E082、E434（distclean 字样）；
  - `grep -rli 'vpath\|in-tree\|构建残留' knowledge/` → E041（bypass-autotools）、E110（use_alternate_build_dir）、E434（copystamp 须 VPATH）、E442（宿主 ABI）、DRAFT-audacious（in-source 静态链）、DRAFT-autoconf269、DRAFT-ci-l4、DRAFT-gnustep；
  - `grep -rn 'already configured' archives/` → advancescan/1.18 notes + 各 generated aclocal.m4；
  - `grep -rln '"config.status"' archives/ --include=conanfile.py | wc -l` → **103**；
  - 经验仓 `grep -rln 'already configured\|distclean' ophs_ci_review/` → 零命中。
- 逐项差异：
  - E082「configure-twice」：机理是 gnulib stdbool 检测在二次 configure 时 sed 读不到 conftest.c，修复是 distclean 后重configure——**同词不同因**，与本条"tarball 残留 × VPATH 首次 configure 即败"不同。
  - E434「copystamp 须 VPATH」：方向相反——E434 论证必须 VPATH，本条解决 VPATH 前置条件（srcdir 残留），互为补充，已挂 similar_to。
  - E110 use_alternate_build_dir、E041 bypass-autotools：分别针对构建目录选择与绕过 autotools，不含残留清理。
- 结论：现有知识库与经验仓均无本条覆盖；且已有第二实例（advancescan）与大规模配方实践（103 处）支撑 L2 准入，非重复申报。

## 适用判断

- 适用：configure 在输出任何 checking 前即报 `source directory already configured; run "make distclean" there first`；tarball 清单含 config.status/stamp-h1。
- 不适用：configure 中途失败（工具链/平台检测问题，分流 E011/E434 等）；distclean 语义被上游改写的包（直接按清单删除）。
