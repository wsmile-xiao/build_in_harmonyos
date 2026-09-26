# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_81e01102.md`

---

## 背景

- **软件名称**: jellyfish
- **版本**: 2.3.1
- **构建日期**: 2026-09-21
- **构建系统**: autotools
- **上游仓库**: https://github.com/gmarcais/Jellyfish
- **适配路径**: 路径 A（基础适配，6 个可移植性补丁）
- **补丁数量**: 6
- **编译依赖**:
无（htslib/SWIG 均可选，配方 `--disable-htslib` 保证可复现）
- **最终状态**: 成功（PR #11589 已提交；远程 CI 因平台故障恢复后重触发中）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | sha256 `ee032b57...0fcd` |
| build | 编译构建 | 成功 | 构建系统: autotools；上游 `make check` TOTAL 15 / PASS 10 / SKIP 5 / FAIL 0 |
| conan-verify | 配方验证 | 通过 | G0–G4 + L2/L4/L5 全 PASS；消费者测试 11/11 |
| finish | 归档收尾 | 完成 | W3 本地 CI PASS；仅 step5b 全局知识库告警（非阻塞） |
| submit | PR提交+AI检视+CI | PR #11589 已创建；AI Review: ✅ 未发现问题；CI: 平台故障期触发未入队（见下） |

### 失败与问题

1. **lang-preflight 误报（阻断级误判，已按证据纠正）**：jellyfish 为 autotools + 94% C++ 源码，但 `scripts/ohc/lang_detect.py` 的 manifest 扫描对 `setup.py` 做**递归**匹配（`names = {p.name for p in files}`），命中可选 SWIG 绑定的 `swig/python/setup.py`，将构建系统判为 setuptools，再与源码统计冲突判为 `mixed`，自动写入 `env_unsupported` 终态（退出码 2）。经根因核实（顶层 configure.ac/Makefile.am、源码 94% cpp）判定为工具缺陷，未按误报终止，最终 `result --status partial --force` 覆盖；已在"建议"中给出修复方案。
2. **平台命名管道限制（真实平台限制）**：HarmonyOS 对 `mkfifo(2)` 全局返回 EPERM（实测 HMDFS、构建目录、`/dev/shm` 均拒绝，toybox 亦无 mkfifo 命令）。jellyfish generator 输入（`-g`/`-G`）不可用；上游测试以运行期能力探测处理（等价回退/跳过），已入草稿 DRAFT-7605。
3. **平台 CI 调度故障（非代码问题）**：PR #11589 于 01:52、12:47、19:11 三次 `/rebuild` 均被机器人受理，但**从未生成排队构建**（无「构建已开始」、无构建链接；`ci-status`=UNKNOWN）。故障期 CI 看板 10 小时仅推进 ~2 条构建、22 条长期"构建中"；平台恢复后（19:10 近期构建 #54353–#54401）新 PR 正常出结果，暴露出旧触发未入队且机器人对**同一 SHA 去重**（旧 `pending-39ab8e8b` 记录卡住后续重触发）。

### 知识图谱使用情况

- **引用知识条目**: E160（config.guess 识别 HarmonyOS）、E011/E114（HMDFS umask 权限）、E002（/tmp 只读 EROFS）
- **新增知识草稿**: `knowledge/drafts/DRAFT-7605-jellyfish-mkfifo-named-pipes-unavailable`（kv+md 成对）
- **引擎命中情况**: 草稿目录 1397 条；本次 `engine` 命中 E160（config.guess）
- **测试统计**: 总计 15（automake TESTS），通过 10, 失败 0, 跳过 5；gtest 51310/51310；消费者测试 11/11
- **未覆盖的错误模式**: mkfifo EPERM（已建草稿）；toybox `unix2dos` 不支持 `-n <in> <out>`（建议沉淀）；平台 CI 触发未入队/同 SHA 去重（平台侧，建议知会主办方）

### AI 检视结果

- **检视阶段到达**: PR 创建后 atomgit-bot 自动完成（本次以 `submit --no-wait` 提交，未走 5 阶段监控；PR 创建后 15s 内机器人自动产出摘要+审查）
- **变更摘要评估**: 与实现一致（6 补丁、11 条消费者断言、FIFO 能力探测与平台限制披露均被准确概述）
- **检视意见数量**: 0（「✅ 未发现问题」）
- **检视意见处理**: 无需修复；1 条 Info 级笔记属 GitCode 不可解决类型（HTTP 400），不计入合并门禁

### CI 结果

- **本地 CI 模拟 (W3)**: PASS（与平台同脚本 `ci/conan/build_and_test.sh`，`.ci-result.json` exit_code=0）
- **远程 CI (PR 校验)**: 未入队（平台调度故障；恢复后第 4 次触发以新 SHA 进行）
- **CI 失败原因**: 无（非代码/配方问题）

### 效率分析

- **HANDOFF 次数**: 1（finish step5b 全局知识库字段缺失告警，非阻塞）
- **重试次数**: 构建类 0（conan-verify/W3/finish 内构建均一次通过）；CI 触发 4 次（平台故障期 3 次被吞 + 新 SHA 1 次，均为规则允许的"未入队重触发"）
- **关键瓶颈**: 平台 CI 调度故障（约 18 小时不可用）；HMDFS 权限与命名管道平台限制
- **耗时较长的步骤**: `make check`（-j1 串行 ~9 分钟）、3 次完整 `conan create`（verify/W3/finish 内嵌）

---

## 建议

### SKILL 设计改进

1. **lang_detect 递归匹配缺陷（建议 P1 修复）**：`_manifest_scan` 对 `pyproject.toml/setup.py/setup.cfg`（以及 Cargo.toml/go.mod 等）只在**顶层**匹配（与 CMakeLists/package.json/meson.build 已有的 `tops` 用法一致），否则任何带可选 Python 绑定/打包脚本的 C/C++ 项目都会被误判 `mixed` 并自动写 `env_unsupported` 终态（本次 jellyfish、以及大量含 `swig/python/setup.py`、`bindings/python/pyproject.toml` 的项目都会中招）。建议同时增加"证据复核"逃生口（如 `--override-with-evidence "检测证据"`），允许在检测与顶层构建系统/源码统计明显矛盾时人工纠正并留痕。
2. **CI 触发未入队可观测性**：机器人在「30s 内未查到排队构建」后应持续探测并在超时后主动告警/重试（或允许以 `PR-SHA` 去重键失效重触发），而不是静默停留在 pending；本次同一 SHA 的去重记录使后续 3 次 `/rebuild` 均未生效。
3. **`finish` 对非本包知识告警的降级**：step5b 因语料中其他条目（E219/E253/E305）字段缺失把 finish 判为部分失败（rc=1），建议对本包无新增告警时保持 rc=0，避免误读为流程失败。

### 模板改进

1. `ohc-run.py conan-init` 生成的 `manifest.yaml` 仍含 `{software}`、`{BUILD_SYSTEM}` 占位符（本次 init-build 阶段模板"不可用"导致），建议补齐自动填充；feedback 骨架的 `{BUILD_SYSTEM}` 同样未被替换。
2. `templates/notes.md` 的关闭标记建议与 `close-archive` 追加的标记合并为一处，避免重复"编译结束"段落。

### 自动化补全

1. **refresh-patch --auto 的 manifest 文本改写 bug**：本次它把 `knowledge_gained` 中 `config.status: subs1.awk` 改成了 `built.awk`（疑似把 `subs1` 当占位符替换为 status 值），建议修复；同时它把手工维护的 `patch_classification`（type/guard）重置为 `auto/pending`，建议保留已有分类。
2. **W3 预下载镜像还原**：`build_and_test.sh` 本次把 `gh-proxy.com` 镜像 URL 写入归档内 `conandata.yml` 后**未还原**（遗留 `conandata.yml.orig`/`.ghfast-bak`），需人工恢复官方源，否则会命中 PF7 源 URL 闸；建议修复 trap/还原路径。
3. **CI 触发失败的自动换 SHA**：可考虑在检测到"未入队且平台已恢复"时提示（或自动）以新提交触发，减少人工介入。

### 知识图谱覆盖

1. 新增 `mkfifo(2)` 全局 EPERM（HarmonyOS）条目（本次草稿 DRAFT-7605 已提交待 promote）。
2. 建议新增 "toybox 命令语义差异" 条目（`unix2dos` 不支持 `-n <in> <out>`；同类还有 `md5`、`dos2unix` 等），并汇总常见 toybox/coreutils 差异对照。
3. 建议复核 E490（autotools 执行位）与本次 G0 实测的差异（本次 6 补丁后无执行位问题），必要时补充"构树方式（in-tree vs VPATH）与执行位关系"的说明。

---

## 作者

- **姓名**: kasumizawa-miyuu
- **邮箱**: 241250031@smail.nju.edu.cn
- **Agent ID**: 9C4A
- **生成时间**: 2026-09-21 19:15 (Asia/Shanghai)
- **PR 编号**: 11589
- **Git Commit**: 39ab8e8b8
