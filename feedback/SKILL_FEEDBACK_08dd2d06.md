# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_08dd2d06.md`

---

## 背景

- **软件名称**: lbrate
- **版本**: 1.1
- **构建日期**: 2026-09-25
- **构建系统**: makefile
- **上游仓库**: https://ibiblio.org/pub/Linux/utils/compress/lbrate-1.1.tar.gz（ibiblio/Sunsite 发布站点，无 VCS 仓库）
- **适配路径**: 路径 A（基础适配，无补丁；配方 source() 增加 urllib 原始字节回退）
- **补丁数量**: 0
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
| build | 编译构建 | 成功 | 构建系统: makefile |
| conan-verify | 配方验证 | 第 3 次通过 | 第 1 次 G1 缺 export_sources/补丁调用；第 2 次 G2 sha256 mismatch（ibiblio Content-Encoding）；第 3 次 G1-G4 PASS |
| finish | 归档收尾 | 完成 | W3 exit_code=0；step5b（存量 E219/E253/E305 字段为空）与 step8（gen_summary 异常）失败均与本包无关 |
| submit | PR提交+AI检视+CI | 进行中 | fork 旁路手动建 PR；本报告在建 PR 前闭环，AI Review/CI 结果以 PR 页为准 |

### 失败与问题

- **1**: 根因=conan-verify G1: `conanfile.py 缺少: export_sources() 方法 / 补丁应用调用`, 解决方案=G1 固定要求 export_sources + apply_conandata_patches，无补丁也不例外
- **2**: 根因=conan-verify G2: `sha256 hash failed for 'lbrate-1.1.tar.gz'`（Provided ec73e07f…, Computed 66f8e87c…）, 解决方案=ibiblio 按 Accept-Encoding 协商 Content-Encoding：curl/urllib → `x-gzip`，requests（conan）→ `gzip`；requests 透明解码落裸 tar，且 conan 对 `gzip` 豁免尺寸校验，于是不报 Transfer interrupted 而在 sha256 处失败。知识引擎命中 E299（分层诊断），同课题已有 `DRAFT-conan-downloader-xgzip-content-encoding`（x-gzip→传输中断症状）与 `E561-draft-4FE2`（诊断框架）
- **3**: 根因=本机无法执行交付的动态 OHOS 二进制, 解决方案=x86 runner 缺 `/lib/ld-musl-aarch64.so.1`，qemu binfmt-P 下报 `Could not open '/lib/ld-musl-aarch64.so.1'`
- **4**: 根因=prescan critical `PSCAN-HMDFS-001`（Makefile:45 `ln -s`）, 解决方案=仅在 `tgz` 分发目标里，构建只跑 `make lbrate` 不触发

> 自动采集更正：上面 4 条的"根因/解决方案"列是错位的——notes.md 表头是 `# | 问题 | 根因 | 解决方案`，
> 采集器（`scripts/ohc/feedback.py:417`）把"问题"列当根因、"根因"列当解决方案。正确对应：
> 1 G1 缺项 → 补 export_conandata_patches/apply_conandata_patches；2 sha256 mismatch（ibiblio 按
> Accept-Encoding 协商 Content-Encoding）→ 登记发布字节 hash + source() urllib 回退；3 x86 不能执行 →
> test_package 非 aarch64 主机 SKIP + 同源 .o 静态重链 qemu 实跑；4 prescan 误报 → 无需处理。

### 知识图谱使用情况

- **引用知识条目**: E299（G2 失败时引擎命中，源码获取分层诊断）；查重参考 `DRAFT-conan-downloader-xgzip-content-encoding`、`E561-draft-4FE2`、E477（W0 制品仓对未发布包的报错语义）
- **新增知识草稿**: 1 条（`knowledge/drafts/E562-draft-BF48.kv` + 配套 `.md`；自动采集按文件数记成 2 条）
- **引擎命中情况**: G2 sha256 mismatch → E299（分层诊断，方向正确但未给出 Content-Encoding 协商这一具体根因）；自动采集把"草稿目录总数"填进了本字段
- **测试统计**: 上游 N=0/N′=0（确认无测试）；test_package 12 项（鸿蒙特有 2 项）。W3 交付产物：1 通过 / 0 失败 / 11 跳过（x86 不能执行 aarch64 动态二进制）；同源静态重链副本 qemu 实跑：11/11 通过。自动采集读成了"总计 0"
- **未覆盖的错误模式**: ibiblio 对 requests 回 `Content-Encoding: gzip`、对 curl/urllib 回 `x-gzip`，conan 对 `gzip` 豁免尺寸校验 → 静默落解码后 tar → 只剩 sha256 mismatch。已有 x-gzip 草稿只覆盖"Transfer interrupted"症状，本次沉淀为 E562-draft-BF48

### AI 检视结果

- **检视阶段到达**: 本报告在建 PR 前闭环（PR 提交纪律：首次提交即完整内容），检视尚未开始
- **变更摘要评估**: 建 PR 前无摘要；预期关注点：source() 的 urllib 回退是否合规（不调 curl/wget、不换 URL、check_sha256 兜底）
- **检视意见数量**: 0（建 PR 前）
- **检视意见处理**: 建 PR 后由会话内手动复查处理；无必须修改项时不追加 commit

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 未知
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 0 次阻塞型 HANDOFF（finish 仅输出 KNOWLEDGE CONSOLIDATION 收尾块）
- **重试次数**: conan-verify 3 次（G1 结构缺项 1 次、G2 sha256 1 次）；finish 1 次通过
- **关键瓶颈**: G2 sha256 mismatch 的定位——需要分别用 curl、conan 自带 requests、urllib 三种客户端比对响应头与落盘字节，并对照三个已合入 ibiblio 先例的登记 hash，才能确定该登记哪一层字节
- **耗时较长的步骤**: 设计 test_package（上游无测试数据，需按 main.c/readhuff.c/readrle.c 反推 LBR 目录格式与 squeeze 编码器）；Content-Encoding 诊断
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-25T13:09:59 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **本地 W3 与 CI 的源码字节层不一致**：`ci/conan/build_and_test.sh` 预下载用 `curl -sL`（发布字节）改写 file://，
   而 `conan-verify` G2（`scripts/ohc/conan_verify.py:546` 起）直接走 conan 下载器（requests，会解码 Content-Encoding）。
   同一 conandata 在两条路径上可能得到不同 sha256。建议 G2 也复用预下载逻辑，或在 G2 失败且
   `Computed hash == sha256(gunzip(发布字节))` 时直接给出"Content-Encoding 层错位"的明确诊断。
2. **finish step5b 被全库存量问题拖成失败**：`scripts/ohc/finish.py:317-333` 的 W5 检查对 E219/E253/E305 等存量空字段报
   rc≠0，导致每个包的 finish 都记"失败步骤 step5b"。建议 W5 只对本分支新增/修改的条目判定，存量问题单独告警。
3. **SKILL.md「x86 runner 跑不动 OHOS 动态产物」缺统一口径**：test_package 在 `can_run()` 为真（build/host 同为
   armv8 profile）时仍会在 x86 上执行 aarch64 二进制而失败。建议在 SKILL.md §3 给出标准写法：仅当
   `platform.machine()` 非 aarch64 时把运行期用例报 SKIP，aarch64 上探测失败必须硬失败；并配套"同源 .o 静态重链 + qemu"
   的本地验证命令模板。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. **makefile 项目生成了 autotools 库模板**：源码只有 Makefile，`conan-init` 却产出
   `package_type="library"` + `Autotools().configure()` + `cpp_info.libs=["lbrate"]` + CMake test_package。
   原因是 `scripts/ohc/conan_recipe.py:151-155` 优先读版本级 manifest 的 `build.system`，而 init-archive 写入的是
   `autotools`（`scripts/ohc/init_archive.py:253` 日志"模板不可用（autotools）"），源码扫描（`:170-171` 能正确识别 makefile）
   根本没机会执行。建议 init-archive 先扫源码再写 manifest，或 conan-init 在 manifest 值与源码扫描冲突时以源码为准。
2. **版本级 manifest 占位符未渲染**：`templates/manifest-version.yaml:13` `software: "{software}"`、`:21`
   `build_system: "{BUILD_SYSTEM}"` 原样落盘；notes.md 骨架同样带 `{cmake|autotools|…}` 占位符且无门禁校验。
   建议 init-archive 渲染这两个字段，并在 finish 结构检查里对 notes.md/manifest.yaml 做 `\{[A-Za-z_|]+\}` 占位符扫描。
3. **CLI 包缺少 test_package 模板分支**：`templates/test_package-executable` 已存在，但 conan-init 对 application
   类型仍生成 CMake + `test.c` 空壳（`printf("OK")`）。建议按 `package_type`/bindirs 选 executable 模板。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **feedback 自动采集的四处失真**（本报告已手工更正）：
   - `scripts/ohc/feedback.py:417` 取 notes 表格 `cols[2]/cols[3]` 作根因/解决方案，与模板表头
     `# | 问题 | 根因 | 解决方案` 错一列，应为 `cols[3]/cols[4]`（或按表头名定位）；
   - `:551` 新增知识草稿按文件计数（.kv + .md 记 2 条），应按 `.kv` 计；
   - `:552` "引擎命中情况"填的是草稿目录总数，应取 conan-verify 报告里的 `knowledge_hit`；
   - `:553` 测试统计读成 0：test_package 输出了 `passed=1 failed=0 skipped=11`，可解析 W3 日志中的汇总行。
2. **finish step8 `gen_summary` 异常**：`'str' object has no attribute 'append'`，疑为 `scripts/ohc/summary.py:87-89`
   `data.setdefault(key, []).append(...)` 在同名键已是字符串时触发；应在类型不符时重建列表或跳过。
3. **finalize-archive 假告警**：`scripts/ohc/finalize_archive.py:111/119` 仍按已废弃的 packaging/ 规范报
   "目录缺失 / 缺少 release tar.gz"，finish Step 10 也仍要求 packaging/。建议随 ARCHIVE-SPEC v2.0 一并移除。
4. **W3 预下载残留**：W3 在仓库根留下未被 gitignore 的 `.build-cache/predl_cache/<hash>_<file>`，
   建议 `.gitignore` 加 `.build-cache/` 或 W3 结束时清理，避免被误 `git add`。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. **新增草稿 E562-draft-BF48**：ibiblio 按 Accept-Encoding 协商 Content-Encoding（requests→`gzip`，curl/urllib→`x-gzip`），
   conan 对 `gzip` 豁免尺寸校验 → 静默落解码后 tar → 仅表现为 sha256 mismatch。建议主编与
   `DRAFT-conan-downloader-xgzip-content-encoding`（同课题的"Transfer interrupted"症状）、`E561-draft-4FE2`
   （诊断框架）合并为一个正式条目，error_signature 同时覆盖两种症状。draft-review 最高相似 E406=0.38。
2. **存量配方复核**：bsdgames-nonfree 2.17、fortune 9708、mp3info 0.8.5a 同为 ibiblio 源，登记的是解码后 hash
   （实测 raw/decoded 分别为 912a9253…/9afcb4f9…、1a98a6fd…/b288b71f…、0438ac68…/6b600a42…），
   与 CI 预下载的发布字节层相反，CI 预下载成功时应会 mismatch；建议主编复核（本 PR 不动他人归档）。
3. **E544 编号多义**：`knowledge/drafts/E544-draft-*` 下同时存在"config.sub 过旧"与"x86 runner 无 musl loader"等
   不同课题，建议 promote 时拆分编号，便于 engine 精确命中。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: zyj070505
- **邮箱**: z2996336133@163.com
- **Agent ID**: 5CD2
- **生成时间**: 2026-09-25 13:30:26
- **PR 编号**: —
- **Git Commit**: e1087e8b6d
