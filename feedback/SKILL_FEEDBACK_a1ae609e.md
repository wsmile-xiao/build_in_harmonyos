# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_a1ae609e.md`

---

## 背景

- **软件名称**: kylin-ai-document-service
- **版本**: 1.2.0.0
- **构建日期**: 2026-09-26
- **构建系统**: cmake
- **上游仓库**: https://gitee.com/openkylin/kylin-ai-document-service/repository/archive/build%2F1.2.0.0-ok0.6.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 3
- **编译依赖**:
- grpc/1.84.0
- protobuf/33.6
- libkylin-ai-system-private/1.2.0.0
- systemd/261
- nlohmann_json/3.12.0
- zlib/1.3.1
- openssl/3.5.6
- abseil-cpp/20260107.1
- c-ares/1.34.6
- re2/2024-04-01
- libcap/2.69
- liblzma/5.8.1
- libzstd/1.5.7
- libxcrypt/4.5.2
- libucontext/1.5.2
- **最终状态**: 成功（CI build #62228 校验通过；本机 W3 全绿）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: cmake（worker 即 OHOS/aarch64，非交叉） |
| conan-verify | 配方验证 | 通过 | Verdict PASS，G0–G4 全 PASS |
| finish | 归档收尾 | 完成 | W3 全门禁 pass，.ci-result.json exit_code=0 |
| submit | PR提交+AI检视+CI | PR #13026, CI 通过 | AI Review 已完成（P0×0/P1×0/P2×1） |

### 失败与问题

- **1**: 根因=`find_package(KylinAiProto)` 报找不到 `KylinAiProtoConfig.cmake`, 解决方案=该包是 `libkylin-ai-system-private` 的**组件**（`cmake_file_name=KylinAiProto`），CMakeDeps 只生成顶层 `<包名>-config.cmake`
- **2**: 根因=`client.cpp` 编译失败：`no member named 'always_print_primitive_fields'`, 解决方案=protobuf 33.x 将该字段改名为 `always_print_fields_with_no_presence`
- **3**: 根因=链接失败 `R_AARCH64_ADR_PREL_PG_HI21 … z_errmsg; recompile with -fPIC`, 解决方案=制品仓 `zlib/1.3.1` 为**非 PIC** 静态库（系统同名库按 R26 静态），无法被共享库吸收；改用 `-Wl,--exclude-libs,ALL` 吸收（未改依赖版本，避免牵连已发布的 systemd/261 二进制）
- **4**: 根因=上游测试程序 `Error loading shared library libkylin-ai-document-service.so`, 解决方案=共享库无 `DT_SONAME`，消费者按路径记 `DT_NEEDED`（`../lib….so`），加载器无法解析
- **5**: 根因=上游测试程序 `Error 127 … libsystemd.so.0 not found`, 解决方案=构建树 test 可执行文件无 RPATH（OHOS 工具链下 build-tree RPATH 不生效）
- **6**: 根因=`-DENABLE_TEST=ON` 无效，test 程序不构建, 解决方案=上游 `if (DEFINED ENABLE_TEST) unset(ENABLE_TEST CACHE)` 把 Conan 注入的 CACHE 变量中和
- **7**: 根因=pkg-config 发现失败（`No package 'grpc++' found` / `libsystemd`）, 解决方案=制品仓 `grpc.pc` 的 `Requires` 链引用未安装的 `absl_*` 模块；`systemd/261` 包 `lib/pkgconfig/` 为**空目录**
- **8**: 根因=协议代码生成：制品仓 proto 与源码不匹配, 解决方案=制品仓 `kylin-ai-proto` 的 `document.proto` 已过期（缺 `max_doc_chars_count`/`callback_data`/`Status`），而 `client.cpp` 调用 `add_max_doc_chars_count()`
- **9**: 根因=`conan package()` 写系统根失败, 解决方案=上游 4 处 `install(... DESTINATION /usr/…)` 绝对路径
- **10**: 根因=submit 自检 `packaging_present` 恒 FAIL（无解）, 解决方案=`_check_packaging_present` 仅对 `status ∈ {built,published}` 要求 `packaging/*.tar.gz`，而 ARCHIVE-SPEC 已明令删除该目录、R16-R20 禁止手动打包、`PackageBuilder` 全仓无调用者（详见"SKILL 设计改进"）。依仓库 manifest 自身约定（"CI 验证前不预标 built"）改为 `pending_ci`，该值下检查按设计跳过
- **11**: 根因=submit 自检 `test_report_present` FAIL, 解决方案=`reports/` 被 `.gitignore:96` 忽略；按既有 30 处逐包反忽略先例补齐真实 `test-report.md`（内容取自实测日志）
- **12**: 根因=`create-pr` 报 `404 Can not find the branch: <branch> in project: build_in_harmonyos`, 解决方案=PR 源分支位于 fork（`Inception662`）而非目标仓；`--source` 需带命名空间限定（`Inception662:<branch>`），裸分支名会 404

### 知识图谱使用情况

- **引用知识条目**: DRAFT-kylin-ai-document-service-protobuf33-json-print-options-rename, E537, E541
- **新增知识草稿**: 5 条
- **引擎命中情况**: 草稿目录 1846 条
- **测试统计**: 总计 5, 通过 5, 失败 0, 跳过 0（test_package 消费者断言）
- **未覆盖的错误模式**: (1) OHOS 无 `Platform/HarmonyOS.cmake` 导致 `CMAKE_SHARED_LIBRARY_SONAME_C(XX)_FLAG` 默认为空、共享库缺 `DT_SONAME`，需显式注入（E537 已部分覆盖，建议独立成条）；(2) 制品仓包 `cmake_find_mode=none`（grpc/protobuf）无法被 `find_package` 发现，须在 `generate()` 固定 `*_DIR` 与 codegen 可执行文件路径；(3) 制品仓 `systemd` 包 `lib/pkgconfig/` 为空目录导致 `pkg_check_modules` 失败；(4) 上游 `unset(<OPT> CACHE)` 会中和 Conan 注入的 CACHE 变量，使 `-D<OPT>=ON` 静默失效

### AI 检视结果

- **检视阶段到达**: Phase 5（完成）——P0×0 / P1×0 / P2×1 / P3×0
- **变更摘要评估**: 摘要准确复述本 PR 的实质改动（Conan 归档、3 个移植补丁、依赖图、test_package、知识草稿），未出现幻觉或遗漏，可作为审阅索引直接使用
- **检视意见数量**: 1 条（P2；另有 1 条同内容的 Medium Priority 独立评论，指向同一处代码）
- **检视意见处理**: 1 条全部复核后 **reject（不接纳）**。该意见称 `test_document_service.cpp:55` 的 `responseIsGenuineCall()` 因额外要求 `data` 非空而"测试恒失败"。复核结论：前提不成立——上游 `src/client.cpp:214-215` 对两条返回路径均无条件赋值 `data = ProtoMessageToJsonString(response)`，protobuf 空消息序列化为 `"{}"`（非空）；实测日志（`reports/conan-create.log`）显示 `errorCode=14` 下 4 项 `[ok]`、`5/5 checks passed`、`[FAIL]` 计数为 0，两次独立运行一致。保留 `data` 非空校验反而可对上游未来"错误分支清空 data"（如 async 分支的 `data = nullptr`）形成有效护栏。已附逐条证据回复，未修改测试代码

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（JC/L0/L1/L4/L5 pass，L2 skip 无 bin/，Pass rate 100%）
- **远程 CI (PR 校验)**: 通过（build #62228，#13026，SHA 31348934；conan test_package 通过、L0 结构门禁通过、L1 测试执行验证通过；7 步全绿）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 8 次（累积于时间线：token_not_configured ×3、resume_no_state ×2、self_check_failed ×2、pr_creation_failed ×1）；其中 **6 次为环境/框架缺陷所致**（凭据缺失 ×3、resume 状态未落盘 ×2、`packaging_present` 门禁矛盾 ×2、fork 场景 head 404 ×1），仅 2 次属真实适配问题
- **重试次数**: submit 重跑 4 次（token → resume → 自检 → preflight）；PR 创建 3 次（裸分支名 404 ×2 → 命名空间限定成功）
- **关键瓶颈**: 凭据与环境缺陷占主导——先被 Gate 0 硬阻断（无 token），配好后又连续撞上 PF0 bare-git、自检 `packaging_present`、`create-pr` fork head 404 三处框架侧问题，合计消耗约 1 小时；真实编译适配本身仅约 30 分钟
- **耗时较长的步骤**: submit 闭环（凭据配置 + 4 类框架缺陷定位与绕行）> 首次构建失败排查（SONAME/非 PIC zlib/protobuf 改名）> finish/W3
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 13 个事件（含 9 次 HANDOFF、3 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-26T22:51:49 | handoff:token_not_configured | GitCode access_token 未配置，无法自动创建 PR \| 请先配置 token: python3 scripts/gitcode_pr.py setup \| 配置后重新 submit: python3 scripts/ohc-run.py submit kylin-ai-document-service 1.2.0.0 |
| 2026-09-26T22:58:35 | handoff:token_not_configured | GitCode access_token 未配置，无法自动创建 PR \| 请先配置 token: python3 scripts/gitcode_pr.py setup \| 配置后重新 submit: python3 scripts/ohc-run.py submit kylin-ai-document-service 1.2.0.0 |
| 2026-09-26T23:01:26 | handoff:token_not_configured | GitCode access_token 未配置，无法自动创建 PR \| 请先配置 token: python3 scripts/gitcode_pr.py setup \| 配置后重新 submit: python3 scripts/ohc-run.py submit kylin-ai-document-service 1.2.0.0 |
| 2026-09-26T23:20:49 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-26T23:20:49 | handoff:resume_no_state | 状态文件 .submit-state.json 中无 PR 编号 \| 请重新提交: python3 scripts/ohc-run.py submit kylin-ai-document-service 1.2.0.0 |
| 2026-09-26T23:21:55 | handoff:self_check_failed | 自检未通过: ['packaging_present', 'test_report_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit kylin-ai-document-service 1.2.0.0 |
| 2026-09-26T23:38:49 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-26T23:38:49 | handoff:resume_no_state | 状态文件 .submit-state.json 中无 PR 编号 \| 请重新提交: python3 scripts/ohc-run.py submit kylin-ai-document-service 1.2.0.0 |
| 2026-09-26T23:39:01 | handoff:self_check_failed | 自检未通过: ['packaging_present', 'test_report_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit kylin-ai-document-service 1.2.0.0 |
| 2026-09-26T23:55:47 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/kylin-ai-document-service-1.2.0.0 --target main --title 'feat(kylin-ai-document-service): 1.2.0.0 适配完成' |
| 2026-09-27T00:04:37 | skeleton_created | pr_created |
| 2026-09-27T00:04:37 | pr_created | PR #13026 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/13026 |
| 2026-09-27T00:34:42 | handoff:ai_review_summary_timeout | 变更摘要未在 30 分钟内生成，请稍后手动检查 PR #13026 \| 检查: python3 scripts/gitcode_pr.py --json monitor-review --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 13026 \| 摘要出现后: python3 scripts/ohc-run.py submit kylin-ai-document-service 1.2.0.0 --resume |
<!-- EVENTS:END -->
> 备注：以上为 harness 自动累积至骨架生成时刻（00:04:37）的事件。此后本次闭环又发生 3 次前置闸阻断（PF7 源 URL、PF9 软件级文件路径、fork head 404），因框架 HANDOFF 不覆盖 preflight 层，未自动计入上表。

---

## 建议

### SKILL 设计改进

**S1（高优先级）`submit` 自检 `packaging_present` 与规范自相矛盾，阻断所有正常包。**
`submission.py:210 _check_packaging_present()` 仅当 `status ∈ {built, published}` 时要求 `packaging/*.tar.gz`；而 `finish.py` 默认产出 `published`、缺 `test-report.md` 时降级 `built`——即**任何正常 finish 出来的包都必然落在这两个取值上**。同时：ARCHIVE-SPEC 明示 `packaging/` = **废弃**、`packaging/*.tar.gz` = **删除**；R16-R20 **禁止手动打包**；`PackageBuilder` 全仓**无调用者**、`package_cli` 未接入 `ohc-run.py`；全仓 7278 个 `built/published` 包**无一**满足该检查，磁盘 `packaging/*.tar.gz` 为 **0**。
建议：与 `finish.py:82-94` 保持一致——有 `conanfile.py` 的包跳过该检查，仅对 legacy 无配方包生效；或将该检查在 `cmd_submit` 中也降级为 **WARN**（目前同两项在 `cmd_review` 只是 WARN，两条路径结论不一致）；或直接删除（目录已废弃）。

**S2（高优先级）`unreplied_opinions` 未定义导致 AI Review 监控必崩。**
`gitcode_pr.py` 第 1066/1094/1095 行引用 `unreplied_opinions`，但全文件**无赋值语句**（`review_opinions` 才是被初始化的那个）。`monitor-review` 在任何 PR 上都会 `NameError` 退出；`submission.py:_call_monitor_review` 对非 0 退出码返回 `None`，于是监控退化为 `获取检视状态失败，重试…` **无限空转**至 30 分钟超时——**检视意见即便已生成也永远不会被拉取处理，5 阶段闭环在 Phase 1 即卡死**。建议补上派生逻辑（或最小修复 `unreplied_opinions = review_opinions`）。

**S3（中优先级）`ci-status` 只看最后一条 CI 评论，易被中间态遮蔽。**
`cmd_ci_status()` 取 `ci_comments[-1]` 判定。本次 CI 已实际通过（`## CI 校验通过`，#62228，SHA=PR HEAD），但随后一条 `/rebuild` 产生的 `## 构建触发中` 成为末条、且不含 `校验通过/校验失败/构建已启动/排队中` 任一关键词 → 判 `UNKNOWN` → `result_report.py` 的 success 核验失败 → **CI 已绿却被降级 `partial`**。建议：按 SHA 过滤并取该 SHA 最后一条*结论性*评论，或让 pending 评论带显式关键词，或在 UNKNOWN 时回退比对全部评论中同 SHA 的通过记录。

**S4（中优先级）`preflight` 未复用 `find_executable`，`GIT_BIN` 形同虚设。**
`submission.py:34` 用 `_GIT = find_executable("git")`（支持 `{NAME}_BIN` 覆盖），但 `preflight.py:75/320/578` 与 `gitcode_pr.py:242/271` 仍裸写 `subprocess.run(["git", …])`。在 `posix_spawn` 不搜 `PATH` 的平台上（本次环境实测：`shutil.which`/`os.execvp` 正常而 `subprocess` 报 `FileNotFoundError: 'git'`，且**不限 git**，`sh`/`grep` 同样失败），PF0 环境闸会 fail-closed 拦截，且用户按提示设置 `GIT_BIN` **无效**。建议统一改用 `find_executable`。

**S5（中优先级）`create-pr` 未处理 fork 场景的 head 限定。**
`gitcode_pr.py:289` 将 `args.source` 原样作为 `head` 提交。当源分支位于 fork（官方仓 + 个人 fork 的常规协作模型）时，官方仓 API 报 `404 Can not find the branch: <branch> in project: <repo>`，而 `--source` 传入 `<owner>:<branch>` 即可成功。建议：404 时自动按 `<head_repo_owner>:<branch>` 重试，或在错误信息中直接给出限定写法。

**S6（低优先级）HANDOFF 不覆盖 preflight 层阻断。**
本次 PF7/PF9 硬闸拦下 PR 创建时，仅输出 `pr_creation_failed` 并建议"手动 create-pr"，未记录到 feedback 事件时间线，也未提示 `--no-preflight` 逃生口在 `submit` 路径上不可达（`submission.py` 调用 `create-pr` 时未透传该开关与其环境变量等价物）。建议统一事件累积，并在 submit 路径暴露等价逃生口。

### 模板改进

**T1** `feedback` 骨架的「最终状态」「build 结果」等字段取自**骨架生成时刻**的状态，此时 submit 尚未完成，故本次落成"最终状态: 失败 / 编译构建: 失败"——与事实相反（编译成功、CI 通过）。建议改为在 `result` 终态时**回填**这些字段，或明确标注为"骨架时点快照"。
**T2** `test-report.md` 无模板，本次须参照既有包（如 openssl）手工成形。建议提供模板（环境/摘要表/消费者断言逐项/上游测试清点/产物校验/已知限制），并明确"上游测试无断言时如何如实申报（R51）"。
**T3** PR body 模板的"测试用例对比"节在**纯库包 + 上游无测试框架**时无内容可填，易残留占位符（而 `submit` 的占位符完整性检查会硬失败）。建议为该形态提供"无可对比上游用例"的标准表述。
**T4** `manifest.yaml` 的 `status` 取值注释（"CI 验证前不预标 built"）出现在**部分**包的模板中，本次 nosso 文件的取值行恰无注释，导致 agent 难以判断该填 `built` 还是 `pending_ci`。建议在 ARCHIVE-SPEC 与模板中统一固化取值时机。

### 自动化补全

**A1** `conandata.yml` 的镜像/官方源判定：PF7 对 gitcode/gitee 源一律拦截并要求人工申请例外。建议内置**官方托管白名单**（`gitee.com/openkylin` 等官方组织）自动放行，或提供一个可审计的例外声明字段，避免每个该组织下的包都重复人工申请。
**A2** PF9 对**软件级文件**（`archives/<字母>/<包>/{manifest.yaml,README.md}`）恒报"缺版本目录层"。这是 ARCHIVE-SPEC 明确要求的文件形态（仓内软件级 `manifest.yaml` 4226 个、`README.md` 5051 个，且 2026-09-26 合并的 libprotoc/checkit-tiff/tarsnap/instaloader 等积分赛 PR 均携带）。建议把"软件级元数据 + 单版本目录"识别为合法组合，减少无谓告警。
**A3** 依赖解析阶段可预检依赖间的**版本互斥**（本次 `protobuf` 必须 33.6 而非 33.6.1，否则与 `grpc/1.84.0` 冲突），在 `generate()` 之前给出提示，而非留到链接期才发现。
**A4** 非 PIC 静态库检测可自动化：本次 `zlib/1.3.1` 的非 PIC 静态对象导致共享库链接失败，可扫描依赖 `lib/*.a` 的 PIC 属性并提前告警，并自动建议 `-Wl,--exclude-libs,ALL`。
**A5** `cmake_find_mode=none` 的制品仓包（grpc/protobuf）在 `generate()` 中需手工固定 `*_DIR`、`*_EXECUTABLE`、`*_PLUGIN` 等一串路径。建议由 `conan-init` 依据依赖包类型自动生成该段，降低遗漏风险。

### 知识图谱覆盖

建议新增/细化以下 E-entry：
- **E-NEW-1（SONAME）**：OHOS 无 `Platform/HarmonyOS.cmake` → `CMAKE_SHARED_LIBRARY_SONAME_C(XX)_FLAG` 默认为空 → 共享库缺 `DT_SONAME` → 消费者按路径记 `DT_NEEDED` 且加载失败。修法：注入 `-Wl,-soname,`。（与 E537 相关但症状/修法独立）
- **E-NEW-2（cmake_find_mode=none）**：制品仓包不生成 `find_package` 可发现文件，须固定 `*_DIR` 与 codegen 二进制路径。
- **E-NEW-3（组件 vs 包）**：`cmake_file_name` 组件（如 `KylinAiProto` 属 `libkylin-ai-system-private`）不会被 CMakeDeps 单独生成 config，`find_package(组件名)` 必然失败。
- **E-NEW-4（上游 unset CACHE）**：上游 `unset(<OPT> CACHE)` 会中和 Conan 注入的同名 CACHE 变量，令 `-D<OPT>=ON` **静默失效**（表现为"选项设了却无效"）。修法：补丁移除该 `unset` 或改用非 CACHE 传递。
- **E-NEW-5（空 pkgconfig 目录）**：制品仓包携带 `lib/pkgconfig/` 空目录时，`pkg_check_modules` 失败；应改走 `find_package(... CONFIG)`。
- **E-NEW-6（非 PIC 静态依赖）**：与共享库链接时非 PIC 静态对象报 `R_AARCH64_ADR_PREL_PG_HI21`；修法 `-Wl,--exclude-libs,ALL`（优于改依赖版本，避免牵连已发布二进制）。
- **E-NEW-7（proto 制品过期）**：制品仓 proto 与上游源码不匹配（缺字段），应改用源码树 `.proto` 生成。

---

## 作者

- **姓名**: Inception662
- **邮箱**: 3389004972@qq.com
- **Agent ID**: E6D8
- **生成时间**: 2026-09-27 00:04:37
- **PR 编号**: 13026
- **Git Commit**: 31348934d3
