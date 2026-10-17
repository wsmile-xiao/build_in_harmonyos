# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_3b421ab1.md`

---

## 背景

- **软件名称**: lfanew
- **版本**: 0-20230825
- **构建日期**: 2026-09-26
- **构建系统**: autotools
- **上游仓库**: https://gitlab.com/tkchia/lfanew （tag 20230825；自动采集填成了 tarball URL，已手工更正）
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
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: autotools |
| conan-verify | 配方验证 | 通过 | G1/G0/G2/G3 PASS，首次即过；G4/L2/L4/L5 因包 ID 解析失败被静默跳过（见建议） |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | 未开始 | fork 贡献者走手动建 PR 旁路；本报告在建 PR 前闭环 |

### 失败与问题

（自动采集把 notes.md 表格的「问题/根因/解决方案」三列错位读取，且漏掉了第 2 行，以下为手工更正）

- **1**: 现象=`Invalid configuration 'aarch64-linux-ohos': system 'ohos' not recognized`（`aarch64-unknown-linux-ohos` 亦被拒）；根因=源码自带 2016 年 config.sub 不认 ohos；解决=configure 无运行期探测，配方 `update_configure_args({"--host": "aarch64-unknown-linux-musl"})`
- **2**: 现象=`a/direntdup.c: use of undeclared identifier 'NAME_MAX'`；根因=OHOS musl `<dirent.h>` 不传递包含 `<limits.h>`；解决=一行补丁 `#include <limits.h>`（草稿 E721）
- **3**: 现象=x86 runner 上动态 OHOS 产物无法运行（E544）；解决=libc-only CLI 与消费者探针 `-static`，qemu-aarch64 实跑交付产物本体
- **4**: 现象=conan-verify G0 预警 E490（autotools 脚本执行位）；结论=上游 tarball 权限正确，预防性提示，未处理

### 知识图谱使用情况

- **引用知识条目**: E122（不适用于旧版 config.sub，据此改走 --host 覆盖）、E544（静态 CLI + qemu 实跑）、E490（G0 预警）
- **新增知识草稿**: 1 条（E721-draft-B1C7，.kv + .md；自动采集按 manifest knowledge_gained 行数计成 2 条）
- **引擎命中情况**: 草稿目录 1941 条
- **测试统计**: 总计 39, 通过 39, 失败 0, 跳过 0（test_package 消费者断言；上游 autotest 8 个用例中可运行 2 个、通过 2 个）
- **未覆盖的错误模式**: `NAME_MAX` 未声明——engine 误命中 E493（program_invocation_name，仅因共享 'undeclared identifier' 关键词），已沉淀为草稿 E721

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: PR 尚未创建（本报告需在建 PR 前闭环入仓），暂无
- **检视意见数量**: 0（尚未检视）
- **检视意见处理**: 不适用

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 未知
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 0（finish 仅输出 KNOWLEDGE CONSOLIDATION 收尾块）
- **重试次数**: 手工编译 1 次失败（NAME_MAX）后修复；conan-verify / finish W3 均一次通过
- **关键瓶颈**: 任务给定的 Debian `+dfsg` 源会被 PF7 拦截，需先到上游 GitLab 找到对应 tag 并逐文件 diff 确认等价
- **耗时较长的步骤**: 设计 rule12 消费者用例（需读 lfanew.c 精确推导三种模式输出字节）；conan create 本身 < 1 分钟
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-26T12:10:06 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **init-build 应在下载前就执行 PF7 同口径的源 URL 检查**：本次任务给的 `deb.debian.org/...+dfsg.orig.tar.xz` 被 `init-build` 照单全收，
   `conan-init` 又把它原样写进 `conandata.yml` 与 `manifest.yaml`，直到建 PR 前 `scripts/ohc/preflight.py:379-381`（`_PF7_DEBIAN_HOSTS` / `+dfsg`）才会拦。
   建议 init-build 复用 `preflight._pf7_reason()` 在 Step 2（URL）即告警，并提示「到 debian/copyright 的 Source 字段找上游」——本包 `debian/copyright` 第 3 行就写着 `Source: <https://gitlab.com/tkchia/lfanew>`，可自动提取。
2. **finish 的 refresh-patch 会覆盖人工补丁分类**：`scripts/ohc/refresh_patch.py:527-534` 每次都把 `patch_classification` 重写为 `type: auto / platform_only: True / guard: pending`，
   AI 在 finish 前填好的 portability / none 被 finish 冲掉（本次需在 finish 后再手工恢复）。建议补丁内容哈希未变时保留既有分类。
3. **R46 里程碑草稿被他人任务的终态回执压制**：`scripts/ohc/result_report.py:782-788` 只看 `$HOME/ohpcd-ai-worker-result.json` 是否 `draft:false`，
   不比对 software/version，于是本次 lang_checked / recipe_generated / conan_verify_passed 三个里程碑草稿全部被跳过。建议比对 `prev["software"], prev["version"]` 不同时照常覆盖（或按包名分文件）。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. **conandata 骨架与仓库约定不一致**：`conan-init` 生成 `sources: {url, sha256}`（无版本键），`templates/conanfile-autotools.py.tmpl:41` 等 5 个模板写
   `get(self, **self.conan_data["sources"], ...)`；而仓库绝大多数配方用版本键 + `self.conan_data["sources"][self.version]`。建议模板与 conan-init 统一为版本键形态，sha256 直接由 init-build 已算好的 `.tarball-sha256` 回填（本次仍是 `REPLACE_WITH_ACTUAL_SHA256`）。
2. **autotools 模板对「库 + CLI」混合包猜错类型**：骨架给出 `package_type = "library"`、`options shared`、`cpp_info.libs = ["lfanew"]`（实际库名 `libfanew.a`，无 shared 选项、另有 bin/）。
   建议 conan-init 读取 staging（或 Makefile 的 LIBRARIES/PROGRAMS）推断库名与是否有可执行文件，混合包生成 `static-library + bindirs + commands.json` 提示。
3. **manifest.yaml 骨架残留 `{software}` / `{BUILD_SYSTEM}` 占位符**，且没有门禁检查；建议与 notes.md 一起纳入 `grep '\{[A-Za-z_]+\}'` 占位检查。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **feedback 自动采集纠错**（`scripts/ohc/feedback.py`）：①「失败与问题」解析 notes 表格时列错位（把「问题」当根因、「根因」当方案）并漏掉含反引号的第 2 行；
   ②`knowledge_drafts`（:388）按 manifest `knowledge_gained` 行数计，应改为统计 `knowledge/drafts/*-draft-<AgentID>.kv`；③测试统计出现「总计 0, 通过 39」，总计应取同源；④「上游仓库」取了 tarball URL，应取 conanfile `homepage`。
2. **conan-verify G4 包 ID 解析恒失败**：`scripts/ohc/conan_verify.py:735-737` 用 `listing["Local Cache"][self.software][self.ref]` 取包，
   但 Conan 2.29 `conan list <ref>:* --format=json` 的键直接是 `"<ref>"`（无 software 这一层），于是 G4 报「无法找到程序包 ID」且 L2/L4/L5 全部「跳过（无 cache 路径）」却仍显示 PASS。建议去掉 `[self.software]` 一层，解析失败时判 WARN 而非 PASS。
3. **finish step8 `gen_summary` 失败**：`'str' object has no attribute 'append'`（`scripts/ohc/finish.py:337` 调用链），导致 finish 汇总为「部分完成」；建议加回归用例。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. 新增草稿 **E721**（本 PR）：OHOS musl `<dirent.h>` 不传递 `<limits.h>` 导致 `NAME_MAX` 未声明，推荐无条件补 `#include <limits.h>`；
   回退方案记录旧版（2016）config.sub 在无运行期探测时用 `--host=aarch64-unknown-linux-musl` 绕过。查重：`draft-review` 最高相似 E500（0.30，MAX_INPUT），E543-draft-2EE3 为同族 PATH_MAX 案例。
2. **engine 粗筛过度依赖通用关键词**：`use of undeclared identifier 'NAME_MAX'` 被 Phase B 判给 E493（program_invocation_name），两者只共享 "undeclared identifier"。
   建议 Phase A 对 `undeclared identifier '<X>'` 类签名以标识符 `<X>` 作为必需匹配项，避免同类误配。
3. 建议把 E543-draft-2EE3（PATH_MAX）与 E721（NAME_MAX）合并为「musl 无传递包含：limits.h 常量」一条正式条目，match_keywords 覆盖 PATH_MAX / NAME_MAX / HOST_NAME_MAX。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: B1C7（feedback 骨架自动生成的是 2DC2，与 graph add 分配给草稿的 B1C7 不一致，已按草稿归属统一）
- **生成时间**: 2026-09-26 12:29:32
- **PR 编号**: —
- **Git Commit**: 本报告随本 PR 唯一 commit 入仓（骨架采集到的 901c0beae6 为 squash 前的中间提交）
