# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_66bebd17.md`

---

## 背景

- **软件名称**: pcc-libs
- **版本**: 1.2.0-devel-20211015
- **构建日期**: 2026-10-02
- **构建系统**: autotools
- **上游仓库**: https://github.com/PortableCC/pcc-libs/archive/5fd7d9e3441968c03914cdc1e963ea55a943284b.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 6
- **编译依赖**:
无
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: autotools；conan create EXIT=0，test_package 真机原生 46/46 |
| conan-verify | 配方验证 | 通过 | EXIT=0，G0/G1/G2/G3/G4 全 PASS；G0 命中原库知识 E490（autotools helper 可执行位）但 G2 实测通过 |
| finish | 归档收尾 | 完成（带告警） | EXIT_REASON=finish_success，manifest→built，.ci-result.json exit_code=0；step5b(知识完整性，涉及他人 E219/E253/E305) 与 step8(gen_summary 工具缺陷) 告警，均为非本包问题 |
| submit | PR提交+AI检视+CI | 未执行 | 按任务约束停在 LOCAL_AUDIT_PASS 等待人工确认，未 commit/push/PR | AI Review: 未开始（本地 W4 审计已 PASS，P0/P1=0） |

### 失败与问题

- **1**: 根因=`system 'ohos' not recognized`, 解决方案=上游 config.sub 不认识 OHOS
- **2**: 根因=config.guess 在真机上报 `unable to guess system type`, 解决方案=`uname -s` 返回 HarmonyOS，2021 年代 config.guess 不识别；且该年代分支是 `echo`/`exit` 风格，末尾没有 `echo $GUESS`
- **3**: 根因=`'aarch64-unknown-linux-ohos' is not (yet) supported`, 解决方案=平台白名单只有 linux/darwin/… 等
- **4**: 根因=`ohos*)` 分支不生效, 解决方案=`config.sub` 把目标 OS 规范化为 `linux-ohos`，而 shell 的 `case` 模式是**前缀匹配**，`linux*)` 会先生效
- **6**: 根因=复数例程段错误（`__muldc3`/`__mulxc3`）, 解决方案=signbit.c 用 `__FLOAT_WORD_ORDER__` 选字序，但 **clang 不定义该宏**；未定义 ≈ 0，恒等于"非小端"，`__signbitl/__signbitd` 读到尾数位
- **7**: 根因=双精度算术全部返回垃圾值（真机实测，addsf3 正确而 adddf3 错误）, 解决方案=上游 `libsoftfloat/arch/aarch64/aarch64-gcc.h` 用 32 位 ARM 宏 `__VFP_FP__`/`__ARMEB__` 判断是否对 double 做 FPA 字交换；aarch64 编译器两个宏都不定义，误入字交换分支，所有 double 位模式被前后 32 位对调
- **8**: 根因=csu 不产出任何目标文件, 解决方案=csu/Makefile.in 只在 `csu/$(TARGOS)/` 存在时才构建

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 8 条
- **引擎命中情况**: 草稿目录 2770 条
- **测试统计**: 总计 46, 通过 46, 失败 0, 跳过 0
- **未覆盖的错误模式**: 3 类（知识图谱中均无对应 E-entry）
  1. **toybox `mktemp -d` 在 umask 077 下产出 2700 目录，构建进程无法写入** —— autotools
     `config.status` 因此报 `./confXXXXXX/subs1.awk: Permission denied` /
     `could not setup config files machinery`，与配方源码完全无关。宿主 `mktemp`（/system/bin、
     /usr/bin、/bin 三处皆 toybox）产物属主为存储 ACL 映射用户、组位不可写；而 `mkdir` 产物为 2771
     可写。conan 的 buildenv 会显式前置 `/storage/.../usr/local/bin`，需把包装装到该目录才生效。
  2. **W3 的 `trap EXIT` 还原在预下载改写后未生效** —— conandata.yml 残留
     `gh-proxy.com` 镜像列表（PF7 命中），而 finish 内部再跑 conan-verify 会注入 ghfast.top
     并在失败路径上中断 trap。必须用构建前快照比对还原（本次已还原并逐字节验证）。
  3. **W3 JC 门禁在 worktree 未提交时退化为 full 模式** —— 无提交 ⇒ `git diff origin/main...HEAD`
     为空 ⇒ 回落 `git ls-files` 全仓扫描，命中他人已合入 main 的 5 个隐藏文件
     （cloog/kics/libbfio/thc 的 .build-closed/.staging-verified），与本包无关却阻塞 W3。

### AI 检视结果

- **检视阶段到达**: 未到达（本地停止，未 push 未建 PR）
- **变更摘要评估**: 由独立子任务（上下文隔离）执行 W4 Pre-PR 审计，verdict=pass，无 P0/P1，
  2 项 P3（R6 补丁 0002 同时改预生成 configure 的例外说明、R49 补丁 0006 内 /usr/local 默认值已被覆盖）
- **检视意见数量**: 0（尚未进入远端 AI 检视）
- **检视意见处理**: 不适用；本地已把两项 P3 观察固化进
  reports/audit-result.json（含 15 个被检文件 sha256 佐证，满足 R52）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 未知
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 3
  1. `finish` Step5 —— W3 本地 CI 模拟失败（JC 门禁 full 模式命中他人包隐藏文件）
  2. `feedback` —— 骨架生成后 14 处占位符待补（预期内的一次交互，已全部填充）
  3. （另有一次非 HANDOFF 但等价的阻塞）conan create 复跑 7 次连续失败于
     `config.status: Permission denied`，非工具 HANDOFF 但需人工定位根因 32 分钟
- **重试次数**: 构建侧 8 次（7 次失败 + 1 次成功）；`finish` 3 次（第 1 次 JC 阻塞、
  第 2 次补 test-report 后 W3 通过、第 3 次确认终态）
- **关键瓶颈**: 宿主机 `mktemp`/`chmod` 行为异常（toybox 版本 + 存储 ACL 映射）导致
  autotools `config.status` 无法创建临时目录，且 `chmod` 是空操作、`/tmp` 只读，
  使常规规避手段全部失效；定位耗时长，因为它伪装成配方问题（报错出现在 configure 阶段）
- **耗时较长的步骤**: ① 环境根因定位约 32 分钟（7 次失败复跑 + 权限/ACL/umask 交叉验证）；
  ② W3 JC 门禁模式判定约 15 分钟（读 junk_check.sh 三级优先级 + 验证 prdiff 口径）；
  ③ W4 审计工具适配约 12 分钟（`pre_pr_audit.py` 依赖 `base...head` 三方 diff，
  worktree 未提交时取不到文件并回落到他人 `main` 引用，误报 267 个无关文件）

---

## 建议

### SKILL 设计改进

1. **W3 的 JC 门禁应显式声明扫描范围，或对未提交工作区强制 prdiff 口径**（本次阻塞根因）。
   `junk_check.sh` 优先级为 prdiff → incremental → full，而 worktree 场景下
   `git diff origin/main...HEAD` 必然为空（改动未提交），于是退化为 `git ls-files` 全仓扫描，
   命中**他人已合入 main** 的 5 个历史隐藏文件（cloog/kics/libbfio/thc 的
   `.build-closed`/`.staging-verified`），把与本包无关的存量问题算到本次 W3 头上并阻塞
   finish。建议：`workflow_checks.run_local_ci` 在调用 `build_and_test.sh` 前，
   用 `git add -n <pkg_dir>` 或显式包目录合成 `JUNK_PR_DIFF`（与远端 CI checkout-pr 同口径），
   或至少把 full 模式下命中"非本包路径"的文件降级为 warn 而非 fail。

2. **`finish`/`conan-verify` 的镜像注入必须无条件还原，且要覆盖崩溃路径**。
   本次 `conandata.yml` 在 finish 结束后仍残留 `gh-proxy.com` 镜像列表（PF7 实测命中），
   需人工按快照还原。虽然 SKILL 已用 `trap EXIT` 兜底，但 trap 在同进程后续步骤
   中断/异常时不可靠。建议：写入前先在内存保存原文，还原动作改为"幂等 + 多挂点"
   （build 结束、G2 结束、finish 收尾各校验一次），并在 conandata.yml 上建
   `sha256` 指纹文件，任何后续步骤读到时先比对再使用。

3. **W4 审计工具（`pre_pr_audit.py`）不支持未提交工作区**。
   其文件集来自 `git diff origin/main...HEAD`，worktree 且未 commit（任务明文禁止 commit）时
   取空并回落到本地 `main` 引用——本机 main 指向**另一任务 worktree**的分支
   （task-C/keydb @172d7d38e0），于是列出 267 个无关文件，审计输入完全失真。
   建议：`generate` 增加 `--files-from` / `--use-worktree`（合并 `git status --porcelain`
   与 `git add -n` 结果），并在检测到 HEAD == base 时给出明确提示而非静默回落。
   同理 `preflight.run_preflight(base, head)` 的调试入口也不适用于未提交改动。

4. **`--output` 语义不一致**：`pre_pr_audit.py generate --output` 期望**文件路径**，
   但 help 写"审计输入输出路径 (默认 /tmp/)"，本次传目录导致
   `IsADirectoryError`。建议 help 明确"文件路径（非目录）"。

### 模板改进

1. **`templates/test-report.md` 缺少"上游测试清点"专节**（R51 强制项）。
   模板只有「测试摘要/结论/详情/环境」，「上游 N/N′/通过率」口径无处填写，
   容易导致 AI 把"上游 0 项、补全 46 项"混写成单一数字。建议在 §一 前增加
   「上游测试清点」节：tests/ 目录数、ctest/pytest 注册数、清点命令与原始输出、
   以及"上游确无测试"的申报位。

2. **模板缺少"平台适配问题"与"上游缺陷（未修改）"分区**。
   本次 5 个问题（含跨平台缺陷根因）与 1 个上游既有缺陷（`__divsf3` 恒返 0）
   性质不同：前者是适配工作，后者必须明确"如实记录、未修改、无断言"以免被
   误判为漏修。建议模板固定增设这两节，避免每个包自由发挥。

### 自动化补全

1. **宿主环境体检应前置到 `check-env`**：本次踩到 3 个宿主异常
   （`mktemp` 产物不可写、`chmod` 空操作、`/tmp` 只读）。
   建议 `check-env` 增加探针：`umask 077; mktemp -d` 后尝试在其内建文件、
   `/tmp` 可写性、`chmod` 是否真实生效。任一异常则给出明确告警与规避方式，
   可省掉本次 32 分钟定位。

2. **W3/finish 前自动做 conandata.yml 指纹校验**：进入 W3 前记录 `sha256`，
   W3/verify 结束后比对；不一致则自动还原并在日志中显式打印"已还原"，
   而不是依赖 trap 的成功执行。

3. **feedback 骨架的自动填充率可提升**：本次 14 处占位符中有 5 处
   （conan-verify 结果、finish 结果、W3 结果、测试统计、失败列表）工具侧已有数据源
   （`.ci-result.json`、`conan-verify-report.md`、`w3-local-ci.log`、notes.md），
   可自动填入，仅保留主观建议类占位符给 AI。

### 知识图谱覆盖

建议新增 4 条 E-entry（均与本次真实踩坑对应，图谱中暂无）：

1. **autotools `config.status` 在 HarmonyOS PC 报 `subs1.awk: Permission denied`** ——
   根因是 toybox `mktemp -d` 在 `umask 077` 下产出 `2700` 目录，而构建进程的 uid 与
   存储 ACL 映射属主不同、仅属组可写；`mkdir` 产物为 `2771` 可写，`chmod` 又是空操作。
   修复：在 conan buildenv 显式前置的目录（如 `~/.local` 或 profile 里的
   `PATH=+(path)...` 首项）放一个按 `mkdir` 实现的 `mktemp` 包装。

2. **W3 预下载镜像改写残留 `conandata.yml`（PF7/JC1 命中）** ——
   `trap EXIT` 在构建中断/同进程后续步骤失败时不可靠，必须用构建前快照比对还原；
   提交前确认 conandata.yml 无 `file://`、`gh-proxy`、镜像前缀。

3. **worktree 未提交时 `junk_check.sh` 退化 full 模式，误拦他人包存量文件** ——
   识别特征：W3 报 `Junk Files: N` 且列出路径不属于本包；处置：以 `JUNK_PR_DIFF`
   提供真实 PR 清单（`git add -n` 结果加 `+++ b/` 前缀）。

4. **`pre_pr_audit.py` / `preflight` 在 worktree 未提交时误取他人 `main` 引用** ——
   识别特征：审计输入列出数百个无关文件；处置：审计输入改用 `git add -n` 的真实清单，
   或先 commit（本任务被明确禁止时只能自建输入）。

---

## 作者

- **姓名**: Yunan0718
- **邮箱**: 2801558242@qq.com
- **Agent ID**: 6210
- **生成时间**: 2026-10-02 23:52:29
- **PR 编号**: —
- **Git Commit**: 67fbdde039
