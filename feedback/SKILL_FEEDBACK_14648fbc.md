# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_14648fbc.md`

---

## 背景

- **软件名称**: tzdiff
- **版本**: 1.2.1
- **构建日期**: 2026-09-25
- **构建系统**: headeronly（无构建：纯 POSIX sh 脚本 + 随包 zoneinfo 数据）
- **上游仓库**: https://github.com/belgianbeer/tzdiff（源码包 archive/refs/tags/1.2.1.tar.gz；自动采集把 tarball URL 当成了仓库地址，已人工修正）
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 1
- **编译依赖**:
- tzdata/2026.3
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: headeronly |
| conan-verify | 配方验证 | 通过 | G1-G4 PASS；G2 内 test_package 8/8 |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | 待定 | fork 旁路手动建 PR；本报告在建 PR 前闭环，AI 检视/远程 CI 结果尚未产生 |

### 失败与问题

- **1**: 根因=上游 `cd /usr/share/zoneinfo || exit`，鸿蒙 PC 无 Olson 目录树（musl 只读打包的 /etc/zoneinfo/tzdata）, 解决方案=补丁 `cd "${TZDIR:-/usr/share/zoneinfo}"` + 随包 tzdata/2026.3 zoneinfo + wrapper 缺省 TZDIR（自动采集在 notes 表格的 `\|` 转义处截断了本行，已人工补全）
- **2**: 根因=按名字 `TZ=Asia/Tokyo` 在 OHOS musl 上不可用, 解决方案=OHOS musl 按名字只查上面的打包库，不看 TZDIR
- **3**: 根因=`date --date=@N` 在鸿蒙上报 `Unknown option 'date=@0'`, 解决方案=鸿蒙用户态 `date` 是 toybox；toybox 0.8.14 `date --version` 返回 0（所以上游判定为 GNU 分支），但没有 `--date` 长选项
- **4**: 根因=`-t 2024-07-01T09:00Z` 在 toybox 下 `bad date`, 解决方案=toybox `date -d` 不接受 ISO `T` 分隔，接受空格

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 1 条（E6402-draft-6E9A，.kv + .md 各一个文件；自动采集按文件数计成 2 条）
- **引擎命中情况**: 草稿目录 1703 条
- **测试统计**: 上游 0（无测试套件）；test_package 8 个用例（含鸿蒙特有 1），通过 8，失败 0，跳过 0（自动采集取到 0，已人工修正）
- **未覆盖的错误模式**: toybox `date` 无 `--date` 长选项且 `-d` 拒收 ISO `T`；OHOS musl 对 `TZ=名字` 只查打包 tzdata、不认 TZDIR，但接受绝对路径 TZif。已有 E315（R 语言时区）/E010/E402（toybox sed/gzip）均未覆盖 → 新增草稿 E6402

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: 建 PR 前闭环，尚无变更摘要
- **检视意见数量**: 0（尚未开始检视）
- **检视意见处理**: 无（后续复查按 PR 提交纪律处理）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 未知
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 1（finish 的 KNOWLEDGE CONSOLIDATION 块，EXIT_CODE 0，非阻塞）；另有 G0 clean-verify HANDOFF（对无构建包误跑 configure，非阻塞）
- **重试次数**: 0（conan-verify、W3 均一次通过）
- **关键瓶颈**: 鸿蒙运行期行为无真机可测——用 x86_64 toybox 0.8.14 模拟用户态、`unshare -m` 遮空 /usr/share/zoneinfo、NDK clang 静态探针 + qemu-aarch64 验证 musl 时区解析；以及清理 finish 回写的镜像 URL/补丁分类
- **耗时较长的步骤**: 平台行为取证（toybox date 选项、musl 时区搜索路径）与测试设计；构建本身秒级
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-25T22:28:11 | lang_checked | detected=other 与任务 other 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **finish 回写已提交的 CI 输入文件**：本次 `finish` 结束后 `conandata.yml` 的 `url` 被改成
   `[gh-proxy.com/..., github.com/...]` 列表——正是 `scripts/ohc/preflight.py:357` PF7 黑名单域名，
   不人工 `git checkout` 就会带进 PR 被拦。镜像改写来自 `ci/conan/build_and_test.sh:1048-1052`
   预下载逻辑，`:1188` 的 `trap _restore_conandata EXIT` 在本地 W3 路径下没有把文件还原。
   建议 W3 结束后由 `workflow_checks` 对 `conandata.yml` 做 `git diff --quiet` 断言，发现改写即自动还原并告警。
2. **refresh-patch 覆盖人工补丁分类**：`scripts/ohc/refresh_patch.py:532` 每次重写
   `patch_classification` 为 `type: auto / platform_only: True / guard: 'pending'`，
   finish [1/10] 又调一次，AI 在 manifest 里填好的分类被静默冲掉。建议补丁内容 hash 未变时保留已有分类。
3. **G0 clean-verify 对无构建包误判失败**：`scripts/ohc/clean_verify.py:173-181` 对 `headeronly`
   （脚本/数据包）也执行 `configure`，得到 exit 127 并输出 FAIL HANDOFF。建议 build_system 为
   headeronly/none 时直接跳过 G0。
4. **R46 草稿被跨任务终态挡住**：`scripts/ohc/result_report.py:788` 看到 `$HOME` 兜底位置已有
   `draft:false` 的**其他软件**的 result.json，就跳过本任务所有里程碑草稿（lang_checked /
   recipe_generated / conan_verify_passed 全部未写）。建议比较 software/version，不同任务时覆盖或另写文件。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. `templates/manifest-version.yaml:13` `software: "{software}"`、`:21` `build_system: "{BUILD_SYSTEM}"`
   在 init-build 后原样落盘（未渲染），且 `status: published` 缺省值与实际不符；需渲染并缺省为 `built`。
2. `templates/conanfile-headeronly.py.tmpl:28` 缺省 `package_type = "library"`，变体 C（脚本工具）
   应为 `application` 并配 `bindirs=["bin"]`；模板里 `get(self, **self.conan_data["sources"])` 与仓库
   主流的版本键 `sources["<ver>"]` 写法不一致，建议统一为 `[self.version]`。
3. `templates/test_package-executable/test.sh.tmpl:9` 只做 `--version || --help` 冒烟，对 R34/PF3
   属于弱测试；而 conan-init 同时生成的 `MANIFEST.yml` 仍写 `file: test.c` / `command: ./test_<name>`
   （与 test.sh 不匹配）。建议脚本类包的 MANIFEST 模板与 test.sh 对齐，并在 test.sh 里留出「固定输入 → 精确比对输出」的断言槽位。
4. 版本级 `notes.md` 模板（`templates/notes.md`）的 `{cmake|autotools|…}` 占位符无门禁校验，
   建议 finish 的就绪预检加 `grep -nE '\{[a-z]+\|'` 检查。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **lang-preflight 识别 shebang 脚本**：`scripts/ohc/lang_detect.py:149` 只按扩展名计数，
   无扩展名的 `#!/bin/sh` 主脚本（tzdiff、bootinfoscript）统计为 0 → `detected=other`，
   只能靠 `OHPCD_LANG=other` 绕过（且默认 cpp 时会**自动写 env_unsupported 终态**）。建议对无扩展名
   可执行文件读首行 shebang 归类为 bash，并在「唯一主体是 shell」时输出提示而非直接终态。
2. **feedback 自动采集**：`scripts/ohc/feedback.py:525` 把源码 tarball URL 当成上游仓库；失败表解析在
   notes 表格 `\|` 转义处截断；`:551` 草稿数按 .kv+.md 文件计成 2；测试统计取到 0（未读
   test_package/MANIFEST.yml 的 `assertion_count` 或 test-report）。本报告已人工修正以上各项。
3. `finish` step 8 `gen_summary` 报 `'str' object has no attribute 'append'`（`scripts/ohc/finish.py:337-345`），
   每次都作为「失败步骤 step8」出现在收尾结论里，干扰判断。
4. finish [10/10] 就绪预检仍要求 `packaging/`（ARCHIVE-SPEC v2.0 已废弃），属固定假告警，建议移除。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. 新增草稿 **E6402-draft-6E9A**：鸿蒙 shell 时区工具失效三件套——无 Olson 目录、musl 按名字只查打包
   tzdata（绝对路径 TZif 可用）、toybox `date` 无 `--date` 且 `-d` 拒收 ISO `T`。draft-review 最高相似度
   0.16（E037），与 E315（R 语言时区契约）互补，建议 promote。
2. 建议补一条 toybox 用户态命令差异对照（date/ln/gzip/sed/touch 目前分散在 E010、E402 与多份草稿），
   统一收录「GNU 长选项 → toybox 短选项」映射，供脚本类包预扫描（prescan_pattern）使用。
3. E037（鸿蒙可能无 /usr/bin/env）与已合入的 acme.sh/boot-info-script wrapper（`#!/usr/bin/env sh`）
   结论互相矛盾，建议主编以真机结果复核 E037 并在其中注明适用范围。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: 0F47
- **生成时间**: 2026-09-25 22:41:54
- **PR 编号**: —
- **Git Commit**: 见 PR 分支 feat/tzdiff-1.2.1 HEAD（报告与配方同一 commit，生成时的 1c34c0cf85 已被 amend）
