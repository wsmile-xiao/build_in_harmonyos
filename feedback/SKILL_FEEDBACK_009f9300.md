# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_009f9300.md`

---

## 背景

- **软件名称**: wise
- **版本**: 2.4.1
- **构建日期**: 2026-09-23
- **构建系统**: makefile
- **上游仓库**: https://deb.debian.org/debian/pool/main/w/wise/wise_2.4.1.orig.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 11
- **编译依赖**:
- glib/2.88.3.1
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: makefile |
| conan-verify | 配方验证 | 通过 | G0/G1 PASS；G2 首次失败源于 refresh-patch 重排补丁文件名后 conandata.yml 未同步，对齐后通过 |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | 完成 | 远程 CI 两轮通过（#57923 / #57926，L0、L1、test_package 均通过）；人工评审 rule12 提出 1 条意见，已修复并回复 |

### 失败与问题

- **1**: 根因=`sh: glib-config: not found`，链接缺 `-lglib-2.0`, 解决方案=上游用 glib 1.2 时代的 `glib-config` 工具，现代系统已无
- **2**: 根因=`make bin` 失败（`csh: not found`）, 解决方案=顶级 makefile 的 bin 目标执行 `csh welcome.csh`（仅打印欢迎信息）
- **3**: 根因=`error: static declaration of 'getline' follows non-static declaration`（HMMer2/sqio.c，20+ 处）, 解决方案=HMMer2 自带静态 `getline(struct ReadSeqVars *)`，与 POSIX `getline()` 同名
- **4**: 根因=`ld.lld: error: undefined symbol: isnumber`（genewise/estwise/genewisedb/estwisedb）, 解决方案=`isnumber()` 是 BSD 专有接口，musl 未提供
- **5**: 根因=`error: incompatible pointer to integer conversion … (aka 'int') -Wint-conversion`（compressed_protein_index）, 解决方案=上游遗留 `return NULL;` 出现在 `boolean` 返回类型函数中
- **6**: 根因=链接 `multiple definition of …`, 解决方案=clang 15 默认 `-fno-common`，而上游依赖 tentative definition 合并
- **7**: 根因=**上游测试仅 4/12 通过**：promoterwise `Length = 798`（应为 797）、basic-cdna 坐标整体 +1 并 SIGSEGV, 解决方案=OHOS/AArch64 上 `char` 默认**无符号**，`dynlibsrc/sequence.c` 的 `char c = fgetc(ifp); if (c == EOF …)` 恒假 → EOF 被当作一个碱基写入序列（长度 +1、坐标偏移），并破坏后续解析
- **8**: 根因=解包后 `make` 调用不存在的 `dyc` 重生成 `.c`, 解决方案=以不保留时间戳的方式复制源码（`cp -r`），`.dy` 被判为比 `.c` 新
- **9**: 根因=`init-build` 后源码树被破坏（顶层只剩 HMMer2 文件）, 解决方案=`init_build.py` 的 `_promote_nested_source`（F068）`_BUILD_MARKERS` 只含大写 `Makefile`；wise2 唯一的大写 `Makefile` 在 `src/HMMer2/`，被误提升到顶层
- **10**: 根因=`clang -c` 以非 0 码退出但**无任何诊断输出**（W3 本地 CI 下必现，同目录手工执行同一命令成功）, 解决方案=OHOS worker 上编译器/链接器输出经管道会被静默丢弃；配方改为 `_run_logged()` 把每步输出重定向到日志文件，失败时回显日志末尾

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 1（knowledge/drafts/wise-2.4.1-aarch64-unsigned-char-eof-fgetc.{kv,md}）
- **引擎命中情况**: 草稿目录 1544 条
- **测试统计**: 总计 0, 通过 12, 失败 0, 跳过 0
- **未覆盖的错误模式**: OHOS worker 上「编译器/链接器输出经管道被静默丢弃、命令判为失败」这一现象此前无对应 E-entry（W3 下 `clang -c` 无任何诊断即返回非 0，同目录手工执行却成功）；已随本次适配沉淀为知识草稿。

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: 变更限于单一包目录 archives/w/wise/2.4.1/ 与软件级 commands.json，外加 1 个知识草稿；共 11 个补丁（全部为可移植性修改，无功能改动）
- **检视意见数量**: 1（评审人 CodexBai，rule12_harmony_specific）— 已处理
- **检视意见处理**: rule12「鸿蒙特有测试仅断言、无完整消费者用例」→ 已把 test_package/test.sh 重构为 7 个具名完整端到端消费者用例（新增 dba / promoterwise 两组），统计口径由「1 项 44 断言」改为「7 个用例」，实测 7/7；同步更新 pr-body.md / test-report.md / notes.md / test_package/MANIFEST.yml；提交 abd922a094 已推送并触发 /rebuild

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（L0_RESULT=pass / L1_RESULT=pass / L2_RESULT=skip（上游 `--version`/`--help` 非 0 退出，非阻塞）/ L4_RESULT=warn（补丁中含危险函数调用，非阻塞）/ L5_RESULT=pass；test_package 7 组断言全绿）
- **远程 CI (PR 校验)**: 通过（#57923、#57926：worker_preparation / git-clone / checkout-pr / conan-setup / conan-build-test / cleanup 全绿，L0 结构完整性通过、L1 测试执行验证通过、Conan test_package 通过）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 3（finish #1 的 G0 clean-verify 与 W3 各 1 次；finish #2 的 G2/W3 合计 1 次）
- **重试次数**: finish ×3、W3 本地 CI ×3、conan create 迭代 ×3
- **关键瓶颈**: 「编译器输出经管道静默失败」的定位——现象为 `clang -c` 无任何输出即返回非 0，而同一目录手工执行同一命令成功，需要交叉比对「W3 的 tee 管道环境 vs 手工重定向环境」才能定位
- **耗时较长的步骤**: 源码下载（deb.debian.org，约 1.5–2 min/次，共约 6 次）与全量 `make realall`（约 2 min/次）；反复重跑 finish/W3 占本次大部分时间

---

## 建议

### SKILL 设计改进

1. **`init-build` 的 F068「嵌套源码提升」会误判 makefile 型项目**：`scripts/ohc/init_build.py` 的 `_BUILD_MARKERS` 只包含大写 `Makefile`，而 wise2 顶层入口是 **小写 `src/makefile`**，唯一的大写 `Makefile` 在 `src/HMMer2/`——结果 `_promote_nested_source()` 把 `src/HMMer2/` 提升为源码根，整棵目录树被破坏（顶层只剩 HMMer2 文件）。建议：① `_BUILD_MARKERS` 同时识别小写 `makefile`；② 提升前校验候选目录的层级深度与包名是否匹配（`src/HMMer2` 明显不是源码根）；③ 提升动作先做 dry-run 并记录可回滚点。
2. **`refresh-patch` 会在 finish 管线中静默重命名补丁**：手工按「一项逻辑改动 = 一个补丁」命名（如 `0001-build-use-conan-glib-flags.patch`）后，finish 的 Step 1 会按文件重新生成为 `0001-src-xxx.patch`，而 `conandata.yml` / `manifest.yaml` 的 `patches_applied` 不会同步，直接导致 G2/W3 报「patch 文件路径错误」。建议：refresh-patch 生成后自动回写 `conandata.yml` 的 `patch_file` 列表与 `manifest.yaml` 的 `patches_applied`，或在已有补丁与生成结果内容等价时跳过重命名。
3. **`refresh-patch` 的 `.patch-backup-<ts>/` 会被 `exports_sources = "patches/*"` 一并导出**（本次 conan 日志出现「Copied 22 '.patch' files」，实际只有 11 个）。建议 backup 目录放到包目录之外或加白名单过滤。
4. **W3 与手工 `conan create` 的行为差异需要显式提示**：W3 的输出经 `tee` 走管道，会让 OHOS worker 上的编译器静默失败，而手工执行不会——这类「同一配方、两种结果」的情况建议在 W3 失败提示中直接给出「请检查输出管道/改用日志绑定」的候选原因。
5. **`-j1` 之外建议默认给出 make 型配方的输出重定向范式**：`self.run("make ... > build.log 2>&1")` 在 OHOS 上是必需项而非优化项，建议写入 makefile 模板并加静态检查（L0 层扫描 `self.run` 中未重定向的构建命令）。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. `templates/conanfile-makefile.py.tmpl` 建议补充：① 递归 makefile 项目的 `cwd=self.source_folder/<子目录>` 说明；② **命令输出必须重定向到日志文件**（OHOS worker 必需）；③ `-fsigned-char`、`-fcommon`、`-Wno-error=int-conversion` 等「遗留 C 代码在 clang/aarch64 上的常见必需标志」清单，可显著缩短后续同类包的排查时间。
2. PR body 模板的「上游库测试用例统计」与「适配后测试用例统计」两张表列名不一致（前者最后一行是「其他测试」，后者是「鸿蒙特有测试」），首次填写容易误改；建议加注「保持模板原样，只填数值」。
3. `templates/skill-feedback.md` 的占位符较多（本次 14 处），其中「AI 检视结果」「CI 结果」在 PR 创建即结束的场景下无法填写；建议按 `AUTO_FILL` / `MANUAL` 分组标注，或在 PR 未等待检视时允许填「按任务要求未等待」。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. `finish` 的 Step 1（refresh-patch）与 `conandata.yml` 的同步可完全自动化（见「SKILL 设计改进」第 2 条）。
2. `packaging/` 归档目前需手工从 conan cache 打包；建议 `finish` 在 close-archive 阶段自动生成 `<pkg>-<ver>-ohos-aarch64.tar.gz`（submit 的 `packaging_present` 自检已要求该文件存在）。
3. `reports/` 目录被 `.gitignore` 忽略，需要 `git add -f` 才能入仓；建议 `finish`/`submit` 内部对 `reports/*.md`、`audit-result.json` 统一 `-f` 添加，避免遗忘。
4. 本机 `archives/l/libXext` 与 `archives/l/libxext` 共享 inode，工作树恒显示 2 个「已修改」文件，容易干扰 `git status` 判读；建议在提交/审计前自动识别并忽略该噪声。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. **新增知识草稿 1 条**：`knowledge/drafts/wise-2.4.1-aarch64-unsigned-char-eof-fgetc.{kv,md}` —— AArch64 上 `char` 默认无符号使 `char c = fgetc(); c == EOF` 恒假（长度 +1 / 坐标偏移 / 段错误），`-fsigned-char` 修复。建议 promote 为正式 E-entry（严重度 2，类别 platform|portability|aarch64|char-signedness|legacy-c）。
2. **建议新增 E-entry（本次命中但无覆盖）**：OHOS worker 上「编译器/链接器输出经管道被静默丢弃并把命令判为失败」，处置范式为构建命令内部 `> log 2>&1` 绑定日志 + 失败时回显日志末尾。该现象已在多个包上重复出现，具备强复用价值。
3. **建议补充既有条目**：`init-build` F068 嵌套提升对「小写 makefile + 子目录大写 Makefile」项目的误判，可作为工程缺陷类条目收录（附回滚/校验建议）。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: Kongling32
- **邮箱**: 308360610@qq.com
- **Agent ID**: 9219
- **生成时间**: 2026-09-23 22:59:27
- **PR 编号**: —
- **Git Commit**: a746679f24

### 评审意见处理记录（2026-09-24）

人工评审（CodexBai）按 `pc-pr-review` 13 条规则判定：rule1~rule11、rule13 全部 PASS，
仅 **rule12_harmony_specific FAIL**——「鸿蒙特有测试行只有断言（N=1），不算完整消费者
用例；至少要有一个完整消费者用例（真正跑通功能/流程的端到端用例），纯断言不行」。

**根因**：本包 test_package 原本实现为「11 程序存在性 + 11 个 `-version` + WISECONFIGDIR
数据完整性 + 4 组比对输出断言」的**断言集合**，在 PR 统计表里按 1 项填报，描述中关键词
是「断言」，被规则判为纯断言。

**修复**：把 test.sh 改写为 7 个具名用例（HC-1…HC-7），每个都是完整端到端消费者流程
（构造输入 → 真实执行包内程序 → 读取包导出的 WISECONFIGDIR → 产出真实结果 → 校验内容），
并新增 HC-6 dba、HC-7 promoterwise 两个此前未覆盖的程序；统计口径由「断言数」改为
「完整端到端消费者用例数」（鸿蒙特有测试 7、合计 19、通过率 [7/7]）。

**经验（可复用）**：
1. 「鸿蒙特有测试」要按**用例数**填报，且用例必须是端到端流程，不能写成断言清单；
   PR 描述里尽量少出现「断言」作为唯一描述词。
2. 应用型（CLI）包应把**每个可执行程序**至少覆盖一个端到端用例，程序清单即用例清单的
   天然来源——这次评审暴露的正是 11 个程序里只覆盖了 4 个。
3. `handle-review-opinion --action accept` 对本类审查结论 note 会因
   「This type of note can not be resolved」无法标记已解决（回复仍成功），
   需改用 `reply-comment` 在讨论串内回复。
