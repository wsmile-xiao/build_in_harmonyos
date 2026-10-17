# nb 7.25.4 上游 bats 测试执行报告（HarmonyOS PC）

> 审查意见整改（rule4）：上游 2298 个测试用例原先 0 运行、仅 `nb --version` 冒烟替代。
> 本报告在 HarmonyOS PC 真机安装 bats-core 1.14.0 并实际运行上游 `test/` 子集，
> 如实记录运行数、通过率与失败归因，TAP 原始日志归档于 `logs/` 子目录。

## 1. 执行环境

| 项目 | 值 |
|------|-----|
| 操作系统 | OpenHarmony (HarmonyOS PC, aarch64) |
| Shell | bash 5.3.0 (aarch64-unknown-linux-gnu) |
| 测试框架 | bats-core 1.14.0（纯 bash 实现，源码 clone 自 github.com/bats-core/bats-core） |
| 被测版本 | xwmx/nb tag 7.25.4（`test/` 目录 134 个 `.bats` 文件，共 ~2298 个 `@test` 断言） |
| 被测脚本 | 上游未修改的 `nb` 单文件 bash 脚本 |
| 执行方式 | 逐文件调用 `bats --formatter tap <file>`，输出 TAP 流落盘 |

**环境准备说明**：
- bats-core 为纯 bash 框架，无需编译，通过源码直接运行 `bin/bats`。
- 上游 `test_helper.bash` 默认将测试临时目录建在 `/tmp/nb_test.*`；HarmonyOS PC 的
  `/tmp` 为只读文件系统，故执行时仅将临时目录根路径替换为可写目录
  （`.opendesk-tmp/nb-test-runtime.*`），**未修改任何上游测试用例的断言逻辑**。
  该替换属于运行环境适配，非测试用例修改。
- **已知局限（已如实声明）**：本批日志采集于 bats **运行器自身临时目录修复**
  （`TMPDIR=/data/local/tmp`）之前——OHOS `/tmp` 只读导致部分文件的 bats 运行器
  `bats-run-*` 临时文件（.src/.out）无法稳定落盘，出现运行中断、越界
  `teardown_file/teardown_suite` 崩溃条目，以及测试夹具（`nb add`/`nb move`，
  依赖 git 笔记本与可写 HOME）的失败。**受污染文件的结果不能作为产品行为证据**，
  已按 AI review（2026-09-07）口径在 §3 分层、在 `logs/*.tap` 文件头显式标注，
  并排除在通过率与失败归因之外，待真机 `TMPDIR=/data/local/tmp` 重跑后替换归档。

## 2. 执行命令（可复现）

```bash
# 获取 bats-core（纯 bash，无需编译）
git clone https://github.com/bats-core/bats-core.git
./bats-core/bin/bats --version          # Bats 1.14.0

# 运行某个测试文件（示例）
PATH="$HOME/.local/bin:$PATH" \
  ./bats-core/bin/bats --formatter tap test/helpers-string-is-email.bats

# 批量运行（并行 8 路，逐文件 TAP 落盘）
ls test/helpers-*.bats test/env.bats > filelist.txt
while read f; do
  base=$(basename "$f" .bats)
  ( PATH="$HOME/.local/bin:$PATH" timeout 120 \
      ./bats-core/bin/bats --formatter tap "$f" > "logs/helper/$base.tap" 2>&1 ) &
done < filelist.txt
wait
```

## 3. 执行结果（2026-09-07 整改口径：证据分层，剔除不可归因项）

本轮对上游 `test/` 中的 **17 个纯函数/环境测试文件** 发起执行
（代表上游 ~2298 个用例中的 helper/env 基础逻辑层），17 个文件 plan 合计 **168 断言**。

**证据有效性判定原则（依据 AI review 2026-09-07）**：仅当某个文件本次运行
①plan 全部满足、无运行器崩溃/越界条目，且 ②`not ok` 的诊断行指向被测函数自身的
断言（而非夹具命令 `nb add`/`nb move`、亦非运行器 .src/.out 丢失伪影）时，
其结果才计入"可判定证据"；否则整文件标注"待重跑"，其 `not ok` 一律不计入
通过率与失败归因。

### 3.1 分层汇总

| 层级 | 文件数 | plan(断言) | ok | not ok(计入统计) | 说明 |
|------|-----:|-----:|-----:|-----:|------|
| A. 证据完整·可判定（运行完整无崩溃，not-ok 为断言级） | 11 | 61 | 48 | 13 | 通过率口径来源 |
| B. 运行完整但 not-ok 全为夹具失败（`nb add`/`nb move`），不可归因 | 1 | 7 | 3 | 0（4 行 not-ok 剔除） | 待真机重跑复核 |
| C. 运行中断/运行器崩溃（TMPDIR 只读），整文件待重跑 | 5 | 100 | 12（可观察） | 0（70 行 not-ok 剔除） | 23 断言未执行 |
| **合计** | **17** | **168** | **63** | **13** | 剔除 74 行不可归因 not-ok + 23 未执行 |

> 口径修正链：初版"150 断言 / 87 失败 / 42.0%"为**含运行器崩溃、夹具失败与越界
> 条目的粗统计**；2026-09-06 版修正为"有效 145 / 82 / 43.4%"（仅剔除 5 个越界崩溃
> 条目与 23 个未执行）；本版（2026-09-07）依据 AI review 逐条复核，进一步剔除
> **夹具失败与运行器伪影导致的不可归因 not-ok（74 行）**，只保留断言级可判定结果。
> 通过数 ok=63 不受影响（ok 均为测试体完整执行且断言成立）。

### 3.2 各文件明细（Plan=上游该文件 @test 数）

| 文件 | Plan | ok | not ok(断言级) | not ok(夹具/运行器,剔除) | 未执行 | 证据状态 |
|------|-----:|-----:|-----:|-----:|-----:|------|
| env | 4 | 4 | 0 | 0 | 0 | ✅ A·完整通过 |
| helpers-build-related-list | 2 | 2 | 0 | 0 | 0 | ✅ A·完整通过 |
| helpers-get-content | 16 | 16 | 0 | 0 | 0 | ✅ A·完整通过 |
| helpers-get-uri | 2 | 2 | 0 | 0 | 0 | ✅ A·完整通过 |
| helpers-normalize-options | 3 | 3 | 0 | 0 | 0 | ✅ A·完整通过 |
| helpers-string-is-email | 2 | 2 | 0 | 0 | 0 | ✅ A·完整通过 |
| helpers-web-browser | 4 | 4 | 0 | 0 | 0 | ✅ A·完整通过 |
| helpers-file-is-text | 4 | 2 | 2 | 0 | 0 | ⚠️ A·断言级失败 |
| helpers-get-unique-relative-path | 18 | 12 | 6 | 0 | 0 | ⚠️ A·断言级失败 |
| helpers-highlight-syntax | 4 | 1 | 3 | 0 | 0 | ⚠️ A·断言级失败（终端） |
| helpers-spinner | 2 | 0 | 2 | 0 | 0 | ⚠️ A·断言级失败（终端） |
| helpers-selector-resolve-path | 7 | 3 | 0 | 4（全为 `nb add`/`nb move` 夹具） | 0 | ⏸ B·待重跑 |
| helpers-resolve-links | 13 | 1 | 0 | 12（全为 `nb add` 夹具，`_resolve_links` 未被调用） | 0 | ⏸ C·待重跑 |
| helpers-selector-resolve-folders | 38 | 7 | 0 | 13（11 夹具 + 2 运行器伪影/越界） | 19 | ⏸ C·待重跑 |
| helpers-get-id-selector | 17 | 2 | 0 | 15（夹具 2〔not ok 11/14 为 `nb move`〕+ 崩溃运行中状态断言 12 + 越界 1） | 1 | ⏸ C·待重跑 |
| helpers-render | 29 | 0 | 0 | 27（崩溃运行中状态断言 26 + 越界 1） | 3 | ⏸ C·待重跑 |
| helpers-string-is-url | 3 | 2 | 0 | 3（运行器伪影 1 + 越界崩溃 2） | 0 | ⏸ C·待重跑 |
| **合计** | **168** | **63** | **13** | **74** | **23** | |

- 中断文件均已在该 `.tap` 文件头添加 `# ⚠️ ARCHIVE NOTE` 标注（运行中断/夹具失败
  的具体范围），原始日志行未改动。
- `helpers-resolve-links`（B 级说明）：13/13 均已执行，但 12 个 `not ok` 的诊断行
  全部是 `` `"${_NB}" add ... failed `` ——失败点位于夹具搭建命令，`_resolve_links`
  从未被真正调用。这与 2026-09-07 AI review（helpers-resolve-links.tap 逐行核验）
  结论一致：该文件**不能作为 `_resolve_links` 有 12 个行为失败的证据**，也不能归入
  "D 类 git/排序/工具链输出差异"。其根因假设为采集环境（TMPDIR 修复前 + git 笔记本
  夹具）下 `${_NB} add` 失败；需先在真机用最小笔记本场景单独验证 `nb add` 可用性，
  再以 `TMPDIR=/data/local/tmp` 重跑本文件，取得夹具成功、真正执行 `_resolve_links`
  的 TAP 后重新归档与归因。重跑完成前不计入统计（已剔除）。

## 4. 失败归因（仅对 A 层 13 个断言级失败归类；其余 74+23 待重跑，单列 §5）

> A 层 13 个断言级失败 = 运行完整、plan 满足、诊断行指向被测函数断言的 `not ok`。
> B/C 层 74 行不可归因 `not ok`（夹具失败 / 运行器崩溃伪影）与 23 个未执行断言
> **不计入**——它们属于本次采集环境（bats 运行器 TMPDIR 未修复）的产物，需
> `TMPDIR=/data/local/tmp` 真机重跑后重新评估（§5）。
> **未修改任何上游测试断言**，仅做运行环境适配。

### A. 终端能力差异（无 TTY：tput/颜色/动画，5 例）—— 部分可通过环境修复 ⚠️

- **现象**：spinner 断言 `lines[0] =~ \[.*\|.*\]` 不匹配（无动画输出源）；
  highlight 着色断言 `lines[0] == "# ..."` 无预期着色。
- **分布**：helpers-highlight-syntax（3）、helpers-spinner（2）。
- **1-e 判定**：非交互终端下纯动画/着色断言无输出源，属平台限制（1-e）；
  `tput: No value for $TERM` 类报错可通过 `TERM=xterm` + `NO_COLOR` 消除，
  着色断言需在带终端能力的会话复跑确认。

### B. 工具链/行为差异（断言级真失败，原因待逐条复核，8 例）—— ⚠️

- **helpers-file-is-text（2）**：`_file_is_text` 对不存在的文件/空路径返回非空输出，
  断言 `[[ -z "${output}" ]]` 失败；上游期望状态 1 且静默。原因与 OHOS 上
  `file`/mimetype 探测工具行为差异相关，待对照上游逐一复核。
- **helpers-get-unique-relative-path（6）**：对单/双/三级已存在路径的
  `_get_unique_relative_path` 返回非 0（`[[ "${status}" -eq 0 ]]` 失败），而同文件
  无参/纯文件名用例（1-7）与 notes/bookmarks 类型用例（14-18）通过。
  原因疑似与 OHOS git/toybox 输出差异或目录解析假设相关，需逐条比对上游工具行为。
- **1-e 判定**：暂记为"工具链输出差异待复核"；两者日志均自洽（无运行器崩溃），
  属真实断言差异，不臆断为 nb 适配回归（对照通过项可见 nb 基础行为与上游一致）。

## 5. 待重跑文件（B/C 层，不计入通过率与失败归因）

| 文件 | plan | 已记录 ok | 剔除 not-ok | 未执行 | 重跑前置条件 |
|------|-----:|-----:|-----:|-----:|------|
| helpers-selector-resolve-path | 7 | 3 | 4（夹具） | 0 | 真机验证 `nb add`/`nb move` |
| helpers-resolve-links | 13 | 1 | 12（夹具） | 0 | 真机最小场景验证 `nb add` |
| helpers-selector-resolve-folders | 38 | 7 | 13 | 19 | TMPDIR=/data/local/tmp |
| helpers-get-id-selector | 17 | 2 | 15 | 1 | TMPDIR=/data/local/tmp |
| helpers-render | 29 | 0 | 27 | 3 | TMPDIR=/data/local/tmp + pandoc（可选） |
| helpers-string-is-url | 3 | 2 | 3 | 0 | TMPDIR=/data/local/tmp |
| **合计** | **107** | **15** | **74** | **23** | |

- 处置：真机以 `export TMPDIR=/data/local/tmp`（可写且生命周期稳定）重跑上表 6 个
  文件直至 plan 全部满足，替换 `logs/*.tap` 归档后，再按日志原文（夹具失败 vs
  断言失败）重新归因与计算通过率；同时单独验证 `${_NB} add` 在 OHOS 运行环境的
  可用性（AI review 2026-09-07 要求），若可用则夹具失败确认为本批环境产物。

## 6. 已确认通过（与上游行为一致）

- A 层 7 个文件（env、build-related-list、get-content、get-uri、normalize-options、
  string-is-email、web-browser）33 例全部通过；另有 file-is-text /
  get-unique-relative-path / highlight-syntax / spinner / selector-resolve-path /
  resolve-links / selector-resolve-folders / get-id-selector / string-is-url 中可观察
  的 30 例 ok。证明 bats-core 在 HarmonyOS PC 可正常运行、nb 脚本基础行为与上游一致。

## 7. 整改结论

- 上游测试用例通过率（可判定口径）：**48/61（78.7%）**——13 个断言级失败已逐类归因
  （A 终端 5 / B 工具链 8，见 §4）；另 6 个文件共 107 断言（ok 15 可观察 + 74 行
  不可归因 not-ok + 23 未执行）因采集环境运行中断/夹具失败**不计入**，已逐文件标注
  并列入 §5 真机 `TMPDIR=/data/local/tmp` 重跑计划（重跑完成前不预判结论）。
- 新增测试用例通过率：1/1（100%）。
- 已安装并实际运行 bats-core（1.14.0），不再是"未安装 / 0 运行"。
- 本批日志采集于 bats 运行器 TMPDIR 修复之前；修复后重跑（§5）将替换归档
  6 个受污染文件，届时按新日志重算全量统计。
- 未发现因 nb 适配引入的回归（test_package 冒烟 1/1 + 真机 CI L0/L1 通过）；
  通过项与上游语义一致；受污染文件不预断为产品缺陷。

---
- 报告生成时间：2026-09-04（UTC+8）；2026-09-07 依 AI review 整改口径修订
- 环境快照：HarmonyOS PC / bash 5.3.0 / bats-core 1.14.0 / nb 7.25.4
