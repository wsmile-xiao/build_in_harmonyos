# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_01f55f48.md`

---

## 背景

- **软件名称**: macutils
- **版本**: 2.0b3
- **构建日期**: 2026-09-26
- **构建系统**: makefile
- **上游仓库**: https://github.com/dgilman/macutils （自动采集为「未知」，人工补全；钉住提交 920f51f）
- **适配路径**: 路径 B（适配 + 知识草稿 E544-draft-6EE2；自动采集误判为路径 A）
- **补丁数量**: 5
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
| conan-verify | 配方验证 | 通过（第 3 次） | 第 1 次 conf 名写错（tools.build:ldflags），第 2 次动态链接 undefined symbol: rindex，第 3 次 G1-G4/L2/L4/L5 全过 |
| finish | 归档收尾 | 完成 | W3 通过；G0 clean-verify 对无 configure 的 makefile 项目跑 configure 报 exit 127（非阻塞） |
| submit | PR提交+AI检视+CI | 本报告随 PR 首次提交，届时尚未开始 | fork 旁路手动建 PR；AI Review / CI 结果见 PR |

### 失败与问题

- **1**: 根因=`makecrc.c:40: error: return type defaults to 'int'`, 解决方案=1992 年 K&R 代码（隐式 int、旧式定义），新编译器默认 C99+ 视为错误
- **2**: 根因=`crc/makefile` 写死 `cc -O -o makecrc` 与 `ar r`, 解决方案=构建期生成器 makecrc 要在构建机上运行，生成 6 个 CRC 表 .c；设备无 `cc`/`ar`
- **3**: 根因=`transname.c:93: use of undeclared identifier 'DIRSIZ'`, 解决方案=musl 既无 MAXNAMLEN 也无 DIRSIZ，补丁 0005 以 `#elif defined(DIRSIZ)` / `NAME_MAX` 兜底（自动采集漏掉了此行，且上面各行把「问题/根因/方案」三列错位成「根因/方案」两列）
- **4**: 根因=`binhex.c:36: error: incompatible integer to pointer conversion ... get_rdfileopt()`（frommac 同类）, 解决方案=缺原型的 `char *get_rdfileopt()`/`get_wrfileopt()` 被隐式声明为返回 int；LP64 上指针会被截断，clang 15 直接报 `-Wint-conversion` 错
- **5**: 根因=手工 `-static` 构建 + qemu 测试全绿，`conan create` 却报 `ld.lld: error: undefined symbol: rindex`, 解决方案=上游 CF 带 `-DBSD`，`hexbin/globals.h` 在 BSD 分支用 `rindex`；OHOS `libc.so` 不导出 `rindex`（`libc.a` 有，`<strings.h>` 也不声明），静态探针掩盖了问题

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 1 条（`knowledge/drafts/E544-draft-6EE2.kv/.md`；自动采集把 manifest 的 3 条 knowledge_gained 当成了草稿数）
- **引擎命中情况**: 草稿目录 2095 条；本次两次 G2 失败引擎各命中一条无关条目（conf 名错误 → E538 harfbuzz 发布二进制；rindex → E540 runner PATH），未命中真正根因
- **测试统计**: 上游 N=0 / N′=0（无测试）；test_package 消费者用例 6 个，同源 .o 静态重链经 qemu-aarch64 实跑 6/6 通过（自动采集为 0）
- **未覆盖的错误模式**: OHOS NDK `libc.a` 比 `libc.so` 多导出 380 个非下划线全局符号（rindex/getw/cuserid/ecvt/fcvt/gcvt/getpass/lchmod/stime/setkey/encrypt 等），`-static` 探针能链过而交付的动态构建 `undefined symbol`——已有 rindex 草稿只记单点替换，未覆盖「静态探针掩盖」这一验证陷阱，已沉淀为 E544-draft-6EE2

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: 本报告随 PR 首次提交入仓，提交时 AI 检视尚未开始，无摘要可评估
- **检视意见数量**: 0（提交时尚未产生）
- **检视意见处理**: 不适用；后续意见在 PR 讨论串内逐条处理

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 未知
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 1（finish 结尾的 KNOWLEDGE CONSOLIDATION 提示，非阻塞）
- **重试次数**: 源码下载 3 次（github.com 跳转层 TLS/超时，改 codeload 直链成功）；conan-verify 3 次
- **关键瓶颈**: 本机为 x86_64 runner，OHOS 动态产物无法本地运行，功能验证需另做「同源 .o 静态重链 + qemu」；而静态链接又掩盖了 libc.so 缺 rindex 的问题，导致第一次 conan create 才暴露
- **耗时较长的步骤**: 消费者用例设计（为 macunpack 合成 PackIt 归档、独立 BinHex 4.0 解码器）与 x86/aarch64 输出逐字节比对
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-26T22:57:55 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **finish 的 refresh-patch 覆盖人工补丁分类**：`scripts/ohc/refresh_patch.py:541-547` 每次用正则删掉整段
   `patch_classification:` 再写回 `type: auto / platform_only: True / guard: 'pending'`，把人工填好的
   `portability / False / 特性检测` 冲掉（本次只能 `git checkout` 还原）。建议：补丁内容哈希未变时保留已有分类，
   只对新增补丁追加 pending 项。
2. **G0 clean-verify 不识别无 configure 的项目**：`scripts/ohc/clean_verify.py:173-181` 对手写 makefile 项目也执行
   `configure`，报 exit 127 并打印 `G0 HANDOFF RESULT: FAIL`，虽非阻塞但极易误导。建议按 `build_system`
   （makefile/none）跳过或改为 `make -n` 探测。
3. **x86 runner 的本地运行证据应纳入流程**：本机 `test()` 只能 skip，rule12 所需的「同源 .o 静态重链 + qemu」完全靠人工。
   建议 finish/W3 在构建机非 AArch64 时提供可选步骤：复制 conan 构建目录、删除 bin 产物、追加 `-static` 仅重链、
   再用同一 `test_package` 可执行（亦静态重链）在 qemu 下跑，并把输出/退出码写进 reports/。
   同时须**先**跑动态 conan create 再做静态重链（见 E544-draft-6EE2：静态会掩盖 libc.so 缺符号）。
4. **R46 草稿被他任务终态误伤**：`scripts/ohc/result_report.py:788` 在默认兜底输出位置发现他任务残留的
   `draft:false` 终态时，本任务所有里程碑草稿（lang_checked/recipe_generated/...）一律跳过。建议比较 software/version，
   不同任务的残留应覆盖或另存，而不是静默跳过。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. **manifest 模板占位符未渲染**：`templates/manifest-version.yaml:13` 的 `software: "{software}"` 与第 21 行
   `build_system: "{BUILD_SYSTEM}"` 生成后原样留在归档里，没有门禁校验。建议 init-archive 渲染这两个字段，
   并在 finish 的 finalize 阶段对 `\{[A-Za-z_]+\}` 做占位符检查。
2. **conandata 骨架格式与仓库主流不一致**：`scripts/ohc/conan_recipe.py:301` 生成非版本键的 `sources: {url, sha256}`，
   且 sha256 写 `REPLACE_WITH_ACTUAL_SHA256`；但 init-build 已把实际 sha 写入 `.orig/.tarball-sha256`
   （`scripts/ohc/init_build.py:305`）。建议直接读取该文件，并按 `sources: {"<ver>": {...}}` 版本键输出。
3. **手写 makefile 项目缺模板**：conan-init 在 BUILD_SYSTEM 误判为 autotools 时套用 autotools 模板（configure/--enable-static
   与 `package_type=library`、`cpp_info.libs=[name]`），对纯 CLI 包全部要重写。建议增加 `conanfile-makefile.py.tmpl`
   （in-source layout、`make CC=... AR=...`、`package()` 手工复制 bin、`package_type=application`）。
4. **PR 正文「鸿蒙特有测试」写死 0**：`scripts/ohc/submission.py:603` `| 鸿蒙特有测试 | 0 | - | 新增 |`。
   建议从 `test_package/MANIFEST.yml` 的 `harmony_specific_tests` 条目数或消费者用例数回填，缺失时写正文完整性闸能识别的待填占位符，让它拦住。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **构建系统探测大小写敏感**：`scripts/ohc/init_build.py:203` 的 `_BUILD_MARKERS` 与第 296/315 行只认 `Makefile`，
   老项目的小写 `makefile` 被判为「未找到构建文件」，BUILD_SYSTEM 回落为 autotools（lang-preflight 也报 build_system=none）。
   建议加入 `makefile`/`GNUmakefile` 并映射为 makefile。
2. **feedback 自动采集多处失真**（本报告已人工修正）：`scripts/ohc/feedback.py:417` 解析 notes 表格时把
   「问题/根因/方案」三列错位为「根因/方案」且漏掉第 3 行；第 388 行把 manifest `knowledge_gained` 条数当作新增草稿数；
   第 525 行上游仓库取不到 conandata 的 GitHub URL 显示「未知」；测试统计未读取 MANIFEST.yml / test-report 得到 0；
   适配路径未检测 `knowledge/drafts/` 中本分支新增草稿而误判为路径 A。建议分别改为按表头定位列、
   统计 `git diff origin/main --name-only -- knowledge/drafts/*.kv`、从 conandata url 推导仓库、读 MANIFEST.yml。
3. **summary 步骤崩溃**：finish Step 8 `gen_summary 失败: 'str' object has no attribute 'append'`（`scripts/ohc/summary.py`），
   可稳定复现于本包，建议加单测。
4. **G2 失败的知识引擎误命中**：Python 侧 `ConanException: [conf] 'tools.build:ldflags' does not exist` 命中 E538（harfbuzz
   发布二进制，评分 3357），`undefined symbol: rindex` 命中 E540（runner PATH）。建议对 ConanException 配置名错误先做
   本地规则分类（提示正确 conf 名 `tools.build:exelinkflags`），并提高 `undefined symbol` 类签名的精确匹配权重。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. **新增 E544-draft-6EE2**（本 PR 携带）：OHOS NDK `libc.a` 与 `libc.so` 导出表差集 380 个（含 rindex 等 BSD/SVID 遗留接口），
   `-static` 探针/qemu 验证会掩盖交付动态构建的 `undefined symbol`；处置为优先走上游 POSIX 分支（本例去掉 `-DBSD`，零补丁）。
   draft-review 结论 `create`（最相似 E123 0.25）。建议主编 promote，并与 `DRAFT-cconv-0.6.3-rindex-strrchr`、
   `DRAFT-irqbalance-1.9.4-rindex-strrchr`、`DRAFT-rdma-core-61.0-rindex-strrchr`、`DRAFT-motif-2.3.8-musl-no-rindex-xpm-guard`
   四份单点草稿合并为一条（它们只记录替换，不含导出表差异与验证顺序）。
2. **构建期生成器用目标编译器 `-static`**：本包 `crc/makecrc` 以 `CC_FOR_BUILD=<target clang> -static` 构建，
   AArch64 CI 原生可跑、x86 runner 经 qemu binfmt 也可跑，无需宿主 cc。现有 `DRAFT-7324-bglibs-djb-two-stage-cross-build`
   走的是「宿主编译器两阶段」路线，在设备原生 CI（无 gcc/cc）不可用。建议在该草稿补充此单阶段替代方案，而不是另开条目。
3. **K&R 代码在 LP64 上的隐式声明截断**：`-std=gnu89` 可放行隐式 int，但返回指针的函数缺原型会截断高 32 位，
   clang 15 对传参处报 `-Wint-conversion` 错误。建议在 pre-scan-rules 增加规则：源码含 `extern char \*[a-z_]+\(\);`
   风格声明且构建使用 `-std=gnu89` 时提示逐个核对 `-Wimplicit-function-declaration` 列表。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: 7BD0
- **生成时间**: 2026-09-26 23:23:01
- **PR 编号**: —
- **Git Commit**: e407bc2b40
