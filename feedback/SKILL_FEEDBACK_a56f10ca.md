# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_a56f10ca.md`

---

## 背景

- **软件名称**: metaeuk
- **版本**: 7-bba0d80
- **构建日期**: 2026-09-23
- **构建系统**: cmake
- **上游仓库**: https://github.com/soedinglab/metaeuk（tag `7-bba0d80`，codeload 归档 tarball，MMseqs2 以 `lib/mmseqs/` 内置随附）
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 1
- **编译依赖**:
无
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | sha256 `45eff3cb…3898fa` 核对通过 |
| build | 编译构建 | 成功 | 构建系统: cmake；主包全量重编 203 个 CXX 目标（证据 `~/tmp/uc2/zhuli1-metaeuk/g2-pass-build-20260923T0302/conan-create.log`） |
| conan-verify | 配方验证 | PASS | G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS，见 `archives/m/metaeuk/7-bba0d80/reports/conan-verify-report.md` |
| finish | 归档收尾 | 完成 | L1e 转 PASS 后 W3 本地 CI 模拟通过；`finalize-archive` 的补丁数告警已于本轮整改（manifest `patches_applied` 与 `patches/` 对齐） |
| submit | PR提交+AI检视+CI | 未执行 | 本报告产出时本任务尚未 submit，PR 编号为 `—`，远程 CI 与 AI Review 均未触发 |

### 失败与问题

流程中出现三处真实问题，均已定位根因并闭环（非"未遇到问题"，原自动摘要在此处偏乐观，据实更正）：

1. **toybox `xxd -i` 导致资源头连锁编译失败**（已由 `patches/0001-mmseqs-resource-compiler-toybox-xxd-no-declaration.patch` 修复）。
   机制：OHOS 的 `/usr/bin/xxd` 是 toybox 实现，`xxd -i` 只输出裸 hex 数组体，不产出 vim xxd 的 `unsigned char 名[] = {…}` 声明行与 `名_len` 长度变量；MMseqs2 的 MMseqsResourceCompiler 因此生成的头文件无声明，`data/` 下 easypredict.sh 等内嵌资源脚本编译连锁报 no declaration。补丁跳过 xxd 探测、强制走 `xxdi.pl` 分支。
2. **消费者测试断言与真机实测不符**（已重写为 5 项，断言数由 4 增至 5）。
   真机实测发现 `--version` 并非合法子命令（非零退出），版本横幅只能从裸 `metaeuk`（无 tty / popen）取；`easy-predict` 合成数据零命中 → 产物 `predictions.fa.fas` 为 0 字节，只能证工作流跑通、不证预测正确性，故补 A4b `createdb` 非空往返（`db` 140B / `db_h` 48B）作为自含可证伪断言。最终 5 项断言全过。
3. **W3 的 L1e（R34 破坏性反向验证）失败**（已由提交 `1c46faad7a` 闭环）。
   根因在框架侧：`ci/conan/build_and_test.sh:1646` 调用 `conan test` 时只传 `-pr`、漏传 `-pr:b`，build profile 回落到 `profiles/default`（os=Linux），于是 `os_build != os_host`、`can_run()` 判假、`test()` 整体静默短路——`conan test` 0.3 秒 rc=0 空转，框架据此判"测试不依赖被测包"。同一脚本 `:316` 的 `conan create` 同时给了 `-pr:h` 与 `-pr:b`，所以 create 阶段测试是真跑的。本包在真机与 CI worker 上均以 `-pr:b=host` 原生构建，不存在合法交叉编译场景，故去掉该短路、让消费者无条件执行；复刻 L1e 命令行（仍不带 `-pr:b`）实测由 0.3s 空转变为 8.42s 真执行。

### 知识图谱使用情况

- **引用知识条目**: `knowledge/drafts/DRAFT-E321-cmake4-policy-version-minimum.kv`（**其验证实例为 etcd-cpp-apiv3 0.15.4**，取自该文件 `# Software:` 行实测；本包是该机制在 CMake 2.8.x 老基线上的再次命中——CMake 4 拒绝 `cmake_minimum_required(2.8.12)`，须以 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 在解析前注入，写 `tc.variables` 时序无效。更正说明：本行原写「cpputest 4.0 实证」，经复核 `grep -rln cpputest knowledge/drafts` 只有两条与本机制无关的 libnfc-tools 草稿，知识库内不存在 cpputest + `CMAKE_POLICY_VERSION_MINIMUM` 条目，出处不实已改）；G0 自动命中的 E092（CMake 不认识 HarmonyOS 目标平台）已在配方中处理。
- **新增知识草稿**: 2 个文件（成对落盘）——`knowledge/drafts/DRAFT-metaeuk-7-bba0d80-toybox-xxd-i-bare-hex-resource-header.md` 与同名 `.kv`，关联 Issue #3249。
- **引擎命中情况**: 草稿目录 1398 条
- **测试统计**: 上游套件 N_static=0 / N_registered=0 / N_executed=0，如实申报不虚构。清点口径（本轮补全，此前只写了子模块一项）：① 全源码树 `add_test(` / `enable_testing` / `include(CTest)` 在 `--include=CMakeLists.txt --include=*.cmake` 下命中 0/0/0，`Makefile.am`/`configure.ac` 各 0 ⇒ 无任何测试注册入口；② 随包的 `lib/mmseqs/src/test/` 共 42 条目（36 个 `.cpp` + CMakeLists.txt + 名为 `0` 的文件 + 4 个 dataGap/dataLinear 数据文件），36 个 `.cpp` 里 **35 个各自带 `int main`**、`assert(` 仅 3 文件共 29 处，性质是上游手工自测 harness（兼回归工具）而非注册可执行测试，不折算成用例；其入口 `add_subdirectory(test)` 位于 `lib/mmseqs/src/CMakeLists.txt:243` 的 `if (NOT FRAMEWORK_ONLY)` 块内，而根 `CMakeLists.txt:6` 以 `set(FRAMEWORK_ONLY 1 CACHE INTERNAL "" FORCE)` 强制锁死（`HAVE_TESTS` 亦默认 0），且 `MMseqsSetupTest.cmake` 的 `mmseqs_setup_test()` 只 `add_executable`、不含 `add_test()` ⇒ 即便开启也不产生 CTest 用例；③ `tests/`（metaeuk-regression 回归数据集）与 `lib/mmseqs/util/regression` 是根 `.gitmodules` 声明的两个子模块，GitHub tag 归档不含其内容（tar 内为空目录），azure-pipelines/.cirrus 为外部下载驱动回归。消费者测试 N_consumer=1 用例、5 项行为断言全通过，失败 0、跳过 0。
- **未覆盖的错误模式**: 两类——① "构建期外部工具实现差异"家族（toybox vs vim/coreutils 的同名命令行为不同）在引擎里没有正式 E-entry，本次以新增 DRAFT 补位；② "测试被静默跳过却被判通过"（`can_run()` 在缺 `-pr:b` 时的短路）无任何可检索条目，见下方知识图谱覆盖建议。

### AI 检视结果

- **检视阶段到达**: 未到达（本任务尚未 submit，PR 未创建，`/ai review` 未触发）
- **变更摘要评估**: 无数据——AI 检视尚未发生，本报告不预测其结论
- **检视意见数量**: 0（尚无检视意见，非"已处理完毕"）
- **检视意见处理**: 不适用；提审四件套的第②项（未解决意见全部回复并 resolve）留待 CIW 在 PR 建好、意见回来后处理

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`archives/m/metaeuk/7-bba0d80/reports/w3-local-ci.log`：`L0_RESULT=pass` / `L1_RESULT=pass` / `L2_RESULT=pass` / `L4_RESULT=pass` / `L5_RESULT=pass`，`[ok] L1e: Negative test confirmed — test genuinely depends on metaeuk`，Build Summary 1/1 100%）
- **远程 CI (PR 校验)**: 未触发（无 PR）
- **CI 失败原因**: 无（L1e 曾在 04:17 的运行中报 `L1_RESULT=fail: negative test: test does not depend on package`，修复后通过）

### 效率分析

- **HANDOFF 次数**: 框架侧事件文件 `.ohc/feedback-state/m/metaeuk/7-bba0d80.json` 仅记录 1 条 `skeleton_created`（detail=`result_partial`），未落任何 handoff 类型事件；实际人工介入按主理派工口径为 9 轮整改。两者不一致本身是一个可改进点（见 SKILL 设计改进第 3 条）。
- **重试次数**: 可核实的返工节点 4 处——`conan-verify` 一次 rc=2（03:02:38）后转 rc=0（03:18:46）；`finish` 两次 rc=2（03:19:54→03:25:46、03:32:27→03:43:52）；W3 的 L1e 失败 1 次（04:17 运行）后于 04:53 运行通过。
- **关键瓶颈**: ①L1e 根因定位——失败信息只说"W3 本地 CI 模拟失败"，需自己下钻到框架脚本第 1646 行才发现是缺 `-pr:b` 的静默短路，占了最多轮次；②主包体量大（MMseqs2 内嵌源码，203 个 CXX 目标），任何一次干净重建都是十分钟级，隔离 CONAN_HOME 下无法靠缓存绕过。
- **耗时较长的步骤**: 整轮 W3 本地 CI 模拟（`setup.sh` + `build_and_test.sh`）实测 12 分 11 秒（04:17:11→04:29:22，主包命中缓存）；含 G2 干净构建的 `finish` 整轮 11 分 25 秒（03:32:27→03:43:52）。两者均远低于框架默认 3600s 预算。

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-23T03:18:46 | skeleton_created | result_partial |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **L1e 与 create 阶段的 `conan test` profile 参数不同源**（`ci/conan/build_and_test.sh:1646` 只传 `-pr`，`:316` 的 create 传 `-pr:h` + `-pr:b`）。同一份 test_package 在两个闸门下语义不同：漏 `-pr:b` 使 build profile 回落 `profiles/default`（os=Linux），`can_run()` 判假 → `test()` 空转 0.3s 仍 rc=0 → L1e 反判"假测试"。结果是**包作者被迫删掉一个合法的 `can_run` 守卫才能过闸门**，这是框架缺陷外溢到归档。建议框架层给 L1e 补 `-pr:b`（与 create 同源）后重跑本包回归，确认去掉守卫并非唯一解。
2. **`finish` 的 W3 失败回显粒度太粗**：HANDOFF 正文只有"W3 本地 CI 模拟失败 — 阻塞"，不指明失败子闸门。建议把 `L1a/L1b/L1e` 中具体哪一项失败、以及该项的判据原文一起回显；本次若直接给出 `L1_RESULT=fail: negative test…`，定位能省掉数轮。
3. **feedback 事件累积与实际返工脱节**：状态文件只有 `skeleton_created`，而实际经历了 verify rc=2、两次 finish rc=2、一次 L1e 失败。`record_event` 是"尽力而为、异常静默吞掉"的设计，导致"效率分析"段失去自动可信度——建议对阻塞类失败（`cmd_finish`/`cmd_verify` 返回非 0）强制记一条事件，不吞。

### 模板改进

1. **背景段"上游仓库 (未知)"本可自动填**：`conandata.yml` 的 `sources.url` 就是上游 tag tarball 地址，`_collect_background` 未取用。建议直接从 conandata 解析，减少一处人工补。
2. **`manifest.yaml` 的 `patches_applied` 与 `patches/` 目录无同步机制**：本次 `finalize-archive` 报"补丁数不一致 manifest=0 vs disk=1"，而 `conandata.yml:10-14` 里补丁名、描述、类型齐全。建议 `init-manifest` 时按 `conandata.patches[].patch_file` 预填，或至少在收尾时自动对齐——这类不一致靠人工补必漏。
3. **test_package 模板默认带 `can_run(self.settings)` 守卫**，而模板注释未提示它与 R34 反向验证的相互作用（见 SKILL 设计改进第 1 条）。建议在模板里显式写明："若使用 `can_run` 守卫，务必确认 CI 的 `conan test` 传了 `-pr:b`，否则测试会静默跳过并被判为假测试"。
4. **"失败与问题"段在无阻塞失败时自动写"本次流程未遇到阻塞性问题"**，掩盖了已闭环的历史问题；建议模板改为区分"当前阻塞 / 已闭环问题"两栏，避免报告被误读成"一路顺利"。

### 自动化补全

1. **超时登记不该靠人工读日志**：`ci/config/build_timeouts.txt` 目前由人手工加行。建议 W3 结束时把实测 wall time 自动打印为候选条目，并给出"是否超过默认预算"的判定——本包实测整轮 12m11s，远低于默认 3600s，本轮据实撤销了 `metaeuk/7-bba0d80 10800` 这行登记（框架文件不得混入配方 PR）。
2. **破坏性反向验证的"空转 vs 真跑"信号没被量化**：L1e 已经会把 `bin/` 移走再跑，但只回 rc。建议同时打印 `conan test` 耗时与 `test()` 是否产出真实 stdout——秒级 rc=0 而零输出正是本类假阴性的强特征，可做成自动探针而不是靠人看。
3. **"新增知识草稿"字段与 `knowledge/drafts/` 无联动**：报告自动填了"无"，而磁盘上确有 2 个成对草稿文件。建议按 `<软件名>-<版本>` 前缀匹配草稿目录自动回填，省掉人工更正。

### 知识图谱覆盖

1. **建议把本次的 toybox 机制升为正式 E-entry**：判据 = 构建期用 `xxd -i` 生成内嵌资源头（MMseqs2 系、以及任何把二进制/脚本 embed 进 C++ 的项目）；现象 = 生成的头缺 `unsigned char 名[] = {…}` 声明与 `名_len` 变量，连锁报 no declaration；处置 = 跳过 xxd 探测、强制走 `xxdi.pl` 分支。当前只以 DRAFT 形式存在（`DRAFT-metaeuk-7-bba0d80-toybox-xxd-i-bare-hex-resource-header`，Issue #3249），下一个撞上的包应当能直接命中。
2. **建议新增"测试被静默跳过却报通过"家族条目**：症状 = `conan test` 秒级返回 rc=0、日志无 `test()` 真实输出、L1e 判"test does not depend on package"；根因 = 消费者测试里的 `can_run()` 在 CI 缺 `-pr:b` 时判假。这条与 (1) 不同层，属 CI 闸门行为，知识图谱目前完全未覆盖。
3. **"构建期外部工具实现差异"是一个尚未成族的空白**：toybox 与 vim/coreutils 同名命令行为不同（`xxd`、`hexdump`、`base64` 等）在 OHOS 上会反复出现，值得立一条通用探针条目，而不是每个包各自重新发现。已可复用的家族（CMake 4 兼容 DRAFT-E321、平台识别 E092）本次确实一次命中，说明正式 E-entry 的复用价值高于 DRAFT。

---

## 作者

- **姓名**: wanderlust_0823
- **邮箱**: wanderlust_0823@noreply.gitcode.com
- **Agent ID**: 4A0C
- **生成时间**: 2026-09-23 03:18:46
- **PR 编号**: —
- **Git Commit**: 94325a6e61
