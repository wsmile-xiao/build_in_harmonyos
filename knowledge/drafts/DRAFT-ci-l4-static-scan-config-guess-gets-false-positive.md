# DRAFT-ci-l4-static-scan-config-guess-gets-false-positive — CI L4 对 config.guess/config.sub 导入文本的 gets/sprintf 误报面（warn 不计失败）

> **Contributor**: GoliWie | **Status**: DRAFT | **Updated**: 2026-09-03
> **Severity**: minor (3) | **Category**: ci / static-scan / false-positive / autotools
> **Audience**: 处理权威 CI L4 warn 的移植 Builder 与 Reviewer；维护 config.guess/config.sub 导入补丁的配方作者

## 触发（trigger）

- 库为 autotools 构建，补丁含 config.guess/config.sub 的**导入文本 diff**
  （增加 HarmonyOS/ohos-linux 识别等，是 OHOS 适配的标准做法）。
- 权威 CI 的 L4 步骤对 `patches/` 目录全部文本执行
  `grep -rlE '(strcpy|sprintf|gets|strcat)\b'` 静态扫描。

## 症状（symptom）

CI 输出 `[warn] L4: Dangerous functions found in patches:` 并列出
0001-config.guess.patch 之类的导入补丁；但整体 RC=0、Build Summary 照计 Success。
实例：run libgee-0.20.8.1 ci-run1 行1915 `L4_RESULT=warn: dangerous functions in patches`，
行1920-1924 Build Summary Total 1 / Success 1 / Failed 0，行1927 RC=0。
实测命中内容：`grep -oE '(strcpy|sprintf|gets|strcat)\b'` 对该补丁仅 1 处 `gets`
（config.guess 上游导入文本自身），补丁与已发布 0.20.8 版本逐字相同——继承性误报。

## 机制（root cause）

L4 是面向"补丁作者引入危险函数"的保守静态扫描，无上游导入文本白名单；
config.guess/config.sub 是 autoconf/libtool 官方分发文件，其探测代码天然引用
`gets`/`sprintf` 等词（diff 上下文行被整行扫描）。命中 ≠ 补丁引入缺陷。
warn≠fail 语义在扫描器本体可自包含核对：L4 步骤命中后**仅赋值**
`L4_RESULT=warn` 与 `L4_DETAIL`（ci/conan/build_and_test.sh:1469-1474），汇总阶段
只 `echo` 结果与写 ci-metadata.json（:1726、:1767），不参与 RC/Build Summary 判定。
风险前瞻：凡带此类导入补丁的库都会继承性命中；若未来 CI 把 warn 升级为失败，
将批量影响——本条属预防性沉淀。

## triage 规则（rec）

1. **warn 不是失败**：RC=0、Build Success 照计，不阻塞交付。
2. **核对同源性**：确认命中补丁与上游导入文本逐字同源（与已发布版本同 patch，
   或与上游 autoconf/libtool 原文比对）；同源即接受 warn 并在报告记录一句说明。
3. **禁止**为消 warn 修改导入补丁、修改 ci/config 豁免清单（CI 面归 CI 管辖，
   单库适配不得动）或绕过扫描。

## 退路（fallback）

同源性核对**不通过**时（补丁非标准导入 diff、含本地改动、无已发布同名补丁可比对），
不得以"warn 不计失败"直接接受：升级为疑似真实缺陷人工审查——与上游 autoconf/libtool
原文逐行比对命中词上下文，区分导入文本自带还是补丁作者引入；作者引入的危险函数按
正常工程缺陷处理（换安全写法并验证功能）。诚实权衡：config.guess/config.sub 为千行级
导入文本，人工逐行比对成本高且无自动化判定，仅在核对不通过时启用；启用前 warn 状态
须在报告中如实标注"待人工核对"而非"已接受"。

## 反模式（forbid）

1. `sed -i`/`patch -R` 修改 patches 内 config.guess/config.sub 导入补丁来消 warn——
   破坏同源性与可重复应用，补丁漂移、后续版本复用失败、引入真实适配回归。
2. 修改 build_and_test.sh 扫描逻辑或维护 L4 豁免清单——改 CI 门禁本体，单库适配
   无权变更门禁语义；豁免会同时放过未来真实引入的危险函数，门禁失效扩散全仓。

## 原则挂靠（principles）

- **P-AUTOTOOLS-001**（最近邻挂靠）：该原则保护 config.guess 的系统检测语义
  （禁止 `--build`/`--host` 绕过检测）；本条 forbid_1（不改导入补丁、保持逐字同源）
  与其同向——config.guess/config.sub 是 autoconf 系统检测基础设施，保持同源即不污染
  其检测语义。诚实边界：CI 静态扫描误报分类（warn/fail 语义、误报面 triage）本身
  无专属 P，建议知识库主编考虑新增（如"CI 门禁 warn 与 fail 语义必须可自包含核对"
  方向的 P-CI-001），本条可作首例支撑。

## 形态选择理由（kv 而非 pre-scan-rules.yaml）

按 curation-policy「B 形态分流」，CI 扫描误报/规则类知识优先考虑
knowledge/graph/pre-scan-rules.yaml 规则形态；本条经核验选择 **kv 条目**，理由：

1. **人工 triage 程序，非可执行 pattern**：本条的核心交付物是"对既有 CI 门 warn 的
   逐字同源核对程序"，无法表达为 pattern+scope_globs+severity 的预扫描规则。
2. **yaml 无白名单/suppress 语义**：pre-scan-rules.yaml 现有规则集（PSCAN-*）只有
   命中→severity→solution_hint 的单向告警语义，没有"命中但接受"的白名单/suppress
   机制（dangerous-functions/patches 类规则现为 0 条，Curator 复验）；硬写入只能做成
   "文档化重复"，不产生可执行价值。
3. **L4 逻辑不受 yaml 驱动**：L4 内置于 `ci/conan/build_and_test.sh`
   （`grep -rlE '(strcpy|sprintf|gets|strcat)\b' "$PATCH_DIR"`），不读取
   pre-scan-rules.yaml；yaml 侧新增规则不改变 L4 行为。
4. **机理叙事+方案空间+forbid 进 kv 更可复用**（E415 先例证明 CI 机制类 kv 可收录）。

非阻塞可选：请知识库主编考虑在 pre-scan-rules.yaml 增 severity:info 注记性规则
（PSCAN-PATCH-001，pattern 指向 patches 内 config.guess/config.sub 导入文本，
kb_ref 指向本 kv），仅作检索入口，不承担门禁语义。

## 查重（dedup）

零覆盖维持：`config.guess|dangerous function` 于 knowledge/graph 与 knowledge/drafts
0 命中；经验仓 ophs_ci_review（`*.md` 检索 config.guess/L4/dangerous functions）
0 命中（Curator §1.2 亲验）。但存在**同族 CI 机制条目**（挂 similar_to，不构成覆盖）：

- E415（CI Mirror-fallback 原地改写 worktree conandata.yml 需在 CI 后恢复，title
  自注"与 L4 误扫关联"）：同属权威 CI 机制的行为面；其范围是 conandata.yml 镜像
  改写与恢复，与本条的 L4 静态扫描 warn triage 不重叠。
- E403（Conan test() 每次运行在 test_package 再生构建/测试残留，交付前必须清理）：
  CI 产物卫生族；机制（构建残留 vs 扫描误报）不同。

初稿"无类似条目"表述有误，修正为：**零覆盖（两者均不覆盖本条问题类）但同族可链**。

## 证据（evidence）

- 机理自包含核对：`grep -oE '(strcpy|sprintf|gets|strcat)\b'
  archives/l/libgee/0.20.8.1/patches/0001-config.guess.patch` → 恰 1 处 `gets`；
  `grep -n -B4 -A10 'Dangerous functions found in patches' ci/conan/build_and_test.sh`
  → DANGER 命中后仅赋值 L4_RESULT=warn（:1469-1474，无 exit/RC 影响）；
  `grep -n 'L4_RESULT' ci/conan/build_and_test.sh` → 汇总仅 echo/写 metadata。
- 同源性核对：`diff -q` 0.20.8 与 0.20.8.1 的 0001-config.guess.patch → 空（逐字相同）。
- run 级佐证：runs/libgee-0.20.8.1/logs/ci-run1.log:1915（warn 原文）、:1920-1924
  （Success 1/1）、:1927（RC=0）。

## 关系

- principles: P-AUTOTOOLS-001（最近邻：config.guess 系统检测语义完整性；见原则挂靠节）。
- similar_to: [E415, E403]（CI 机制同族；差异见查重节）。
- 与 DRAFT-conan-skipped-binaries-package-folder-null-guard（同 run 线索 a）受众与
  动作不同，不合并。
