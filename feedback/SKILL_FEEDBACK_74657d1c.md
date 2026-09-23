# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_74657d1c.md`

---

## 背景

- **软件名称**: libkeduvocdocument
- **版本**: 26.04.0
- **构建日期**: 2026-09-21
- **构建系统**: cmake
- **上游仓库**: https://invent.kde.org/education/libkeduvocdocument （源码包 `https://download.kde.org/stable/release-service/26.04.0/src/libkeduvocdocument-26.04.0.tar.xz`）
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 2（0001 上游 Config.cmake 打包缺陷修复；0002 E537 可重定位链接）
- **编译依赖**:
- qtbase/6.11.1
- ki18n/6.26.0
- karchive/6.26.0
- kio/6.26.0
- libxml2/2.15.3
- （tool_requires）ecm/6.26.0
- **最终状态**: 成功（本地全部门禁；停在 PR 前等待确认）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | sha256 `032689e3…` 与上游逐字一致；骨架生成但 conanfile/conandata/test_package 因模板不匹配需全部手写 |
| lang-preflight | 语言预检 | 通过 | detected=cpp（源文件 41 个，主体 100%） |
| build | 编译构建 | 成功 | 构建系统: cmake；首次 ctest 因 E537 全挂，修复后 8/8 |
| conan-verify | 配方验证 | 通过 | G0/G1/G2/G3/G4 全 PASS；报告内 L2/L4/L5 标注 PASS 但正文为「跳过（无 cache 路径）」 |
| finish | 归档收尾 | 完成（非全绿） | W3 阻塞门禁通过；G0 clean-verify 工具误报、gen_summary 内部错误 |
| submit | PR提交+AI检视+CI | 未执行 | 按用户要求停在 PR 前；AI Review: — |

### 失败与问题

1. **E537 消费者侧（阻塞首次 ctest）**：已发布的 `kio/6.26.0` 二进制把构建机 Conan 缓存绝对路径写进 DT_NEEDED
   （`/…/.cache/conan2/p/<hash>/p/lib/libKF6*.so`），musl 按绝对路径解析、`LD_LIBRARY_PATH` 无法覆盖 ⇒ 8/8 测试启动即失败。
   修复：`build()` 中把缺失路径物化为指向当前缓存的兼容符号链接（akonadi 25.12.3 先例）。
2. **E537 生产者侧（阻塞产物可消费性）**：ohpcd 的 KF6 库无 DT_SONAME，导致本产物 DT_NEEDED 记录绝对路径。
   用最小 CMake 工程实测 `IMPORTED_SONAME` / `IMPORTED_SONAME_RELEASE` / `IMPORTED_LOCATION` 改写**均无效**（CMake 4.1.2），
   最终采用 `-l:libKF6*.so` + `target_link_directories`（kpackage 26.04.0 E537 推荐变体）。
   另有坑：KF6 目标只设 `IMPORTED_LOCATION_<CONFIG>`，读 generic 属性得到 NOTFOUND；`KF6::CoreAddons/ConfigCore` 必须显式列出，否则 `KJob`/`KAutoSaveFile` 头与符号缺失。
3. **退出码 127 的 G0 误报**：`finish` Step3 clean-verify 对 CMake 工程执行 `./configure`（autotools），
   日志 `bash: ./configure: No such file or directory`；同时伴随 `getcwd: cannot access parent directories: Not supported`。
4. **`gen_summary` 内部错误**：`'str' object has no attribute 'append'`（finish Step8）。
5. **W3 全仓扫描被 main 存量垃圾阻塞**：`origin/main` 跟踪了 3 个未登记隐藏文件
   （`archives/c/cloog/0.21.1/.build-closed`、`archives/c/cloog/0.21.1/.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`），
   未提交状态下 W3 退化为 full 模式即失败；改用 `JUNK_PR_DIFF`（PR diff 口径，与 CI 一致）后全绿。
6. **test_package 断言计数四处不一致**（审计发现）：运行时 18 / MANIFEST 24 / test-report 19 / notes 19，已统一为 18。

### 知识图谱使用情况

- **引用知识条目**: E537（Conan 缓存绝对 DT_NEEDED 泄漏与可重定位 SONAME/链接修复）、E092（CMake 不识别 HarmonyOS）
- **新增知识草稿**: 0 条（`conan-verify` G2 一次通过，未触发 R31 草稿生成）
- **引擎命中情况**: E537、E092 命中并由人工复核落实；manifest `knowledge_gained` 记录 5 条经验（未转正式条目）
- **测试统计**: 上游 10（8 ctest + 2 未注册程序），通过 10，失败 0，跳过 0；test_package 18 断言，通过 18
- **未覆盖的错误模式**: 见「知识图谱覆盖」小节列出的 3 类

### AI 检视结果

- **检视阶段到达**: —（未创建 PR，submit/AI Review 未执行）
- **变更摘要评估**: —
- **检视意见数量**: —
- **检视意见处理**: —

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`JC/L0/L1/L5=pass`，`L2=skip: no bin/ dir` 纯库包，`L4=warn` 正则误报，Pass rate 100%；`reports/w3-local-ci.log`）
- **远程 CI (PR 校验)**: 未知（未提交）
- **CI 失败原因**: 无（本地无失败项；`.ci-result.json` `exit_code=0`，`log_sha256` 与 W3 日志实测哈希一致）

### 效率分析

- **HANDOFF 次数**: 3（finish#1 W3-JC 阻塞 1 次；finish#2 / finish#3 各 1 次 G0 干净构建 HANDOFF）
- **重试次数**: 10 次 `conan create`（其中 4 次失败：源码缓存 0 字节、E537 生产者侧 2 次、静态库链接目标传递 1 次）
  + 3 次 `conan test`（test_package 迭代）
- **关键瓶颈**: E537 可重定位链接 —— 需先证明「KF6 库无 SONAME」，再逐项排除 3 种改写方案，才落到 `-l:` 方案
- **耗时较长的步骤**: E537 定位与修复（含最小 CMake 复现工程）、上游测试入口核验（发现 `ecm_mark_as_test` 不注册 ctest）

---

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-20T23:27:23 | lang_checked | detected=cpp 与任务 cpp 匹配 |
| 2026-09-21T01:01:03 | skeleton_created | result_partial |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **`finish` Step3（G0 clean-verify）对 CMake 工程误用 autotools**：直接执行 `./configure` ⇒ 所有 CMake 包都产生 `exit 127` 假失败（本次 `bash: ./configure: No such file or directory`），且该失败在日志中与真实失败混在一起，容易让 AI 误判为配方问题。建议 G0 按 `manifest.build_system` 或 `conanfile.py` 类型选择验证方式（CMake 工程直接用独立 `conan create`，或复用 W3 结果）；同时 `getcwd: cannot access parent directories` 属 OHOS 已知问题，应识别为平台噪声而非失败。
2. **W3 在未提交状态自动退化为 full 扫描**：junk_check 的三级模式中，`incremental` 依赖 `git diff origin/main...HEAD`，而适配期间变更通常尚未 commit ⇒ 自动降级 `full` ⇒ 被 main 中的存量垃圾（本次为 cloog/kics 的 3 个未登记隐藏文件）阻塞，且阻塞原因与被审核包无关。建议 full 之前增加一级「未跟踪 + 已修改文件」模式（`git status --porcelain` 集合），使未提交状态下的 W3 与 PR diff 口径一致。
3. **`gen_summary` 崩溃**：`finish` Step8 抛 `'str' object has no attribute 'append'`，导致 SUMMARY.md 未能刷新（非致命但每次 finish 都报错）。
4. **JC1/JC5 与 `finish` Step10 的自相矛盾**：Step10 要求创建 `.staging-verified`，而该文件既不在 JC5 白名单、又被 JC1 判为「运行时状态文件」。实测近期已发布包（kcolorscheme/keditbookmarks/accessibility/libktorrent/kio/akonadi）**均未把 `.staging-verified` 与 `packaging/` 纳入 git**，说明这两项是过期期望；建议删除 Step10 这两项就绪检查，或把 `.staging-verified` 登记进 JC5 白名单。

### 模板改进

1. **`conan-init` 构建系统误判**：对 CMake 工程仍生成 autotools 模板（本次 `conanfile.py 模板不可用（autotools）`、`test_package 模板不可用`、`conandata.yml 模板不可用`），迫使 conanfile/conandata/test_package 全部手写。建议优先用 `CMakeLists.txt` / `meson.build` / `configure.ac` 的特征文件探测，而不是依赖 registry 的猜测字段。
2. **KF6/CMake 库缺少可直接复用的配方底稿**：`recipe-search` 可检索到 kguiaddons/kcolorscheme/keditbookmarks，但它们各自的 OHOS 决策分散在 docstring/notes 中。建议为「KDE Gear 26.04 纯 Qt6+KF6 库」提供一份组合模板（ECM_MODULE_PATH 注入 + 手写 conan_cmakedeps_paths.cmake + `-l:` 可重定位链接 + offscreen ctest 沙箱 + E537 运行期桥接），可显著减少重复推演。
3. **test-report 模板缺少「计数一致性」自校验**：本次出现运行时 18 / MANIFEST 24 / notes 19 的三方不一致，直到提交前只读审计才暴露。建议模板与 `finish` 在生成 test-report 时自动回填运行日志中的实测计数（当前为手写）。

### 自动化补全

1. **`.ci-result.json` 可由 `finish` 直接比对 `log_sha256` 与 `reports/w3-local-ci.log`** 并在不一致时自检告警（本次人工核验一致，但机制上值得内建）。
2. **断言计数自动回填**：`conan create` 日志中的 `^  ok   :` 行数可解析，建议 `finish`/`feedback` 用它校验 `test_package/MANIFEST.yml:assertion_count`，不一致时 HANDOFF。
3. **`report`/`notes` 中「上游测试数量」自动校验**：上游注册数可由 `ctest -N --test-dir <build>` 直接取得，建议 `finish` 用它校验 MANIFEST/notes/test-report 的声明值，避免人工漏改。
4. **E537 运行期桥接可工具化**：`_bridge_absolute_needed_paths()`（扫描 ELF 绝对 DT_NEEDED → 物化兼容符号链接）目前在 akonadi 与本包中重复实现，建议抽到 SKILL 的公共 helper，供 KF6 系配方直接调用。

### 知识图谱覆盖

1. **E537 需补充「改写 IMPORTED_* 无效」这一实测结论**：条目现给出「(1) 打 IMPORTED_SONAME / (2) 用 -l: basename」两条路径，本次在 CMake 4.1.2 上实测路径 (1) **无效**（含 `IMPORTED_SONAME`、`IMPORTED_SONAME_RELEASE`、`IMPORTED_LOCATION` 改写三种变体，链接行仍为绝对路径），并附带两个新坑：KF6 目标只有 `IMPORTED_LOCATION_<CONFIG>`（读 generic 得 NOTFOUND）、传递组件 `KF6::CoreAddons/ConfigCore` 必须显式列出。建议把 (1) 降级为「已在 CMake ≥4 失效」并在 rec_approach 中给出 `get_target_property` 的配置回退写法。
2. **建议新增条目（HarmonyOS 平台行为）**：`KEduVocDocument::saveAs()` 等基于 `KAutoSaveFile` 的写入，在**新建 `QTemporaryDir()`（0700）**内会因 autosave/lock 伴随文件创建失败返回 `FileCannotLock`（`qWarning: Cannot lock file <path>`），而写入 `QDir::tempPath()` 正常 —— 属可复现的平台差异，测试代码应据此放置临时文件。
3. **建议新增条目（KDE 库测试漏测陷阱）**：`ecm_mark_as_test()` 在 ECM 中**只**设置 `EXCLUDE_FROM_ALL`、**不调用** `add_test`，因此使用它的测试程序不会出现在 ctest 中（本包 `keduvocdocument/tests/` 的两个程序即如此）。凡是 KDE 系仓库用 `ecm_mark_as_test` 注册测试的，都必须额外显式运行对应可执行文件，否则会「看似全绿实则漏测」。
4. **建议补充 L4 正则误报说明**：`build_and_test.sh` 的 `(strcpy|sprintf|gets|strcat)\b` 会命中普通单词中的子串（如 "Tar**gets**"），凡是注释/文档里含 "Targets" 的补丁都会得到无意义的 `L4 warn`；建议加词边界或改为只扫 C/C++ 源文件。

---

## 作者

- **姓名**: ran060619
- **邮箱**: ran060619@noreply.gitcode.com
- **Agent ID**: DC3F
- **生成时间**: 2026-09-21 01:01:03
- **PR 编号**: —
- **Git Commit**: 42a8cc8fd8
