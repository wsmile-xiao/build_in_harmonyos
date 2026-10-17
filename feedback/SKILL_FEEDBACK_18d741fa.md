# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_18d741fa.md`

---

## 背景

- **软件名称**: multitee
- **版本**: 3.0
- **构建日期**: 2026-09-23
- **构建系统**: makefile（上游无构建文件，补丁 0001 新增最小 Makefile；配方 AutotoolsToolchain + Autotools.make）
- **上游仓库**: https://salsa.debian.org/debian/multitee（tag upstream/3.0；作者原始发布 https://cr.yp.to/software/multitee-3.0.shar.gz，两者 20 个文件逐字节一致）
- **适配路径**: 路径 A（基础适配），另附 2 条知识草稿
- **补丁数量**: 5
- **编译依赖**:
无（仅 libc）
- **最终状态**: 成功（本地 W3 通过，status=built）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 未探测到构建文件，BUILD_SYSTEM 被默认成 autotools |
| build | 编译构建 | 成功 | 构建系统: makefile（补丁新增） |
| conan-verify | 配方验证 | PASS | G0-G3 通过；G4/L2/L4/L5 工具记 PASS/跳过，但因取不到 package id 实际未执行（见自动化补全 2） |
| finish | 归档收尾 | 完成 | W3 通过（L0/L1/L1e/L4/L5/JC/KC pass，L2 skip）；step5b/step8 为存量问题误报 |
| submit | PR提交+AI检视+CI | 本报告在建 PR 前定稿 | AI 检视与 CI 在 PR 创建后产生，按 RV-27 在 PR 讨论串内闭环 |

### 失败与问题

- **1 上游没有 Makefile 或任何构建文件**：根因=1991 年 shar 发布只含源码和手册；解决方案=补丁 0001 新增最小 Makefile，规则只引用 CC/CPPFLAGS/CFLAGS/LDFLAGS/LDLIBS
- **2 `struct sigvec` 不完整类型 + sigvec/sigblock/sigsetmask/sigmask 隐式声明**：根因=4.2BSD 信号接口未进入 POSIX，musl 不提供；解决方案=补丁 0004/0005 改写为 sigaction/sigprocmask/sigset_t（草稿 E634）
- **3 ralloc.c `incompatible redeclaration of library function 'malloc'`**：根因=前 ANSI `extern char *malloc();` 与 libc 原型冲突；解决方案=补丁 0003 改 include 标准头
- **4 multitee.c read/write/exit/perror 隐式声明**：根因=未 include 标准头，LP64 下 ssize_t 返回值按 int 处理；解决方案=补丁 0002
- **5 x86_64 runner 执行产物报 `aarch64-binfmt-P: Could not open '/lib/ld-musl-aarch64.so.1'`**：根因=宿主无 OHOS musl loader；解决方案=同源 .o 静态重链 + qemu 跑功能用例，test_package 在该宿主显式 SKIPPED（草稿 E635）

### 知识图谱使用情况

- **引用知识条目**: E074（make -j1，HMDFS jobserver）；engine 对 `struct sigvec` 报错命中 E102（musl 缺 mmsg API）属误命中
- **新增知识草稿**: 2 条（E634-draft-62B2、E635-draft-2704；draft-review 均判 create，最高相似度 0.25 / 0.08）
- **引擎命中情况**: 本次 2 类新错误均无正确命中
- **测试统计**: 上游 0（R51 清点无测试）；test_package 制品检查 4/4；功能用例 11/11（同源 .o 静态重链 + qemu-aarch64）；x86_64 上 conan create 的功能层为 SKIPPED（非通过）
- **未覆盖的错误模式**: 4.2BSD 信号接口缺失（→E634）；x86 runner 缺 OHOS loader 时的功能验证路径（→E635）；上游以 shar 形式发布时的 R39 来源处置（尚无条目，见知识图谱覆盖 3）

### AI 检视结果

- **检视阶段到达**: 未开始（本报告须在建 PR 前提交）
- **变更摘要评估**: N/A（PR 创建后产生）
- **检视意见数量**: N/A（PR 创建后产生）
- **检视意见处理**: N/A，PR 创建后按 RV-27 逐条 accept/reject 并在讨论串回复

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 未知（PR 创建后评论 /rebuild 触发）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 2 次，均非阻塞：finish G0 clean-verify 的 configure exit 127，以及 finish 收尾的 KNOWLEDGE CONSOLIDATION；阻塞型 HANDOFF 0 次
- **重试次数**: 0（conan-verify、finish 均一次通过）
- **关键瓶颈**: ① conan-init 生成的是 library/autotools 模板，conanfile、conandata、test_package 需整体重写；② x86_64 runner 执行不了 OHOS 动态产物，功能验证需要自建静态重链路径；③ finish 第 1 步重写 manifest 补丁分类并留下 .patch-backup，需要手工恢复与清理
- **耗时较长的步骤**: 源码来源核验（shar 解析比对、GitLab 归档 sha256 稳定性复核）与 test_package 功能用例设计；conan-verify / W3 各约 1–2 分钟
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-23T07:36:29 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **finish Step 1 在补丁未变时仍整体替换**。`refresh-patch --auto` 每次都把旧补丁移进 `.patch-backup-<ts>/`（`scripts/ohc/refresh_patch.py:490`），
   并用 `re.sub(r'\npatch_classification:.*', '', …, re.DOTALL)`（`refresh_patch.py:547`）重写 manifest：
   已补好的 type/guard 被重置为 `auto/pending`，该段之后的 manifest 内容也被截掉。本次 finish 后只能手工
   `git checkout manifest.yaml` 并删除备份目录。建议：staging 补丁与现有补丁逐文件 sha256 相同时跳过替换；分类段按 file 合并，保留已填值。
2. **G0 clean-verify 固定执行 `./configure`**（`scripts/ohc/clean_verify.py:69`）。纯 Makefile 或无构建文件的项目必然 exit 127，
   还会弹出 G0 HANDOFF，虽不阻塞但有误导性。建议先读 manifest 的 `build_system`：makefile/custom 跳过 configure，改为复用 conan create 的结果。
3. **W5（finish Step 7）把主库存量问题算进本次失败步骤**。E219/E253/E305 的 root_cause 为空，却导致 finish 报 `失败步骤: step5b`，而这与本 PR 无关。
   建议 W5 只对本 PR 触及的 knowledge 文件判失败，存量问题降为提示。
4. **PF9 与 R38/PF8 互斥仍存在**。`scripts/ohc/preflight.py:570` 的 `len(f.split("/")) < 5` 会拦截软件级 `archives/<l>/<pkg>/commands.json`，
   新增 CLI 包必然命中，只能 `--no-preflight`。建议 PF9 白名单放行软件级 `commands.json` / `README.md` / `manifest.yaml`。

### 模板改进

1. **conan-init 给无构建文件的 CLI 项目套了 library/autotools 模板**。`scripts/ohc/init_build.py:86` 在探测不到构建文件时默认返回 `"autotools"`，
   conan-init 随即生成 `package_type="library"`、`--enable-static/--disable-shared`、`cpp_info.libs=["multitee"]`，以及 CMakeLists.txt + test.c 的库消费者 test_package，全部要重写。
   建议：探测不到构建文件时记为 `custom`；源码里存在 `main(` 且没有库目标时，选 application 配方与 `templates/test_package-executable`。
2. **conandata.yml 留下 `sha256: "REPLACE_WITH_ACTUAL_SHA256"`**（`scripts/ohc/conan_recipe.py:301`）。init-build 其实已把实测哈希写进
   `.orig/.tarball-sha256`（`scripts/ohc/init_build.py:305`），应直接读取回填。
3. **notes.md 问题表与 feedback 解析错位一列**。模板列序是 `# | 问题 | 根因 | 解决方案`，而 `scripts/ohc/feedback.py:417` 按 cols[1..3] 取值，
   结果本报告"失败与问题"被自动填成"根因=问题、解决方案=根因"（已手工修正）。应改为 cols[2..4]，或统一模板列序。
4. **`templates/test_package-executable/conanfile.py.tmpl` 只有 `bash test.sh`**，没有处理 x86_64 runner 执行不了 OHOS 动态产物的情况。
   建议模板内置骨架：任何宿主都做制品检查（ELF/EM_AARCH64/PT_INTERP）；外架构宿主凭显式 loader 标记报 SKIPPED；aarch64 上强制执行；二进制缺失即失败。
   本 PR 的 `test_package/test_multitee.py` 可作参考。

### 自动化补全

1. **feedback 自动采集失准**（本报告已手工修正）。上游仓库取成了源码包 URL，而不是仓库地址；测试统计取到 0/0，没有解析 `reports/test-report.md`；
   conan-verify 一栏仍是待填占位符，而 `.conan-verified` 已经存在；引用知识条目显示"无"，实际引用了 E074。建议从 `.conan-verified`、`test-report.md` 和 conandata 的 homepage/url 取值。
2. **conan-verify 的 G4/L2/L4/L5 实际没有执行却记 PASS**。用 `multitee/3.0@ohpcd/stable` 查询 package id 失败（`scripts/ohc/conan_verify.py:741` 报"无法找到程序包 ID"，
   800/851/942 报"无 cache 路径"），四项门禁只写了跳过，却记为 PASS。建议查询时带上 user/channel，或像 `ci/conan/build_and_test.sh` 那样从 conan create 日志的 `Package folder` 行解析；
   取不到时应记 SKIP，不能记 PASS。
3. **建议新增 `ohc-run.py relink-static <软件> <版本>`**，把 E635 的方案工具化：从 conan 构建目录收集 `.o`，用 OHOS clang `-static` 链接 NDK libc.a，
   在 qemu-aarch64 下执行 test_package 的功能用例，并输出可直接写进 notes/test-report 的段落，同时附上"不等于交付产物实跑"的声明。
4. **finish Step 8 gen_summary 必然失败**。`archives/q/qpdf/12.3.2*/manifest.yaml` 里列表与标量混写，`scripts/ohc/summary.py:87` 的 `_parse_yaml_simple`
   因此抛出 `'str' object has no attribute 'append'`，任何包的 finish 都会报 step8 失败。建议解析器遇到类型冲突时容错并跳过该键。
5. **finalize-archive 仍检查 release/debug tar.gz**（`scripts/ohc/finalize_archive.py:119-122`）。packaging/ 已列入 ARCHIVE-SPEC §2.3 废弃项，
   这条告警应删除，finish 第 10 步的"packaging/ 未就绪"同理。软件级 README.md / manifest.yaml 是 ARCHIVE-SPEC §2.1 的必须项，这项检查本身是对的，
   但 conan-init 不生成这两个文件，建议由它按 `templates/manifest-software.yaml` 生成骨架。

### 知识图谱覆盖

1. **新增草稿 E634**：4.2BSD sigvec/sigblock/sigsetmask/sigmask 缺失，改写为 POSIX 调用。草稿带 `prescan_pattern`，promote 后可自动预扫老 BSD 代码。
   目前 engine 会把 `struct sigvec` 报错误命中 E102（musl 缺 mmsg API），promote 后可以纠正。
2. **新增草稿 E635**：x86 runner 缺 ld-musl loader 时，用同源 .o 静态重链 + qemu 做验证，并规范 test_package 的显式 SKIPPED。
   它与 `DRAFT-yosys-0.66-ohos-aarch64-local-run-missing-fd-chk`（动态 loader + shim 路径）互补，建议 promote 时合并为同一条目的两个方案。
3. **建议新增一条**："上游只以 shar/非归档形式发布时的 R39 来源处置"。做法是使用权威托管的等价 tag 归档，再把 shar 解析（不执行）后逐字节比对，
   并对按需生成的归档包复核 sha256 稳定性。本 PR 的 notes.md 有完整证据链，知识库目前没有此类条目。

---

## 作者

- **姓名**: lkjing2021345
- **邮箱**: 1908499668@qq.com
- **Agent ID**: FC32
- **生成时间**: 2026-09-23 08:26:11
- **PR 编号**: —
- **Git Commit**: 以 PR 分支 feat/multitee-3.0 的 HEAD 为准（报告随该提交入仓，无法内含自身哈希；基线 origin/main 7f702efc1d）
