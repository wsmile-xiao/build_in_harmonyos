# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_e5768468.md`

---

## 背景

- **软件名称**: shml
- **版本**: 1.1.0
- **构建日期**: 2026-09-29
- **构建系统**: custom（纯 Bash 脚本库，无编译；自动采集写成了 `{BUILD_SYSTEM}`，已按实修正）
- **上游仓库**: https://github.com/odb/shml（自动采集取到的是源码包 URL，已修正）
- **适配路径**: 路径 A（基础适配，无补丁）+ 知识库扩展（新增草稿 E6440、E6441）
- **补丁数量**: 0
- **编译依赖**:
无
- **最终状态**: 本地验证通过（status=built）；PR 建立后的机器人检视与 CI 结果不在本报告范围

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交前的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 构建系统被猜成 autotools（源码无 configure，实为脚本库） |
| build | 编译构建 | 成功 | 构建系统: custom（无编译，手写配方） |
| conan-verify | 配方验证 | 通过（G0–G4） | 首轮 G1 因缺 `export_sources()`/补丁应用调用失败 1 次 |
| finish | 归档收尾 | 完成 | W3 首轮因 test_package 版本解析失败 1 次，修复后通过；G0 clean-verify 走 autotools 路径失败（非阻塞） |
| submit | PR提交+AI检视+CI | 未到达 | 本报告须先于建 PR 定稿；检视与 CI 在建 PR 之后才会产生 |

### 失败与问题

- **#1 conan-init 骨架不可用**: 根因=Makefile 被识别为 autotools，模板含 `cpp_info.libs=["shml"]`、扁平 `sources:`、`{BUILD_SYSTEM}`/`{software}` 占位符, 解决方案=手写无编译配方并补实 manifest
- **#2 语言预检把 Bash 库判为 nodejs**: 根因=`package.json` 仅为 npm 分发元数据，`.sh` 不计入主体, 解决方案=只读调用 `detect_language()` 留证，不运行会落 `env_unsupported` 终态的 `lang-preflight`
- **#3 上游 `make test` 运行时 `curl | bash` 下载 shunt**: 根因=浮动引用、无校验和、配方内 curl 被 CI L0o 禁止, 解决方案=固定官方 tag 归档 + sha256（知识草稿 E6440）
- **#4 shunt 遇含 `-h` 的路径静默 usage 并以 0 退出**: 根因=`grep "\-h"` 扫描含全部测试路径的 argv, 解决方案=只传相对路径并断言汇总 `Total==172`
- **#5 G1 报缺 `export_sources()` 与补丁应用调用**: 根因=门禁做字面检查, 解决方案=保留两个标准调用（无补丁为空操作）
- **#6 conan-verify 通过而 W3 失败**: 根因=`tested_reference_str` 在 W3/CI 形态为 `name/ver#revision%timestamp`, 解决方案=改用 `dependencies[...].ref.version`（知识草稿 E6441）
- **#7 W3 脚本把 `conandata.yml` 改成 `gh-proxy.com` URL 列表且未真正还原**: 根因=先追加镜像回退、之后才备份, 解决方案=每次 finish 后 `git checkout -- conandata.yml`，提交前核对只含官方 URL

### 知识图谱使用情况

- **引用知识条目**: E325（bash 发现回退到 `/data/service/hnp/bin/bash`，已用于两处 `_find_bash`）；`engine` 对 shunt 片段只命中泛化的 E185（HTTPS 证书），不适用
- **新增知识草稿**: 2 条（E6440、E6441），`draft-review` 均判 `create`（最高相似度 0.09 / 0.16）
- **引擎命中情况**: 无针对性命中；报告骨架里的“草稿目录 2516 条”是共享草稿目录的总数，与本次无关
- **测试统计**: 总计 173, 通过 173, 失败 0, 跳过 0（上游 172 + 鸿蒙特有消费者 1；骨架自动采集为 0，因生成时 test-report.md 尚未写出）
- **未覆盖的错误模式**: 已沉淀为 E6440、E6441；“带 package.json 的 Bash 库被判 nodejs”已有多条相近草稿（见下方建议），未再新增

### AI 检视结果

- **检视阶段到达**: 未到达（PR 尚未创建）
- **变更摘要评估**: 不适用（建 PR 前定稿）
- **检视意见数量**: 不适用
- **检视意见处理**: 不适用

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（Pass rate 100% (1/1)；L1 pass、L2 skip（无 bin/）、L4 pass、L5 warn（无 artifacts））
- **远程 CI (PR 校验)**: 未触发（建 PR 之后才触发）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 4（finish 两次运行各 1 个 G0 clean-verify 块，非阻塞；W3 阻塞块 1 个；知识整理提示块 1 个）
- **重试次数**: 2（conan-verify G1 一次；W3 一次），finish 共运行 2 次
- **关键瓶颈**: conan-verify 与 W3 使用不同的 `conan create` 形态，test_package 里依赖引用字符串的缺陷晚一步才暴露；W3 脚本对 conandata 的改写需要人工核对并还原
- **耗时较长的步骤**: 单次 `conan create`（含下载两个源码包、编译并用 qemu 运行消费者）在本机约 2 分钟；其余时间主要用在核对门禁行为

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-29T15:54:37 | skeleton_created | result_partial |
<!-- EVENTS:END -->

---

## 建议

### SKILL 设计改进

1. `scripts/ohc/lang_detect.py:117-121`（`_manifest_scan` 的 package.json 分支）与 `:159`、`:183`（bash 不计入主体）：纯 Bash 库带 npm 分发用 `package.json` 时，没有任何 JS 源文件也被判 nodejs（本次 `source_stats` 为“无源文件可统计”），`lang_preflight_cli`（`:315` 的 `result_cli`）随即写终态 `env_unsupported`。建议 ① package.json 只有在统计里存在 ≥1 个 `.js/.ts`（或 `main` 指向 `.js`）时才判 nodejs，否则继续看 Makefile 与统计；② 给 `lang-preflight` 增加只读探针模式（如 `--probe`：只打印判定、不写回执）。现在只能手写 `python3 -c` 调 `detect_language`。
2. `scripts/ohc/conan_verify.py:583` 的 G2 传 `--user/--channel`，而 W3（`ci/conan/build_and_test.sh`）与 CI 不传，`tested_reference_str` 因此形态不同（E6441），conan-verify 通过、W3 才失败。建议 G2 改为与 W3/CI 相同的无 user/channel 形态，让两道门禁对同一配方给出一致结论。
3. `ci/conan/build_and_test.sh:1179-1188`：`PREDL_BACKUP` 在“追加镜像回退”（`:1145-1160`）之后才备份，`_restore_conandata` 写回的是已带 `gh-proxy.com` 的版本，日志却输出“已还原为官方 URL”。每次 finish 后工作树里的 `conandata.yml` 都带镜像 URL，直接 `git add` 会触发 PF7。建议在镜像改写之前备份。
4. `scripts/ohc/preflight.py:559-570`（PF9 拒绝所有不满 5 段的 `archives/` 路径）与 ARCHIVE-SPEC §2.1（软件级 `README.md`/`manifest.yaml` “必须”）和 `scripts/ohc/finalize_archive.py:87` 的缺失告警相互矛盾。建议 PF9 放行 `archives/<字母>/<包>/` 下 `README.md`、`manifest.yaml`、`commands.json` 三个固定文件名。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. `templates/manifest-version.yaml:13,21` 的 `{software}`/`{BUILD_SYSTEM}` 未被 init-archive 替换，版本级 manifest 与本报告的背景、执行概要各出现一次原样占位符。建议渲染时对未知构建系统回落到 `custom`。
2. `templates/conandata.yml.tmpl:6-8` 与 `scripts/ohc/conan_recipe.py:299-301` 生成扁平 `sources:` 且 sha256 留 `REPLACE_WITH_ACTUAL_SHA256`；仓库主流是版本键 `sources: {"<ver>": {...}}`。建议改为版本键，并在 init-build 已下载 tarball 时直接填入实测 sha256。
3. `templates/conanfile-headeronly.py.tmpl` 没有“脚本库”变体：应装 `share/<pkg>/`、`resdirs=["share"]`、`runenv_info.define_path`、不设 `package_type`（避免 PF8 误判 CLI 而要求 commands.json），且缺对应的 test_package 模板（脚本输出 → 生成头文件 → 交叉编译 C 消费者 → qemu 运行）。脚本库/数据包正是 rule12 最容易失分的类型，建议新增。
4. `scripts/ohc/conan_verify.py:491-492` 的 G1 用字面串检查 `export_sources` 与 `apply_conandata_patches`；无补丁的脚本包也得写两个空操作。建议 conandata 无 `patches` 键时豁免。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. `scripts/ohc/init_build.py:78-86` 的 `_guess_build_system(url)` 只看 URL 并默认 autotools，从不看源码树。本次仓库只有一个只含 install/test/clean 目标的 Makefile，结果 `.build-context` 写 `BUILD_SYSTEM="autotools"`，G0 clean-verify 去跑 `./configure`（失败，finish 每次都输出 HANDOFF 块），conan-init 生成 autotools 骨架。建议按源码树判定：无 `configure.ac`/`Makefile.am`/`CMakeLists.txt`/`meson.build` 且 Makefile 无编译规则 → `custom`，conan-init 选脚本库模板，G0 直接跳过。
2. `scripts/ohc/submission.py:603` 把自动生成的 PR 正文里“鸿蒙特有测试”写死为 `0`，而 rule12 判 N=0 为 FAIL。建议用 `test_package/MANIFEST.yml` 的 `test_package_tests` 条目数生成，为 0 时拒绝生成正文。
3. `scripts/ohc/conan_verify.py:565-573` 注入镜像后，`finally`（`:628`）只写回 conandata，从不删除 `conandata.yml.ghfast-bak`；备份要到下次运行开头才被 `_recover_ghfast_bak`（`:52-70`）清理。建议在 `finally` 里恢复后 `bak_path.unlink(missing_ok=True)`（该文件被 gitignore，本次未入仓）。
4. finish 的 Step 8 `gen_summary` 每次报 `'str' object has no attribute 'append'`（非阻塞）；Step 10 的“packaging/ — 需创建 packaging/ 目录并打包”与 finalize-archive 的“缺少 release tar.gz”对 v3.0 配方都是假告警，建议按 ARCHIVE-SPEC 删除。
5. `.staging-verified` 与 `reports/test-report.md` 目前靠人工造。建议 conan create 通过并校验 `package_folder` 后自动写 `.staging-verified`，由 `conan-create.log` 中的 `UPSTREAM TEST PASS/FAIL` 行生成 `test-report.md`。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. 新增 E6440（上游测试框架运行时 curl|bash 拉浮动引用、shunt 的 `-h` 静默跳过）与 E6441（`tested_reference_str` 的 `#revision%timestamp` 后缀），已随本 PR 放入 `knowledge/drafts/`，建议主编 promote。
2. `rg -l 'lang-preflight|lang_detect' knowledge/drafts/*.kv | wc -l` 为 48，其中“package.json / 纯脚本包被误判”至少 6 条（`DRAFT-libok-0.6.5-langpreflight-clib-packagejson-misdetect`、`E6401-draft-1AD8`、`E543-draft-27D5`、`E999-draft-351D` 等）。建议主编合并成 1 条正式条目并优先修 `lang_detect.py`，不要再逐库新增草稿。
3. 建议给 E6440 补 `prescan_pattern`（如对 Makefile 的 `curl[^|]*\|\s*(ba)?sh`），让预扫描在适配前就提示“上游测试要下载框架”。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: 8730
- **生成时间**: 2026-09-29 15:54:37
- **PR 编号**: —
- **Git Commit**: 445d5d05db
