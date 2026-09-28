# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_7b5a28b7.md`

---

## 背景

- **软件名称**: ubench
- **版本**: 0.32
- **构建日期**: 2026-09-25
- **构建系统**: makefile
- **上游仓库**: https://www.ibiblio.org/pub/Linux/system/benchmark/ubench-0.32.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 3
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
| conan-verify | 配方验证 | 通过（第 2 次） | 第 1 次 G2 在 source() 报 sha256 不符（ibiblio Content-Encoding: x-gzip），加 urllib 回退后 G1/G2/G3 PASS，test_package 经 qemu-aarch64 7/7 |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | 手动建 PR | 本报告在建 PR 前闭环；AI 检视与 CI 结果待 PR 创建后产生，本报告不含 |

### 失败与问题

- **1**: 问题=`cpubench.c:93` / `membench.c:83` 报 `use of undeclared identifier 'CLK_TCK'`；根因=POSIX.1-2001 已删除 `CLK_TCK`，OHOS sysroot 只有 `_SC_CLK_TCK`；解决=补丁改为 `sysconf(_SC_CLK_TCK)`（新草稿 E6418）
- **2**: 问题=`use of undeclared identifier 'sys_errlist'` ×5；根因=musl 从未导出 `sys_errlist`；解决=补丁改为 `strerror(errno)`
- **3**: 问题=cpubench.c 隐式声明 `abs`/`exit`；根因=K&R 写法，缺少 `<stdlib.h>`；解决=补丁补 include
- **4**: 问题=上游 configure/Makefile 不能用于交叉构建；根因=按宿主 uname 写 gcc/x86 标志，并调用宿主 strip；解决=配方直接编译上游 ubench 目标的 4 个对象
- **5**: 问题=conan-verify G2 报 `sha256 hash failed … Computed hash: c21b18a5…`；根因=ibiblio 对 .tar.gz 回 `Content-Encoding: x-gzip`，Conan 解掉一层 gzip 后算的是裸 tar 的哈希；解决=get() 失败后回退 urllib 下载，仍用 check_sha256 校验文件面哈希

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 3 条
- **引擎命中情况**: 草稿目录 1703 条
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0
- **未覆盖的错误模式**: `use of undeclared identifier 'CLK_TCK'` 全库零覆盖（graph/drafts 均无），已新增草稿 E6418；`sys_errlist` 与 x-gzip 双面 sha256 仅有草稿、无正式条目，engine 对这两条报错分别误命中 E493/E213（引擎不检索 drafts）
- **自动采集修正**: 上方「新增知识草稿: 3 条」实为 manifest `knowledge_gained` 的行数，本次真正新增的草稿只有 1 条（E6418-draft-9D56）；「引用知识条目: 无」实际引用了 2 份既有草稿（tevent sys_errlist、DRAFT-E690 x-gzip）；「测试统计 0/0」实际是 test_package 7/7 通过（上游测试 0）；「失败与问题」把 notes 表格的「问题」列当成了根因、把「根因」列当成了解决方案，并漏掉了第 3 行（K&R 隐式声明）

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: 不适用。报告在建 PR 前完成并随 PR 提交，检视还没开始
- **检视意见数量**: 不适用（同上）
- **检视意见处理**: 不适用（同上）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 未知
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 1（finish 内 G0 clean-verify 的非阻塞 HANDOFF：它跑了上游 gcc/-m486 Makefile，配方本身并不使用该 Makefile）
- **重试次数**: conan-verify 2 次（sha256 双面问题 1 次）；finish 1 次通过 W3
- **关键瓶颈**: conan-verify G2 的 sha256 失败只显示 Provided/Computed 两个哈希，引擎命中的是 E540（shadow-ci PATH），与根因无关；要手工 curl 对比 + `gunzip -c | sha256sum` 才能确认是 Content-Encoding 解码
- **耗时较长的步骤**: 完整基准手工实跑（`ubench -c` 经 qemu 3m03s）；finish 中 W3 conan create 与 G0 clean-verify
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-25T23:56:06 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **finish 会覆盖人工填写的补丁分类**：`scripts/ohc/refresh_patch.py:532` 固定写 `platform_only: True` / `guard: 'pending'`，`:547` 用正则把整个 `patch_classification:` 段删掉重写。finish Step 1 的 refresh-patch 因此把人工填好的 `type: portability / platform_only: False` 覆盖回占位值，只能 `git checkout` 恢复。建议：已有条目且不是 `pending` 时保留原值，只新增或删除条目。
2. **G0 clean-verify 不认配方的构建方式**：finish Step 3 按 `BUILD_SYSTEM` 跑上游 configure+make。本包配方有意绕开上游 Makefile（宿主 uname 生成 gcc `-m486`，宿主 strip），G0 必然失败并弹 HANDOFF，这是噪声。建议：G0 改为复用 conanfile 的 `build()`（例如 `conan build`），或者在 conan-verify G2 已通过时跳过。
3. **step5b 知识缺口的判定口径没有文档**：`scripts/ohc/check_knowledge_gap.py:65` 要求 `knowledge_gained` 的每一行都带字面量 `ref:`/`knowledge_ref`，否则计入 unreferenced 并把 finish 标为失败。SKILL.md 与 manifest 模板里都没写这个格式。建议：在 `templates/` 的 manifest 模板注释里给出 `- "... (ref: knowledge/drafts/<id>.kv)"` 示例。
4. **gen_summary 崩溃**：finish Step 8 报 `gen_summary 失败: 'str' object has no attribute 'append'`（`scripts/ohc/finish.py:340` → `summary.generate_summary`），和本包内容无关，应当是存量数据类型不一致。建议给出失败的条目名，便于定位。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. **conandata.yml 生成器写的是扁平 `sources:`**：`scripts/ohc/conan_recipe.py:299-301` 输出 `sources: {url, sha256}`，而仓库配方的主流是版本键 `sources: {"<ver>": {...}}` + `get(**self.conan_data["sources"][self.version])`。另外它已经下载过 tarball，却仍写 `REPLACE_WITH_ACTUAL_SHA256`。建议：改为版本键格式，并直接填入 init-build 算出的 sha256。
2. **CLI 工具拿到的是库模板**：Makefile 类 CLI 包的 conan-init 仍生成 `package_type = "library"`、`options shared`、`cpp_info.libs = ["ubench"]` 以及 CMake + test.c 的 test_package，全部都要重写。建议：init-build 检测到上游 install 目标只装可执行文件（或 Makefile 里没有 `.a/.so` 目标）时，改用 application 模板（bindirs=["bin"]、libdirs=[]、test_package 调用二进制）。
3. **版本级 manifest.yaml 占位符没有渲染**：`software: "{software}"`、`build_system: "{BUILD_SYSTEM}"`、`sha256: ""` 原样留在文件里，也没有门禁检查。建议在 conan-init 时渲染，或加入 L0 占位符检查。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **feedback 自动采集的纠错**（本报告已人工修正，见「知识图谱使用情况」）：`scripts/ohc/feedback.py:417` 按固定列号 `cols[1..3]` 解析 notes 表格，把「问题/根因/解决方案」错位成「根因=问题、解决方案=根因」，还漏行；`:388` 把 `knowledge_gained` 行数当作「新增知识草稿」数；测试统计没有读 `test_package/MANIFEST.yml` 和 `reports/test-report.md`。建议：按表头名定位列；草稿数改用 `git diff --name-only origin/main -- knowledge/drafts/*.kv`；测试统计解析 test-report 表格。
2. **sha256 失败时自动探测双面哈希**：conan-verify G2 命中 `sha256 hash failed` 时，可以自动执行一次 `curl -sI -H 'Accept-Encoding: gzip'`。如果响应带 `Content-Encoding: (x-)gzip`，并且 Computed 值等于 `gunzip -c <file> | sha256sum`，就直接在 HANDOFF 里给出 urllib 回退处方（已合并先例 simstring/1.0），不必人工排查。
3. **`graph add --draft` 不带 id 时给出的是通用号**：`scripts/ohc/graph.py:281` 建议的 `E429` 已被几十份 `E429-draft-*` 共用，查重和人工引用时容易混淆。建议：遇到已被 drafts 占用的号，顺延到下一个空号。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. **新增 E6418**（`knowledge/drafts/E6418-draft-9D56.kv/.md`）：`use of undeclared identifier 'CLK_TCK'` → `sysconf(_SC_CLK_TCK)`。已实测 OHOS sysroot 与现代 glibc 均不定义该宏，并记录了禁止用 `CLOCKS_PER_SEC` 顶替的原因（单位相差 10^4）。draft-review 最相近的是 E500（MAX_INPUT，相似度 0.35），根因不同，建议作为新条目 promote。
2. **建议 promote sys_errlist**：`tevent-0.17.1-musl-strerror-sys-errlist-remap` 与 `DRAFT-irpas-0.10-musl-errlist-registry-replace` 两份草稿讲的是同一件事，但 engine 不检索 drafts，本次 `use of undeclared identifier 'sys_errlist'` 误命中 E213（l64a）。建议合并后 promote 为一条正式条目，处方写 `strerror(errno)`。
3. **建议合并 x-gzip 双面 sha256 草稿**：`DRAFT-E690-content-encoding-x-gzip-conan-decode-two-faced-sha256` 与 `DRAFT-conan-downloader-xgzip-content-encoding` 描述的是同一根因的两种症状（sha256 不符 / Transfer interrupted）。本次 ibiblio.org 是新增的实测域名，G2 的 engine 却命中了 E540，说明该根因没有正式条目。建议合并后 promote，并在 match_keywords 里加入 `Computed hash`、`Content-Encoding`、`x-gzip`。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: 5910
- **生成时间**: 2026-09-26 00:13:22
- **PR 编号**: —
- **Git Commit**: a25689eafa
