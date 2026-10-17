# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_bcc2e0e2.md`

---

## 背景

- **软件名称**: ppunpack
- **版本**: 1.0
- **构建日期**: 2026-09-25
- **构建系统**: makefile（上游手写 Makefile；自动采集渲染成 `{BUILD_SYSTEM}`，已人工修正）
- **上游仓库**: https://aminet.net/package/misc/unix/ppsmall-1.0（源码 https://ftp.fau.de/aminet/misc/unix/ppsmall-1.0.tar.Z；自动采集为「未知」，已人工修正）
- **适配路径**: 路径 A（基础适配，无补丁；适配在配方内完成）
- **补丁数量**: 0
- **编译依赖**:
无
- **最终状态**: 成功（conan-verify / finish W3 通过，PR 结果以 CI 为准）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成（需人工介入） | `.tar.Z` 被按 gzip 解，报 `解压失败: not a gzip file`；手工 `zcat` 解到 `.orig` 后重跑 |
| build | 编译构建 | 成功 | 构建系统: makefile；`make ppunpack CC=<OHOS clang> COPTS='-O3 -fPIE -static-pie'` |
| conan-verify | 配方验证 | 通过（第 2 次） | 第 1 次 G1 因「缺 export_sources()/补丁应用调用」失败（本包无补丁） |
| finish | 归档收尾 | 完成 | W3 通过 |
| submit | PR提交+AI检视+CI | PR !12895 已建，1 轮修复 | fork 旁路手动建 PR；评审按 rule4 判不通过（上游 0/1），修复后推送 1 个提交并重新触发 CI |

### 失败与问题

1. `init-build`：`_guess_tar_format()` 不识别 `.tar.Z`，默认 `tar.gz`，解压失败后直接退出（无 HANDOFF 指引）。
2. conan `get()` 不支持 compress(LZW)，报 `BadZipFile`；设备 toybox gzip 也无 LZW → 配方内置 Python LZW 解码。
3. 上游 Makefile `CC=acc` 写死、`all:` 依赖 `check`（样例文件不在 short 分发包）→ make 命令行覆盖 + 只构建 `ppunpack` 目标。
4. conan-verify G1 对无补丁包强制要求 `export_sources()` 与 `apply_conandata_patches`，并把失败打印成 `✅ G1: FAIL`。
5. x86 runner 无法执行动态 OHOS 产物（E544）→ 以 `-static-pie` 链接，qemu-aarch64 直接执行交付产物。

### 知识图谱使用情况

- **引用知识条目**: E392（raw makefile 配方三要素：compiler_executables 取 dict、`cwd=self.source_folder`）、E544-draft-0ADA（静态 CLI 经 qemu 执行功能断言）、E483/E271（相似签名，排除）
- **新增知识草稿**: E6417-draft-CC63（Unix compress `.tar.Z` 在 conan get / init-build / 设备 toybox gzip 上均解不开；配方内置 Python unlzw）
- **引擎命中情况**: `engine "not a gzip file .tar.Z ..."` 未命中；`CC=acc` 命中 E392；draft-review 对 E6417 给出 merge-into E271（signature_overlap 1.0 来自共同的 "not a gzip file" 字样，但 E271 根因是「单文件非归档」，keyword_jaccard 仅 0.06，根因不同，保留独立草稿）
- **测试统计**: 总计 8, 通过 8, 失败 0, 跳过 0（test_package，qemu-aarch64 执行；上游 make check 1/1 + 新增 7/7。首版 PR 把上游用例记为「样例不在 short 包内、不可运行」，被评审按 rule4 判不通过；改为从 Aminet long 版取 sf.pp/sf.chk 实跑）
- **未覆盖的错误模式**: `.tar.Z`/compress(LZW) 源码格式（已沉淀 E6417 草稿）

### AI 检视结果

- **检视阶段到达**: 已收到评审结论（规则审计）
- **变更摘要评估**: 无必须修改项
- **检视意见数量**: 1（rule4：上游有用例 1 个但 0/1 未执行）
- **检视意见处理**: 接受并修复：从 Aminet 官方 long 版取 sf.pp/sf.chk，在 test_package 中实跑上游 make check（1/1）；本地 W4 复审另发现鸿蒙特有用例只是产物头检查，同一提交内改为完整消费者流程

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 首轮已触发；修复提交推送后重新触发，结果以 PR 页为准
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 0（init-build 解压失败直接 exit，未产生 HANDOFF 块）
- **重试次数**: 2（init-build 1 次、conan-verify 1 次）
- **关键瓶颈**: `.tar.Z` 解包——框架与 conan 都不支持，需要自己写并对拍 LZW 解码
- **耗时较长的步骤**: 按 depack.c 位流逆推 PP20 编码器并做码路径覆盖断言；首版 PR 后按评审补实跑上游 make check（数据取自 Aminet long 版），并把鸿蒙特有用例从产物头检查改为完整消费者流程（ppunpack 还原源码 → OHOS clang 编译 → 运行）

---

## 建议

### SKILL 设计改进

- `scripts/ohc/conan_verify.py:491-492`：G1 把 `export_sources` 与 `apply_conandata_patches` 列为必需项，对 `conandata.yml` 无 `patches` 的包也判 FAIL，迫使配方加入 no-op 调用。建议仅在 `conandata.yml` 含 `patches` 或存在 `patches/` 目录时检查这两项。
- `scripts/ohc/conan_verify.py:541`：`log_ok(f"  G1: {'PASS' if g.passed else 'FAIL'}")` 失败时仍用 `log_ok` 打印出 `✅ G1: FAIL`，易误读；失败分支应改用 `log_fail`。
- `scripts/ohc/conan_verify.py:741/800/851/942`：G4 找不到 package ID、L2/L4/L5 「无 cache 路径」时整体仍记 PASS（报告里 `## L4: ✅ PASS` + `⏭️ 跳过`）。建议 skip 单列为 SKIP 状态，不计入 PASS，避免把没跑过的安全扫描当作通过。
- R51 / PR 模板「验证结果」：评审按 rule4 对「上游 N>0 但 N′=0」一律判不通过，任何理由都不接受；SKILL 文本仍写着「逐项列具体技术原因」，容易让人误以为写清原因就够了。建议在 R51 与 `templates/积分赛事PR模板.md` 中写明「上游用例必须实跑，测试数据不在源码包时要从同一上游的其他官方分发物取（固定 sha256）」。
- finish step [3/10] clean-verify(G0) 对手写 Makefile 包仍执行 `./configure`，报 `configure 失败 (exit 127)` 并弹出 G0 HANDOFF 块（非阻塞但会误导）；建议按 manifest `build_system` 选择构建命令，makefile 包跳过 configure。
- finish step [8/10] `gen_summary` 抛 `'str' object has no attribute 'append'`（非致命，但每次 finish 都会把 step8 记为失败步骤）。
- finish step [10/10] 仍要求 `packaging/` 目录（ARCHIVE-SPEC v2.0 已废弃打包产物），属于假告警，建议移除该检查项。
- `lang-preflight`（`scripts/ohc/lang_detect.py:265-270`）不接受 `--out`，与 `result` 的参数习惯不一致，只能靠 `OHC_RESULT_OUT` 指定回执位置；建议加 `--out` 并透传。

### 模板改进

- `conan-init` 对手写 Makefile 的 CLI 包仍套用 autotools+library 模板（`package_type = "library"`、`license = "MIT"`、`cpp_info.libs = ["ppunpack"]`、CMake 版 test_package 与 `test.c`），与 `init-build` 已知的 makefile 形态不符。建议按 build_system=makefile 且无库产物时生成 application 骨架（参考 E392 三要素）与 shell/python 版 test_package。
- 版本级 `templates/manifest-version.yaml:13` 的 `software: "{software}"` 与 `build_system: "{BUILD_SYSTEM}"` 在 conan-init 后未渲染，`tar_format` 注释也只列 `tar.gz | tar.xz | tar.bz2 | zip`；建议渲染占位并补充 `tar.Z`。
- 生成的 `conandata.yml` 是非版本键写法且 `sha256: "REPLACE_WITH_ACTUAL_SHA256"`，而 init-build 已经算过 tarball 的 sha256（`.orig/.tarball-sha256`）；建议直接写入版本键 + 实际 sha256。

### 自动化补全

- `scripts/ohc/init_build.py:89-93` `_guess_tar_format()`：只识别 `tar.xz/tar.bz2/tar.gz/zip`，其余缺省 `tar.gz`。建议按文件魔数（`1f 9d` compress、`1f 8b` gzip、`BZh`、`fd 37 7a 58 5a`、`PK`）判定，并为 compress 加一条解码路径（构建机上 `gzip -dc` 即可，或复用 Python unlzw）；识别失败时输出 HANDOFF（含「手工解到 .orig 后重跑」的命令），而不是只打印 `解压失败` 就退出。
- `scripts/ohc/feedback.py:300/321`：构建系统取自版本 manifest 的 `build_system`（conan-init 后为未渲染的 `{BUILD_SYSTEM}`），上游仓库取不到就写「(未知)」。建议回退到 `.build-context-<name>-<ver>` 与 `conandata.yml` 的 URL；补丁数/测试统计同样可从 `conandata.yml` 与 `test_package/MANIFEST.yml` 的 `assertion_count` 读取。
- conan-verify 的 G2 失败之外，可对 `source()` 中出现的 `gzip -dc|zcat|uncompress` 调用给出预警（设备 toybox 无 LZW），接入 prescan 的 `prescan_pattern` 机制即可。

### 知识图谱覆盖

- 新增草稿 **E6417-draft-CC63**：compress(`.tar.Z`, LZW) 源码格式——conan `unzip()` 落入 zip 分支报 `BadZipFile`（与 E483 同签名、根因不同）、init-build 报 `not a gzip file`、设备 toybox gzip 无 LZW；推荐配方内置 Python unlzw，回退 `cmake -E tar`（cspice 先例）。建议主编 promote，并在 E483 的 `similar_to` 里互链，便于引擎在 `BadZipFile` 签名下区分两种根因。
- 建议给 E392（raw makefile）补一条：Makefile 内的 `CC=xxx` 赋值会压过环境变量 CC，只能用 make 命令行赋值覆盖；以及「默认目标依赖测试样例、样例不在分发包内」时应显式构建产物目标。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: 04A6
- **生成时间**: 2026-09-25 23:19:24
- **PR 编号**: !12895
- **Git Commit**: 基线 origin/main 2e478fc4a2（本报告所在提交即 PR 的适配提交）
- **备注**: 知识草稿后缀 CC63 由 `graph add --draft` 随机生成，与本报告 Agent ID 04A6 不同，属同一任务
