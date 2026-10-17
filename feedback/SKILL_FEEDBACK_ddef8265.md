# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_ddef8265.md`

---

## 背景

- **软件名称**: uchardet
- **版本**: 0.0.7
- **构建日期**: 2026-09-18（Conan 适配；历史首次编译 2026-05-25）
- **构建系统**: cmake
- **上游仓库**: https://gitlab.freedesktop.org/uchardet/uchardet
- **适配路径**: 路径 A（基础适配，无补丁，源码零修改）
- **补丁数量**: 0
- **编译依赖**:
无（纯 C++ 算法库）
- **最终状态**: 成功（PR #10866，AI 检视零意见，CI 全绿）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 历史归档 URL 复用（gitlab.freedesktop.org 官方 tag 归档） |
| lang-preflight | 语言预检 (R47) | 通过 | detected=cpp，与任务语言一致 |
| build | 编译构建 | 成功 | cmake + clang15，116/116 上游测试通过 |
| conan-verify | 配方验证 | 通过 | G0-G4 + L2/L4/L5 八道门禁全 PASS（三次迭代：cache_variables 修正、reset 断言修正、SONAME 修正后复验） |
| finish | 归档收尾 | 完成 | W3 本地 CI 模拟通过（首轮因未提交文件回退全仓扫描误报 cloog 历史遗留，提交后增量模式通过） |
| submit | PR提交+AI检视+CI | 成功 | PR #10866；AI 检视"未发现问题"；CI L0/L1/test_package 全过 |

### 失败与问题

- **1**: 根因=CMake 版本兼容性（cmake_minimum_required 2.8.5 被 CMake 4.x 拒绝），解决方案=CMAKE_POLICY_VERSION_MINIMUM=3.5，但 conan-init 模板用 tc.variables（写入 toolchain set() 时机太晚不生效），必须改用 tc.cache_variables 走命令行 -D；首次 G2 失败定位此差异
- **2**: 根因=OHOS 本机构建 CMake 自检未知平台 HarmonyOS（无共享库 SONAME/版本化规则），shared 变体 libuchardet.so 无 SONAME、CLI 记录相对 NEEDED ../libuchardet.so 包外不可解析，解决方案=tc.cache_variables["CMAKE_SYSTEM_NAME"]="Linux"（abcmidi 已合入先例），shared 变体获得 SONAME=libuchardet.so.0 并全流程通过
- **3**: 根因=test.c 首版 reset 断言逻辑错误（reset 后未喂数据却断言非空结果），解决方案=reset 后重喂数据断言相同检测结果（真实验证句柄可复用语义）
- **4**: 根因=W3 首轮 junk_check 全仓扫描命中 main 上 cloog 历史遗留状态文件（.build-closed/.staging-verified 被跟踪），解决方案=先 git commit 本包变更使 junk_check 走增量模式（git diff origin/main...HEAD），历史遗留文件不在 diff 中即不阻断；同时建议主编清理 cloog 的两个被跟踪状态文件
- **5**: 根因=本机 musl posix_spawn 不做 PATH 搜索，python3.12 subprocess 列表模式（["git",...]）全部 FileNotFoundError，submit 的 PF0 环境闸与 monitor-review 轮询均受影响，解决方案=PYTHONPATH 注入 sitecustomize.py 禁用 subprocess._USE_POSIX_SPAWN 回退 fork+execvp（本地环境修复，未动框架文件）
- **6**: 根因=scripts/gitcode_pr.py cmd_monitor_review 引用未定义变量 unreplied_opinions（NameError），submit 内置 AI Review 轮询（_call_monitor_review 子进程）持续失败，解决方案=改用可用的 get-comments/get-review-comments/trigger-ci/ci-status 命令手动驱动同一套 Phase 1-5 流程（变更摘要→检视意见→CI 触发→CI 绿），行为与工具轮询完全等价

### 知识图谱使用情况

- **引用知识条目**: 无直接命中（E540/E529/E092 均为弱关联提示，实际根因不同）
- **新增知识草稿**: 无（问题均可归因到已有规则或先例：R7/E002/E046 平台特性、abcmidi CMAKE_SYSTEM_NAME 先例）
- **引擎命中情况**: conan-verify 失败时引擎给出 E540/E529 提示但与实际根因（cache_variables 时机、musl posix_spawn）不符，仅作参考
- **测试统计**: 上游 ctest 116 项（100% 通过）+ test_package 8 断言（100% 通过）；5 项上游已知损坏由上游 CMakeLists 跳过未注册
- **未覆盖的错误模式**: ① tc.variables vs tc.cache_variables 对 cmake_minimum_required/CMAKE_SYSTEM_NAME 的时机差异；② musl posix_spawn 无 PATH 搜索导致 subprocess 列表模式全挂；③ gitcode_pr.py monitor-review unreplied_opinions NameError。三者本次均以笔记+本报告沉淀，建议入库

### AI 检视结果

- **检视阶段到达**: Phase 5 完成（摘要→检视→CI 全流程）
- **变更摘要评估**: 摘要准确描述适配内容（conanfile 结构、cache 变量注入、commands.json、审计归档），无需修改
- **检视意见数量**: 0（"#### 代码审查 ✅ 未发现问题"）
- **检视意见处理**: 无需处理；Pre-PR W4 独立审计 verdict=pass（P0=0/P1=0，P2=1 status 口径已按建议降级 built，P3×5 已修复 4 项）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（build_and_test.sh JC/KC/L0/L1/conan create 全过）
- **远程 CI (PR 校验)**: 通过（PR #10866，build #50537，worker OpenHarmonyPCDeveloper-CI-020；conan-setup/conan-build-test/cleanup 全 ✅，L0 结构/L1 测试执行/test_package 全过）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 6（G2 cmake policy 1 次、W3 junk 1 次、W4 未审计 1 次、manifest 自检 1 次、PF0 posix_spawn 1 次、PF9 软件级路径 1 次）
- **重试次数**: conan-verify 3 轮（每轮修复后复验）、submit 4 轮（含 2 次环境修复）
- **关键瓶颈**: ① conan-init 模板 CMAKE_POLICY_VERSION_MINIMUM 用 tc.variables 默认值必失败（首个 G2 失败的确定性根因）；② 本机 musl posix_spawn 环境缺陷使框架内所有列表模式 subprocess 调用挂掉（PF0/monitor-review 连环受影响）；③ gitcode_pr.py monitor-review NameError bug 使 submit 内置轮询不可用，被迫手动驱动闭环
- **耗时较长的步骤**: AI 检视等待约 70 分钟（18:38 触发→19:50 CI 绿，其中检视意见 19:0x 才出现）；环境问题诊断约 40 分钟（posix_spawn 隔离测试）

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 12 个事件（含 4 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-18T17:19:51 | skeleton_created | result_partial |
| 2026-09-18T17:19:51 | lang_checked | detected=cpp 与任务 cpp 匹配 |
| 2026-09-18T18:07:34 | handoff:w4_audit_not_done | W4 Pre-PR 审计未执行，请先完成审计 \| python3 scripts/pre_pr_audit.py generate --repo-dir /storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent --package uchardet --version 0.0.7 \| 审计子任务完成后将结果保存为 reports/audit-result.json |
| 2026-09-18T18:30:29 | handoff:self_check_failed | 自检未通过: ['manifest_complete'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit uchardet 0.0.7 |
| 2026-09-18T18:32:07 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/uchardet-0.0.7 --target main --title 'feat(uchardet): 0.0.7 适配完成' |
| 2026-09-18T18:36:27 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/uchardet-0.0.7 --target main --title 'feat(uchardet): 0.0.7 适配完成' |
| 2026-09-18T18:38:59 | skeleton_exists | pr_created |
| 2026-09-18T18:38:59 | pr_created | PR #10866 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/10866 |
| 2026-09-18T19:09:29 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-18T19:09:29 | skeleton_exists | resume_pr_exists |
| 2026-09-18T19:57:08 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-18T19:57:08 | skeleton_exists | resume_pr_exists |
<!-- EVENTS:END -->

---

## 建议

### SKILL 设计改进

1. **conan-init 模板修正**：cmake 模板的 `tc.variables["CMAKE_POLICY_VERSION_MINIMUM"]` 应改为 `tc.cache_variables[...]`——对 cmake_minimum_required 和平台变量（CMAKE_SYSTEM_NAME/CMAKE_SYSTEM_PROCESSOR），toolchain 内 set() 时机太晚或根本不进 cache，模板默认值首次 G2 必失败；建议模板直接用 cache_variables 并注释适用场景（abcmidi 式平台覆盖也应模板化）
2. **PF9 与 PF8/L0k 对混合 lib+tool 包自相矛盾**：PF8 要求 bindirs 声明的包必须有软件级 commands.json（archives/<字母>/<包>/commands.json，4 段路径），PF9 又把一切 <5 段 archives 路径判为"缺版本目录层"拦截——混合类型包（a52dec/dict/libndp 先例均带软件级文件合入）无法同时满足两闸；建议 PF9 对已知软件级文件名（commands.json/README.md/manifest.yaml）加白名单豁免，判定"No packages to build"应看 diff 中是否存在版本目录层 conanfile.py 而非要求全部路径 ≥5 段
3. **junk_check 全仓回退模式对 main 历史遗留的误伤**：本地未提交时 git diff origin/main...HEAD 为空 → 回退 full 模式 → 命中 main 上他人误提交的状态文件（cloog .build-closed/.staging-verified）阻断 W3；建议 full 模式下仅与 base 比较新增的违规文件才报错，或提示"先 commit 走增量模式"而非直接 FAIL
4. **W3 应在 finish 文档中明确"先 commit 再跑"**：本次 W3 失败的解法（先 git commit 使 junk_check 走增量模式）在 HANDOFF 的 AI NEXT ACTIONS 里没有提示，靠读 junk_check.sh 源码定位
5. **submit 的 _REQUIRED_MANIFEST_FIELDS 顶层字段要求与 conan-init 生成的嵌套 manifest 结构不一致**：模板生成 build.build_system（嵌套），submit 自检要求顶层 build_system——建议 conan-init 直接生成顶层字段（dict/libndp 先例形态），避免提交期才发现

### 模板改进

1. conanfile cmake 模板的 `tc.variables["CMAKE_INSTALL_PREFIX"] = "$DEFAULT_PREFIX"` 字面量占位符是必删项（conan create 自带 prefix，字面量 $DEFAULT_PREFIX 会破坏安装）——建议模板删除该行或改为注释说明
2. conanfile cmake 模板的 `tc.variables["CMAKE_BUILD_TYPE"] = "Release"` 硬编码与 CMakeToolchain 从 settings.build_type 的自动生成冲突（破坏 Debug 构建）——建议删除
3. test_package 模板的 test.c printf 空壳（R34 违规源）：模板应提供一个调用被测包 API 的最小示例骨架（哪怕 TODO 标注关键 API），否则每次都要整个重写
4. 混合 lib+tool 类型：建议模板/文档补一段 package_info 同时声明 cpp_info.libs 与 cpp_info.bindirs + 软件级 commands.json 的标准形态（本次靠 a52dec 先例反推）

### 自动化补全

1. **gitcode_pr.py monitor-review NameError 修复**（P0 级框架 bug）：cmd_monitor_review 第 1066 行引用未定义的 unreplied_opinions，导致 submit 内置 AI Review 轮询在本环境持续失败、30 分钟超时；建议补 `unreplied_opinions = [...]` 计算逻辑（可从 review_opinions 与已回复讨论差集推导）
2. **posix_spawn 环境探测自动化**：musl posix_spawn 无 PATH 搜索使框架内 subprocess.run(["git",...]) 列表模式全挂（PF0 假故障）；建议 ohc-run.py 入口自检 subprocess 列表模式可用性，不可用时自动注入 sitecustomize 或改用 shutil.which 解析绝对路径（框架内 subprocess 调用统一走 which 包装）
3. **AI Review/CI 并行触发**：当前 submit 串行等待检视完成才进 CI 监控，本次检视等待 70 分钟；检视与 CI 无数据依赖，PR 创建后即可同时触发 CI（/rebuild）与检视监控，缩短闭环时延
4. **staging 验证（driver Step8）在模式 B 流程中缺失**：手动编译+finish 路线不会生成 .staging-verified，submit 前才以"需创建 .staging-verified"警告暴露；建议 finish 流程内置对 conan 包产物的 staging 验证（bin/* --version 实测）并自动写标记

### 知识图谱覆盖

1. **新增 E 条目建议：tc.variables vs tc.cache_variables 时机差异**——错误签名 `cmake_minimum_required.*Compatibility with CMake < 3.5 has been removed` 且已传 tc.variables 仍失败；根因是 toolchain set() 对早期 cmake 命令与 cache 语义变量太晚；方案是 cache_variables（命令行 -D）。本次实测踩坑两次（POLICY_VERSION_MINIMUM、SYSTEM_NAME）
2. **新增 E 条目建议：OHOS CMake 未知平台无 SONAME**——错误特征 `readelf -d *.so` 无 SONAME + NEEDED 相对路径（../libxxx.so）；根因 CMAKE_SYSTEM_NAME=HarmonyOS 无平台模块；方案 cache_variables CMAKE_SYSTEM_NAME=Linux（abcmidi 先例）；本次验证 shared 变体修正前后差异
3. **新增 E 条目建议：musl posix_spawn 无 PATH 搜索**——错误签名 `FileNotFoundError: [Errno 2] No such file or directory: 'git'`（subprocess 列表模式）而 which/execvp 正常；根因 musl posix_spawn 不做 PATH 搜索；方案 sitecustomize 禁用 _USE_POSIX_SPAWN 或框架内 which 解析
4. **新增 E 条目建议：C++ 库的 C 消费者链接**——错误特征 C 测试程序链接 C++ 库 undefined reference to operator new/__cxa；方案 set_target_properties LINKER_LANGUAGE CXX（test.c 保持 C 编译）
5. 平台特性条目可补充：新写二进制偶发 exec EPERM（OHOS 首次执行确认机制，同权限旧文件可执行）——避免后续任务误判为包缺陷

---

## 作者

- **姓名**: ohpcd-robot
- **邮箱**: ohpcd-robot@noreply.gitcode.com
- **Agent ID**: 42BA
- **生成时间**: 2026-09-18 17:19:51（终稿填充 2026-09-18 20:05）
- **PR 编号**: 10866（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/10866）
- **Git Commit**: 3c011ec1abb3a0937e787f39f1472b8e94684cfd（分支 feat/uchardet-0.0.7）
