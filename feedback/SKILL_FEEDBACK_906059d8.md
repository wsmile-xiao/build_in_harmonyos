# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_906059d8.md`

---

## 背景

- **软件名称**: shush
- **版本**: 1.2.3
- **构建日期**: 2026-09-29
- **构建系统**: autotools（Autoconf 2.59 生成的 configure + 手写 Makefile.in，非 automake）
- **上游仓库**: https://web.taranis.org/shush/（官方发布页，发布包 `dist/shush-1.2.3.tgz`；无公开 VCS）
- **适配路径**: 路径 B（知识库扩展）——12 个补丁 + 知识草稿 `knowledge/drafts/E544-draft-31E6`
- **补丁数量**: 12
- **编译依赖**:
pcre2/10.45（静态 `libpcre2-8.a`）
- **最终状态**: 成功（conan-verify 与 W3 通过；本报告在建 PR 前完成并随 PR 提交）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 内置下载器对官方站挂起 300 s，改为预置 tarball + `EXPECTED_SHA256` |
| build | 编译构建 | 成功 | 构建系统: autotools；x86_64 交叉，`--host=aarch64-linux-ohos` |
| conan-verify | 配方验证 | PASS | G0-G3 通过；G4 仅告警（未找到包 ID）；L2/L4/L5 因无 cache 路径跳过 |
| finish | 归档收尾 | 完成 | W3 PASS（L0/L1/L1e/L5 pass，L2 skip，L4 warn）；finish 以 step5b/step8 返回 1（原因见下） |
| submit | PR提交+AI检视+CI | 旁路建 PR | 本地实跑 PF 闸后用 create-pr 建 PR；AI Review: 报告提交时尚未开始 |

### 失败与问题

1. `init-build` 下载挂起：`init_build.py` 的 `_download_one()` 用 urllib、单次 300 s 超时，
   对 web.taranis.org 无响应直到超时；同一 URL 用 curl 与 requests（Conan `get()` 同款）均 0.6 s 完成。
2. `conan-init` 按「库」模板生成配方（`package_type="library"`、`shared` 选项、`cpp_info.libs=["shush"]`），
   conandata 为非版本键且 sha256 为 `REPLACE_WITH_ACTUAL_SHA256`，test_package 为只打印字符串的空壳，
   版本级 `manifest.yaml` 残留 `{software}`/`{BUILD_SYSTEM}`——全部手工重写。
3. finish 每次都把手工填好的 `manifest.yaml` `patch_classification` 覆盖回 `type: auto / guard: 'pending'`，
   并在 `notes.md` 末尾追加「编译结束/最终状态」页脚，使已提交文件变脏；只能 `git checkout` 还原后再提交。
4. finish 步骤判定：首跑因 `reports/test-report.md` 缺失把 status 降为 built；`knowledge_gained` 条目
   需带 `ref:` 才算「已引用」（check_knowledge_gap.py）；`packaging/` 为已废弃交付形式但 step8 仍判未就绪，
   因此 finish 固定返回 1（W3 本身通过，`.ci-result.json` exit_code=0）。
5. 假告警：finalize-archive 报「补丁数不一致 manifest=12 vs disk=9」（只数 `000*.patch`，漏掉 0010-0012）；
   G0 clean-verify 在交叉构建机上用裸 `clang` 跑 configure 必报 `C compiler cannot create executables`；
   W3 L4「危险函数」命中的是 config.guess 补丁上下文行里上游原有的 `ld_supported_targets`（`gets\b` 匹配到 `targets`）；
   gen_summary 报 `'str' object has no attribute 'append'`（未写 SUMMARY.md）。
6. refresh-patch 把旧补丁备份到 `patches/.patch-backup-*`，W3 的 L4 扫描会连备份一起扫；W3 在仓库根留下未被
   忽略的 `.build-cache/`。均手工清理。

### 知识图谱使用情况

- **引用知识条目**: E007、E011、E064、E272、E453、草稿 E543-draft-419E（jday 同款 config.guess/sub）、
  E544-draft-7C1A（x86 qemu 静态重链验证法）、e665-hmdfs-maildir-portability、DRAFT-inputlirc-34（查重）
- **新增知识草稿**: `knowledge/drafts/E544-draft-31E6.{kv,md}`——构建期生成器 cat 构建机 `/usr/include`
  头文件，交叉/真机上静默生成空信号表（draft-review 结论 create，rebase 到最新 main 后重做，最高相似度 0.05/E049）
- **引擎命中情况**: 新模式均无有效命中（仅关键词误命中 E106/E064/E453）
- **测试统计**: 总计 9，通过 9，失败 0，跳过 0（同源 .o 静态重链副本 qemu 实跑）；交付动态产物在 x86 上 9 项 SKIP，由 CI 执行
- **未覆盖的错误模式**: ① `AC_PATH_PROG` 交叉构建时把构建机工具路径（`/usr/lib/sendmail`）烙进产物；
  ② 配置文件「属主必须等于 euid、不得组可写」的安全检查在 HMDFS 上拦掉核心功能（已有 e665 只覆盖 .netrc 类可选功能）

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: 报告须在建 PR 前入仓，提交时变更摘要尚未生成，不回填（避免建 PR 后再推 commit）
- **检视意见数量**: 提交时为 0（检视尚未开始）
- **检视意见处理**: 检视意见将在 PR 讨论串内逐条回复处理，不在本报告回填

### CI 结果

- **本地 CI 模拟 (W3)**: PASS（L0/L1/L1e/L5 pass，L2 skip，L4 warn 为补丁上下文假阳性）
- **远程 CI (PR 校验)**: 建 PR 后评论 /rebuild 触发，结果见 PR
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 2（两次 finish 内 G0 clean-verify 的非阻塞 HANDOFF，均为交叉构建机上的假失败）
- **重试次数**: finish 2 次（首次缺 test-report/.staging-verified 与知识引用）；init-build 1 次（下载挂起后改预置）
- **关键瓶颈**: 证明「消费者用例能区分适配点」——为此额外构建两个反向变体（上游式构建、`--without-pcre`）做对照
- **耗时较长的步骤**: 老 autotools 的 PCRE2 移植（为让生成文件补丁可复现，本地编译原版 Autoconf 2.59 重生成 configure）；两次 finish（各约 3 分钟）

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-29T09:13:55 | skeleton_created | result_partial |
| 2026-09-29T09:13:55 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. finish 不应改写已手工完成的归档文件：`scripts/ohc/refresh_patch.py` 生成补丁后「补丁分类标注已写入
   manifest.yaml」时，对已存在且 `guard != 'pending'` 的条目应保留原值；close-archive 的「编译结束」页脚
   已存在时不再追加。否则 AI 按要求补全的内容每次 finish 后都被还原，且已提交文件变脏。
2. finish 的 step8 仍把 `packaging/` 当作就绪项（`scripts/ohc/finish.py` step8_submit_readiness 中
   `packaging_dir` 判定），而 ARCHIVE-SPEC v2.0 已废弃 packaging——conanfile 配方包应跳过此项，否则 finish
   对所有 Conan 包都固定返回 1，退出码失去意义。
3. finish Step 0 在 `reports/test-report.md` 缺失时静默把 published 降为 built；该文件被 gitignore、
   只在本地存在，建议 conan-init 结束时就提示需要它，或由 conan-verify 自动生成基础版。

### 模板改进

1. conan-init 对「只安装可执行文件」的 autotools 项目仍套用库模板（`package_type="library"`、`shared`
   选项、`cpp_info.libs=[name]`）。可在 init-build 阶段识别 `Makefile.in` 的 install 目标只复制到 `$(bindir)`，
   直接选 application 形态，并提示生成软件级 `commands.json`。
2. 生成的 `conandata.yml` 为非版本键且 sha256 为 `REPLACE_WITH_ACTUAL_SHA256`，而 init-build 已校验过
   tarball（`EXPECTED_SHA256`）；建议直接写入实际 sha256，并采用仓库主流的版本键写法
   `sources: {"<ver>": {url, sha256}}`。
3. 版本级 `manifest.yaml` 模板残留 `software: "{software}"`、`build_system: "{BUILD_SYSTEM}"`；
   SKILL_FEEDBACK 骨架同样残留 `{BUILD_SYSTEM}`——占位符应在生成时渲染。

### 自动化补全

1. 本报告骨架的自动采集有 5 处错误，已按实修正：构建系统渲染成 `{BUILD_SYSTEM}`、上游仓库「未知」、
   补丁数量 0（生成时磁盘已有 10 个补丁）、适配路径判为「路径 A 无补丁」、测试统计 0/0。
   建议骨架生成与 finish 结束时各刷新一次这些字段（数据源：conandata.yml 的 patches、manifest 的 build_system、
   test_package/MANIFEST.yml 的计数）。
2. `scripts/ohc/init_build.py` `_download_one()`（约第 106-124 行）用 urllib 单次 300 s 超时且无回退；
   建议缩短连接超时并回退到 requests/curl。`_guess_tar_format()`（第 89-93 行）不认 `.tgz`，虽回落 tar.gz
   可用，建议显式支持。
3. `scripts/ohc/finalize_archive.py` 第 146、152 行用 `glob("000*.patch")` 计数，补丁 ≥10 个时必报不一致；
   改为 `glob("[0-9][0-9][0-9][0-9]-*.patch")`。
4. `ci/conan/build_and_test.sh` 第 1469 行 L4 扫描对整个补丁文件 `grep -rlE '(strcpy|sprintf|gets|strcat)\b'`：
   上下文行也会命中，且 `gets\b` 会匹配 `targets` 这类普通词（本包即因 config.guess 的 `ld_supported_targets`
   告警），还会扫到 `patches/.patch-backup-*`；建议只扫 `^+` 行、正则加前置 `\b` 并排除备份目录。
   refresh-patch 的备份目录（refresh_patch.py 约第 488-490 行）建议放到 patches/ 之外，W3 结束后清理
   仓库根的 `.build-cache/`。
5. finish Step 3 的 G0 clean-verify 在 x86_64 交叉构建机上用裸 `clang` 跑 configure，必然报
   `C compiler cannot create executables` 并打印 HANDOFF；建议复用 conan 工具链，或在构建机架构与目标不同时跳过。
6. W3 L2 冒烟只试 `--version/--help`；shush 用 `-V/-h`，可从 test_package 或 commands.json 读取版本参数。

### 知识图谱覆盖

1. 本 PR 新增草稿 `E544-draft-31E6`：构建期生成器读构建机 `/usr/include`（`cat … 2>/dev/null | awk`），
   交叉构建与鸿蒙真机上静默生成空表；修法为 `$(CC) $(CPPFLAGS) -E -dM` 取目标宏值 + 空表检查。
   与 DRAFT-inputlirc-34（make 前置条件断链、构建直接失败）区分明确。
2. 建议新增：`AC_PATH_PROG` 等运行期工具路径探测在交叉构建时烙入构建机路径——用 `ac_cv_path_*`
   缓存变量钉死为目标机结果（本包 C5 反向对照：未钉死时 `SENDMAIL` 为 `/usr/lib/sendmail`）。
3. 建议在 e665/E453 家族补充「配置文件属主/组写检查拦掉核心功能」的处理口径：可选功能按环境限制申报；
   核心路径则提供默认关闭的放宽开关、保留全局可写拒绝，并用「先 stat 实际权限位再断言、构造不出记 NOT RUN」
   的测试写法。
4. 草稿编号 E544 已被多份草稿复用（如 E544-draft-7C1A、E544-draft-CD04），按编号引用易混淆；建议
   `graph add --draft` 生成不带正式编号的 slug 文件名。

---

## 作者

- **姓名**: lkjing2021345
- **邮箱**: 1908499668@qq.com
- **Agent ID**: B5F4
- **生成时间**: 2026-09-29 09:13:55
- **PR 编号**: —
- **Git Commit**: 317e16ed5a
