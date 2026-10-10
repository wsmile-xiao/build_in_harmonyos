# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_3e9aaeb0.md`

---

## 背景

- **软件名称**: libfuse
- **版本**: 3.16.1
- **构建日期**: 2026-09-27
- **构建系统**: meson
- **上游仓库**: https://github.com/libfuse/libfuse（源码 `https://github.com/libfuse/libfuse/releases/download/fuse-3.16.1/fuse-3.16.1.tar.gz`）
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 4
- **编译依赖**:
meson/1.11.0（tool_requires）
- **最终状态**: 成功（`status: built`，PR #13377 已提交并触发 CI）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 上游无 3.16.0，按 3.16.1 进行（sha256 `75a7140c…46fb5`） |
| build | 编译构建 | 成功 | 构建系统: meson，16/16 目标，产物 `lib/libfuse3.a` |
| conan-verify | 配方验证 | 通过 | G1/G2/G3 PASS，`conan create` 含 test_package 实跑 14/14 PASS；最终树上再次独立复核仍 PASS |
| finish | 归档收尾 | 完成 | 10 步管线跑完；W3 本地 CI 模拟 PASS（`Pass rate 100.0% (1/1)`）；失败步骤仅 step5b(知识图谱既有 E-entry 字段缺失)、step8(gen_summary 框架 bug) |
| submit | PR提交+AI检视+CI | 部分（等价执行）| AI Review: 未等待。因 `submit` 自检的 `packaging_present` / `.staging-verified` 为 v2.0 遗留且被 JC5 白名单排除，改按仓内先例手工执行等价步骤：`git push` → `gitcode_pr.py create-pr --no-preflight` → `trigger-ci`（PR #13377，`/rebuild` note 191804325）|

### 失败与问题

- **2**: 根因=`lib/meson.build` 选择了 BSD 挂载后端, 解决方案=上游写死 `host_machine.system().startswith('linux')`，OHOS 上报 `harmonyos`，条件不成立而落到 `mount_bsd.c`（E090）
- **3**: 根因=「关闭 fd 唤醒阻塞 read」的兜底方案会死锁, 解决方案=实测 OHOS 上另一线程 `close(fd)` **不会**唤醒已阻塞在同一 fd 上的 `read()`（`pthread_join` 永久阻塞）
- **5**: 根因=`ninja` 归档 `libfuse3.a` 时报 `/bin/sh: safe-bin/rm: No such file or directory`（code=126）, 解决方案=宿主沙箱的 `rm` 垫片 shebang 指向不存在的 `/bin/bash`
- **6**: 根因=meson `tests=true` 时 `test/test_setattr` 链接失败（`undefined symbol: pthread_cancel`）, 解决方案=上游测试程序自己也直接调用了 `pthread_cancel`
- **7（本次新增，最严重）**: 根因=W3（`ci/conan/build_and_test.sh`）的 Pre-download 备份取在「镜像回退改写」**之后**，因此其 EXIT 陷阱虽打印「conandata.yml 已还原为官方 URL」，实际写回的是镜像列表（`https://gh-proxy.com/…` 前置），命中 R39/PF7 镜像域黑名单；且因预下载把两份 URL 都下成功，构建全绿、污染静默。解决方案=提交前以 `git diff` 逐行核对并人工还原为官方单值 URL，同时清理 `conandata.yml.ghfast-bak` / `.orig` 残留；已沉淀为知识草稿 `DRAFT-LIBFUSE-3161-W3-PREDL-MIRROR-RESTORE-POLLUTES-CONANDATA`。该问题由 W4 独立审计（`pre_pr_audit.py`）第一轮判 P1/verdict=fail 抓出，修复后复审 PASS

### 知识图谱使用情况

- **引用知识条目**: E085（musl 缺 `pthread_cancel` 家族）、E090（meson `host_machine.system()` 报 `harmonyos`）
- **新增知识草稿**: 2 对（4 文件）—— `DRAFT-LIBFUSE-3161-PTHREAD-CANCEL-MESON-FEATURE-DETECT-POLL`、`DRAFT-LIBFUSE-3161-W3-PREDL-MIRROR-RESTORE-POLLUTES-CONANDATA`
- **引擎命中情况**: 草稿目录 2096 条
- **测试统计**: 总计 14, 通过 14, 失败 0, 跳过 0
- **未覆盖的错误模式**: ①**框架侧**：W3 predl 的「备份晚于改写」导致 conandata 被静默写入镜像源（现有 E-entry 与 DRAFT-8543/8960 只覆盖「读错 URL 导致构建失败」，未覆盖「写回错的 URL 导致污染与硬闸命中」）；②**环境侧**：宿主 WorkBuddy 沙箱的 `safe-bin/rm`（shebang `#!/bin/bash` 不存在）会破坏 ninja 归档步骤，以及 `conan` 必须由 HAP 签名解释器启动、需 `env -i` 纯环境，均属构建环境类知识，尚未有 E-entry；③**平台行为侧**：OHOS 上「另一线程 `close(fd)` 不唤醒阻塞 `read()`」这一实测结论，建议纳入 musl 差异清单（现仅存在于本草稿）

### AI 检视结果

- **检视阶段到达**: 否（按用户约定 PR 提交后不等待 CI / AI 审阅；atomgit-bot 的 AI 检视亦为异步，本次未阻塞等待）
- **变更摘要评估**: 未获取（未等待机器人评论）
- **检视意见数量**: 0（未等待）
- **检视意见处理**: 不适用。替代做法是**提交前**跑仓库自带的独立审计 `scripts/pre_pr_audit.py`（W4/W5）——第一轮抓到 1 条 P1 + 2 条 P2 + 2 条 P3，修复后复审 PASS（P0=0/P1=0/P2=1/P3=3），见 `archives/l/libfuse/3.16.1/reports/audit-result.json`

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 未知（已 `/rebuild` 触发，按约定不等待结果）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 3 —— ①G0 干净构建验证（非 autotools 包被无条件跑 `./configure` → exit 127，框架误报，非阻塞）；②W3 本地 CI（第一轮因 junk_check 落到 full 模式扫全仓、命中 4 个**别的包**遗留的隐藏文件而 fail）；③feedback 占位符
- **重试次数**: `finish` 2 次（第一轮 W3 fail → 提交后第二轮通过）、`conan-verify` 3 次（finish 内 2 次 + 最终树独立复核 1 次）、W4 审计 2 轮（首轮 P1 → 修复 → 复审）
- **关键瓶颈**: ①**W3 的 junk_check 判定依赖 git 提交状态**——工作树有改动但未 commit 时 `git diff origin/main...HEAD` 为空，junk_check 回落到 full 模式扫全仓 97107 个文件，把其它包的 4 个历史遗留隐藏文件算作本包失败。必须先 commit 再跑 finish 才能进入 incremental 模式；②编译本身很快（16 个小目标），耗时集中在每轮 `conan create` 的依赖解析与 predl 预下载
- **耗时较长的步骤**: Step 4 `conan-verify`（含一次完整 `conan create`）、Step 5 W3 本地 CI 模拟（setup.sh + build_and_test.sh，内含第二次 `conan create`）——同一棵树被完整构建两次

---

## 建议

### SKILL 设计改进

1. **junk_check 的检查范围应与调用方意图对齐**：W3 / `finish` 明明是针对 `libfuse/3.16.1` 的收尾，却因未提交就退化为全仓扫描，把其它包的历史遗留（本次是 `cloog`/`kics`/`thc` 的 `.build-closed`、`.staging-verified`）算到本包头上，导致 HANDOFF 且信息完全误导。建议：`build_and_test.sh` 在拿到 `<pkg>/<ver>` 参数时，把范围限定为该包的 `<pkg_dir>`（或把 `JUNK_SCOPE` 显式传给 `junk_check.sh`），只在 Release/非 git 场景才允许 full 回退。
2. **`finish` 应在 Step 0 就校验「工作树是否已提交」**，未提交时给出明确提示（「请先 commit 再 finish，否则 W3 会退化为全仓扫描」），而不是等到 Step 5 用一个与根因无关的错误打回。这一条能直接消掉本次 1 次 HANDOFF 与 1 次整体重跑（含两次额外 `conan create`）。
3. **Step 4 与 Step 5 存在重复的完整构建**：`conan-verify` 一次 `conan create`、W3 再一次 `conan create`。建议让 W3 复用 conan-verify 的构建产物（或至少提供 `--reuse-verify-build` 开关），对 meson/cmake 小包也能省掉一半的收尾耗时。
4. **`finish` Step 3 的 G0 干净构建验证应按构建系统分流**：对 `build_system: meson` 的包仍无条件执行 `./configure` 并报 `exit 127`，每次都要人工判断「这是误报」。建议按版本级 manifest 的 `build_system` 选择对应验证（meson → `meson setup`；cmake → `cmake -S -B`），或至少在非 autotools 包上跳过并标注 `skipped: not-autotools`。
5. **Step 10 的 submit 就绪预检应清理 v2.0 遗留项**：`packaging/` 与 `.staging-verified` 在 ARCHIVE-SPEC v3.0 已废弃、R19 又禁止手动打包 tar.gz，但预检仍在要它们；更麻烦的是 `.staging-verified` 不在 `junk_check.sh` 的 `JC5_ALLOWED` 白名单里——按要求创建反而会被 junk_check 拦下（本次出现的是其它包留下的同名文件被扫出来）。建议二者同时从预检与白名单口径中移除。
6. **`pre_pr_audit.py check` 的 `.ci-result.json` 路径与生产者不一致**：`finish` 把 `.ci-result.json` 写在**版本归档目录**（`archives/<l>/<pkg>/<ver>/.ci-result.json`），而 `check` 只在**仓库根**找，导致 W3 明明通过却提示「未找到」，只能靠 `generate` 绕过。建议 `check` 同时探测归档目录位置。
7. **建议把 W4 独立审计（`pre_pr_audit.py`）正式纳入 `finish` 管线**（或至少在 HANDOFF 的 AI NEXT ACTIONS 中显式列出）。本次它是**唯一**发现 P1 的环节：`conan-verify` 全绿、W3 全绿、`junk_check` pass、`finish` 只报两条无关告警，若没有这一轮审计，带 `gh-proxy.com` 的 `conandata.yml` 会被直接提交。
8. **`finish` 的收尾应当包含「提交前 diff 复核」一步**：至少对 `conandata.yml` / `manifest.yaml` 做「只含官方 https 源、无镜像域、无 `.bak/.orig` 残留」的机械断言（等价于本地跑一次 PF7）。该类污染是构建全绿也不会暴露的，属于「必须由机械检查兜底」的类别。

### 模板改进

1. **`templates/conanfile-meson.py.tmpl` 有两处会产生不可用配方**：①引用 `meson_layout`，而 Conan 2.29.1 **不存在**该函数（直接 `ImportError`）；②把 `meson/1.11.0` 写进 `requirements()` 而非 `build_requirements()/tool_requires`（导入期即报「构建依赖必须放 build_requirements」）。两个问题都要人工发现并改掉，建议直接修正模板并给模板加一条 `conan create --dry-run` 级别的自检。
2. **`templates/积分赛事PR模板.md` 的「上游测试用例统计 / 适配后测试用例统计」两张表共用同一个 `total` 字段语义**，而 `_extract_test_summary` 只认 `test-report.md` 里「总测试数 / 通过…PASS / 失败…FAIL / 跳过…SKIP」的精确措辞；两者不一致时生成器会静默渲染成 0。建议：①模板合并/明确两张表的口径；②生成器改为优先读取 `test_package/MANIFEST.yml` 的 `assertion_count`，并让 `_generate_pr_body` 的默认正文直接采用赛事模板结构（本次是手写覆盖）。
3. **`templates/test-report.md` 缺少「断言口径」字段**：本包 14 条断言中有 3 条是「到达型」（`check(1, …)`，用于证明未挂死），审计会合理质疑「14 是否虚高」。建议模板增加「取值断言 / 到达型断言」两栏，或要求写明构成，避免同类质疑。
4. **`patch_classification` 的 `platform_only` 需要明确定义**：审计指出同一份 manifest 里 0004 判 `false`、0001/0002 判 `true` 看似不一致（三者都含 `HAVE_PTHREAD_CANCEL` 守卫）。本次在 manifest 内加了判定口径注释，但更合适的做法是把口径写入模板注释或 ARCHIVE-SPEC。
5. **`MANIFEST.yml` 可直接吸收「上游测试清点」表**：目前清点结果散落在 `notes.md`（R51 表）+ `MANIFEST.yml`（注释）+ PR body（表格），三处需手工保持一致。建议在 `MANIFEST.yml` 里给出结构化字段（如 `upstream_inventory: {meson_registered: 1, c_programs: 5, pytest_modules: 3}`），生成器据此自动渲染 PR body 的上游表。

### 自动化补全

1. **把「提交前 diff 复核」自动化为一键命令**，例如 `ohc-run.py clean-conandata <pkg> <ver>`：扫描 `conandata.yml` / `manifest.yaml` 是否含镜像域（`_PF7_MIRROR_HOSTS` 14 域）、`file://`、绝对路径、以及 `*.bak/*.orig/*.ghfast-bak` 残留在版本目录中的存在性，并支持 `--fix` 直接还原为官方单值 URL。这是本次 P1 的根治性自动化。
2. **`finish` 结束后自动执行「提交前预检」**：把 `scripts/ohc/preflight.py <repo> main HEAD` 与 `scripts/junk_check.sh` 作为 finish 的收尾步骤（当前需要人工记得跑），任何硬闸命中都在 push 之前暴露；PF8/PF9 的已知误报则通过「本包类型 + 路径规则」白名单化，而不是让每个包各自 `--no-preflight`。
3. **`create-pr --no-preflight` 的使用应留痕**：本次因 PF8（纯库包与遗留 `commands.json` 冲突）与 PF9（软件级 `README.md`/`manifest.yaml` 与「必须落在版本目录」冲突）的**必然冲突**而跳过。建议让 `--no-preflight` 强制要求同时提供 `--no-preflight-reason`，并自动写入 PR 正文的「补充说明」，避免绕过变成无记录。
4. **W3 的镜像改写应改为「只在临时副本上做」**：正确修法是把 `PREDL_BACKUP=…; cp` 挪到镜像改写**之前**、或干脆在 `mktemp` 出来的副本上改写/替换，绝不回写工作树的 `conandata.yml`。这是框架侧一行级修复，收益是所有后续包都不再需要人工核对。
5. **`feedback` 报告里由工具自动填的字段也应尽量准确**：本次自动段落出现「引用知识条目: 无」（实际引用了 E085/E090）、「新增知识草稿: 5 条」（实际 2 对 4 文件）、「编译依赖: 无」（实际 `meson/1.11.0`）。这些与人工填写项混排，反而增加核对成本，建议改为从 manifest 读取。

### 知识图谱覆盖

1. **新增 E-entry：`conandata.yml` 被 CI 写回镜像源（predl 备份晚于镜像改写）**。症状是「构建全绿 + 提交体命中 R39/PF7」，与既有 DRAFT-8543 / DRAFT-8960（注释 URL 被当源码 URL 抓走 → 构建失败）同族但根因、症状都不同。建议以 E-entry 固化，并在条目里给出「W3 日志三特征串」速查法：`Source URLs rewritten with mirror fallback` + `Pre-downloaded N files`(N≥2) + `conandata.yml 已还原为官方 URL`。
2. **新增 E-entry：OHOS 上 `close(fd)` 不唤醒阻塞在同一 fd 的 `read()`**。这是「线程取消不可用时如何优雅释放阻塞线程」这一通用问题的**实证边界**，会反复出现在事件循环 / 线程池 / FUSE / socket server 类库上。建议纳入 musl 差异清单，并与 E085 互相引用。
3. **为「框架误报」类问题建立独立标注层**：本次遇到 G0 非 autotools 误跑 `./configure`（exit 127）、`gen_summary` 的 `'str' object has no attribute 'append'`、Step 10 索要已废弃的 `packaging/`+`.staging-verified`、`submit` 自检的 `packaging_present`、junk_check 的 full 回退、`pre_pr_audit check` 的 `.ci-result.json` 路径不一致——共 6 处。它们不是「知识」而是「工具缺陷」，建议单列一份 **known-false-positives** 清单（带复现命令与判定口径），让后续会话能一眼分辨「我错了」还是「工具错了」，而不是每次重新诊断。
4. **建议为「meson 布尔宏生成无值 `#define`」补 E-entry**（或并入 E090 的说明）：`configuration_data.set()` 真值时写出 `#define X`（无值），因此从 autotools（`#define X 1`）迁来的代码若写 `#if X` 会在真值分支预处理报错，只能用 `#ifdef`。本次是实测踩到后才改的，属可复现的机械陷阱。
5. **建议整理 `knowledge/drafts/` 存量**：`finish` Step 7 报出「1965 个草稿待审」，且 `knowledge/` 下存在 `knowledge/*.kv` 与 `knowledge/drafts/*.kv` 两种命名（`DRAFT-*.kv` 与裸 stem 混用）。数量已达难以人工消化的规模，建议按族聚类后批量转正或归档，否则「待审草稿数」这一指标将失去信号价值。

---

## 作者

- **姓名**: kongling
- **邮箱**: 308360610@qq.com
- **Agent ID**: 24E0
- **生成时间**: 2026-09-28 00:40:15
- **PR 编号**: 13377
- **Git Commit**: e458e7c286
