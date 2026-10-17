# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_c96ba5ca.md`
>
> 修订说明（2026-09-16）：路径 B 收敛为 1 条类级草稿 `DRAFT-11301-ohos-compile-fail-suite`（draft-review=create）；E430 类问题经查重并入既有知识（E342 等），不单独提交（详见 PR #10341 与 issue #3048）。

---

## 背景

- **软件名称**: trompeloeil
- **版本**: 49
- **构建日期**: 2026-09-16
- **构建系统**: cmake（header-only 库；build() 内编译并执行上游 Catch2 自测与 68 个 expect-to-fail 用例）
- **上游仓库**: https://github.com/rollbear/trompeloeil （tag `v49`）
- **适配路径**: 路径 A（基础适配）+ 路径 B（知识库扩展，最终交付 1 条类级草稿 `DRAFT-11301-ohos-compile-fail-suite`；E430 类问题经查重并入既有知识，不单独提交）
- **补丁数量**: 0（零源码修改）
- **编译依赖**: catch2/3.8.1（`tool_requires`，构建期自测与消费者测试用）
- **最终状态**: 成功（PR #10341，AI 检视未发现问题，CI #48680 全过）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | sha256 与调研值一致（2523571f…5593） |
| build | 编译构建 | 成功 | CMake；header-only 无库产物；build() 内跑上游全量测试 |
| conan-verify | 配方验证 | G0/G1/G2/G3/G4/L2/L4/L5 全过 | conan create 内：C++14 自测 604 用例/1361 断言、C++20 615/1394；负向 C++14 50/50、C++20 68/68；消费者 4 用例 5 断言 |
| finish | 归档收尾 | 完成 | W2/W3 本地 CI 模拟通过（`.ci-result.json` exit 0）；非阻塞告警（step5b、G0 clean-verify、debug tarball） |
| submit | PR提交+AI检视+CI | 成功 | PR #10341；AI Review 摘要已生成 + 检视"✅ 未发现问题"（0 意见）；CI #48680 全过 |

### 失败与问题

1. **CMake 配置期从 GitHub 下载 `catch.hpp`（构建期联网）**: 根因是上游 `test/CMakeLists.txt` 在 `find_package(Catch2)` 失败后走 `file(DOWNLOAD)` 兜底（且下载的是 v2 单头）。解决方案：`build_requirements()` 加 `tool_requires("catch2/3.8.1")`，`build()` 将 `self.dependencies.build["catch2"].package_folder` 传给 `-DCMAKE_PREFIX_PATH`；实测无下载文件、编译定义含 `-DCATCH2_MAIN -DCATCH2_VERSION=3`。
2. **`check_errors.sh` 无法运行**: 根因是驱动依赖 GNU `parallel`（OHOS toybox 无此命令），且 `mktemp` 默认路径为只读的 `/tmp`（E002）。解决方案：配方内用 `ThreadPoolExecutor(2)` 逐用例执行**未修改**的 `verify_compilation_error.sh`，`TMPDIR` 指向构建目录，按上游语义（`grep FAIL | wc -l`）判定。
3. **CMake 提示 `System is unknown to cmake, create: Platform/HarmonyOS`**: CMake 尚无 OHOS platform 模块（从编译器默认目标识别出 HarmonyOS）；实测良性，`Threads` 仍命中 `pthread`，构建/运行不受影响。
4. **GNU make `jobserver mkfifo ... Operation not permitted` 警告**: HMDFS 上 mkfifo 受限；非致命，`-j2` 并行构建正常完成。
5. **finish/W3 后 `conandata.yml` 被写入 gh-proxy 镜像 URL 且残留 `.ghfast-bak`/`.orig`**: `conan-verify` 的 E017 预防注入镜像后在 W3 链路中未完全还原。解决方案：每次 finish 后 `git checkout -- conandata.yml` 并清理残留（本任务执行 2 次）。已确认提交版本仅含官方单 URL（PF7 通过）。
6. **首次 `submit` 被 PF9 拦截（假阳性）**: PF9 要求 `archives/` 变更路径至少 5 段，但归档规范要求软件级 `archives/t/trompeloeil/README.md`、`manifest.yaml`（4 段）。按既定逃生口 `OHC_PREFLIGHT=0` 重跑后 PR 创建成功。

### 知识图谱使用情况

- **引用知识条目**: E002（/tmp 只读）、E063（-Werror 评估）、R32/R33/R39/R51 铁律；E524/DRAFT-cmake-test-framework-fetch-to-conan-find-package 作为测试框架接线的查重对象
- **新增知识草稿**: 1 条（DRAFT-11301-ohos-compile-fail-suite：compile-fail 测试套件在 OHOS 的执行模型/TMPDIR/诊断锚定治理，draft-review=create）；另发现的 CMake `file(DOWNLOAD)` 测试依赖兜底问题经查重由 E342 与 DRAFT-cmake-test-framework-fetch-to-conan-find-package 覆盖，未单独提交（见 notes.md 与 PR #10341）
- **引擎命中情况**: 草稿目录 772 条（含他任务草稿）
- **测试统计**: 上游执行 C++14 604（+负向 50）+ C++20 615（+负向 68），消费者 4；全部通过，0 失败 0 跳过（18 个负向用例为上游 `// exception:` 规则排除）
- **未覆盖的错误模式**: ① `monitor-review` 的 `NameError: unreplied_opinions` 使 submit Phase 1 恒失败并白等 30 分钟（本任务复现；改用 `get-comments` 手动确认摘要与"未发现问题"）；② finish 的 G0 clean-verify 对 CMake 项目固定 `exit 127`（找 configure 脚本），属工具实现缺口；③ finish/W3 的 conandata 镜像注入残留无自动还原。

### AI 检视结果

- **检视阶段到达**: 完成（变更摘要已生成；submit 内置 Phase 1 轮询因 monitor-review 缺陷超时，实际检视在 PR 创建后 1 分钟内已完成）
- **变更摘要评估**: 摘要准确——覆盖路径 A+B、零补丁、Catch2 预置、负向套件驱动替换、消费者测试与两条知识草稿，无失实或必须修改点
- **检视意见数量**: 0（atomgit-bot "✅ 未发现问题"）
- **检视意见处理**: 无需处理；该 Info 讨论串平台标记为不可 resolve（"This type of note can not be resolved"），非阻塞

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（exit_code=0；L0/L1/L1e/L4 与 KC1–KC5/JC1–JC6 全过，L5 无产物 warn；integrity_hash a91ceb84…）
- **远程 CI (PR 校验)**: 通过（build #48680：worker_preparation/worker-prep/git-clone/checkout-pr/conan-setup/conan-build-test/cleanup 全部 ✅）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 2（pr_creation_failed：PF9 假阳性；ai_review_summary_timeout：monitor-review 缺陷白等 30 分钟）
- **重试次数**: submit 2 次（PF9 逃生口 1 次、`--resume` 未用因状态文件缺失改为手动推进）；conan create 共 3 次（conan-verify、CI 门禁、finish W3）
- **关键瓶颈**: ① monitor-review 缺陷导致 30 分钟无效等待；② PF9 假阳性每次多一轮 submit；③ finish/CI/W3 三次全量上游测试（每次约 7–10 分钟）在共享设备上还需等待其他参与者 conan create（本任务累计等待 17 分钟）；④ conandata 镜像残留需人工还原与复查
- **耗时较长的步骤**: 上游测试全量执行（两个标准 + 68×2 负向编译）；AI Review 摘要监控超时
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 5 个事件（含 2 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-16T12:10:28 | lang_checked | detected=cpp 与任务 cpp 匹配 |
| 2026-09-16T14:30:06 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/trompeloeil-49 --target main --title 'feat(trompeloeil): 49 适配完成' |
| 2026-09-16T14:31:06 | skeleton_created | pr_created |
| 2026-09-16T14:31:06 | pr_created | PR #10341 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/10341 |
| 2026-09-16T15:01:16 | handoff:ai_review_summary_timeout | 变更摘要未在 30 分钟内生成，请稍后手动检查 PR #10341 \| 检查: python3 scripts/gitcode_pr.py --json monitor-review --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 10341 \| 摘要出现后: python3 scripts/ohc-run.py submit trompeloeil 49 --resume |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **PF9 应豁免归档规范要求的软件级文件**：`archives/<l>/<包>/README.md` 与 `manifest.yaml` 是 ARCHIVE-SPEC 必须文件（4 段路径），与"缺版本目录层"是两回事。当前每次软件级新增都会被 PF9 拦截并要求 `OHC_PREFLIGHT=0`，而该逃生口同时跳过 PF1–PF8（含 PF7 URL 闸），建议 PF9 增加白名单（软件级 README/manifest）或将逃生口细化为 `--skip-pf9`。
2. **W3/finish 结束后自动还原 conandata.yml 并清理 `.ghfast-bak`/`.orig`**：镜像注入链路的还原不完整（本次 2 次 finish 均出现），建议在 W3 末尾对 `git diff` 做自动还原校验（发现镜像域名即 git checkout + 删除备份），避免把带镜像 URL 的版本误提交。
3. **修复 `gitcode_pr.py monitor-review` 的 `NameError: unreplied_opinions`**（本任务复现，另见历史反馈）：submit Phase 1 无法读取真实检视状态，建议修复变量名并在轮询连续失败 N 次后降级为 `get-comments` 解析（摘要与"未发现问题"可直接从评论流判读）。
4. **finish 的 G0 clean-verify 对 CMake 项目适配**：当前对无 configure 脚本的项目固定 `configure 失败 (exit 127)` 并输出 RESULT: FAIL 告警（非阻塞但噪声大），建议按 `build_system` 分派（cmake 项目走 cmake 探测或明确 skip）。

### 模板改进

1. **`conanfile-headeronly.py.tmpl` 增加"上游测试依赖"注释块**：内置 `tool_requires(test framework)` + `CMAKE_PREFIX_PATH` 的写法提示，可直接避免"构建期联网下载"这一类问题（该类已由 E342 与既有 FetchContent 草稿覆盖，见 notes.md）。
2. **`templates/test-report.md` 增加"负向编译测试（expect-to-fail）"节**：包含逐用例计数（executed/excluded/fail）与驱动说明，方便审计与复审核对（对应本 PR 的 `DRAFT-11301-ohos-compile-fail-suite`）。
3. **PR body 模板可加"路径 B 知识贡献说明"可选小节骨架**：列出草稿编号、一类问题、触发实例、查重差异、draft-review 结论五项，减少每次手写差异说明的遗漏。

### 自动化补全

1. **审计输入/结果跨机搬运自动化**：W4 子代理审计需要把 `audit-input-*.json` 从设备拉到本机、结果再推回设备。可提供 `ohc-run.py audit fetch/push` 或让 `pre_pr_audit.py` 支持远端路径，减少手工 base64/ssh 环节。
2. **共享设备 conan create 排队/占用提示工具化**：已有 `ps | grep conan` 人工检查，可在 `conan-verify`/`finish` 入口自动检测并给出等待/让行建议（本任务遵守纪律等待 17 分钟）。
3. **AI Review 状态自动降级**：见"设计改进 3"，配合 `get-comments` 自动判读即可将 30 分钟固定超时降为分钟级。

### 知识图谱覆盖

1. **`DRAFT-11301-ohos-compile-fail-suite`（本 PR 已提交草稿）**：compile-fail 测试套件在 OHOS 的执行模型、TMPDIR 固定与诊断锚定治理——建议正式纳入并关联 E002/E063/E325。
2. **E430 类问题（不新增草稿）**：CMake 测试依赖 `file(DOWNLOAD)` 兜底的主版本漂移——既有条目 E342 与 DRAFT-cmake-test-framework-fetch-to-conan-find-package（FetchContent 变体）已覆盖该类；trompeloeil 实测证据作为 notes.md 适配记录保留。
3. **建议新增**：`monitor-review` 缺陷的识别特征与绕过（工具类知识，可能更适合 v12.x backlog）；以及"三次 conan create 全量测试的用时预算基线（~10 分钟/次）"供 `timeout set` 参考。

---

## 作者

- **姓名**: kasumizawa-miyuu
- **邮箱**: 241250031@smail.nju.edu.cn
- **Agent ID**: 9C4A
- **生成时间**: 2026-09-16 14:31:06
- **PR 编号**: 10341
- **Git Commit**: e76cae351
