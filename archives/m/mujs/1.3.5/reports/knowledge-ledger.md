# mujs 1.3.5 知识候选台账（knowledge_candidate_ledger）

任务类型：知识库扩展（路径 B 候选评估）
- 决策：**new_draft**（已建同 stem 草稿对：
  `knowledge/drafts/mujs-1.3.5-test262-es5-upstream-entry.kv` + `.md`）
- 知识候选非噪声：test262 ES5 一致性套件作为嵌入式 JS 解释器类库的
  官方上游测试入口（无 make check；逐用例独立进程运行 harness）

## 候选记录

| 候选 | 真实错误/现象 | 根因 | 修复 | 验证 | 适用范围 |
|------|--------------|------|------|------|----------|
| C1: test262 ES5 入口 | mujs 无 make check；官方测试在 tools/test262 + harness.js，需外部 ES5 套件 | 嵌入式 JS 解释器以一致性套件为测试标准 | 克隆 tc39/test262 es5-tests 分支，tools/test262 <suite> 全量运行，逐用例独立进程 | 11724 用例：9636 通过 / 581 失败 / 21 跳过，全量通过率 82.19% | mujs 及同类嵌入式 JS 解释器（duktape/quickjs 类）OHOS 适配 |
| C2: js_dostring 不保留栈值 | test_package 首败：表达式栈顶非数字 | mujs API 语义：js_dostring 执行后不保留表达式值 | 经全局变量读取（js_dostring 写 var，js_getglobal 读） | test_package 真实 API 测试通过 | mujs 嵌入方（C API 用户） |
| C3: CLI 无 --version/--help | mujs --version 报 unknown option | getopt 仅 -i/-s | L2 smoke 用 mujs-pp --version + 真实 JS 脚本验证 CLI | W3 L2 pass（非阻塞警告） | mujs 类无版本选项 CLI |

## 七轴查重

| 轴 | 结果 | 说明 |
|----|------|------|
| exact_duplicate | false | 知识库无 mujs / test262 / HAVE_READLINE 条目（index.tsv 540 条全库搜索无命中） |
| causal_duplicate | false | 无同类"JS 解释器测试入口"根因条目 |
| trigger_overlap | partial | E363（/tmp 只读）、E108（install 缺失）触发面有交集，但本候选核心是测试入口方法论，非平台陷阱；E363/E108 为已收录不同条目，不构成重复 |
| solution_overlap | partial | opencsg jobserver mkfifo 草稿覆盖 make 告警（触发面），本候选方案面不同（测试入口）；无覆盖 test262 的既有方案 |
| combination_novelty | true | "Makefile 无 configure + HAVE_READLINE=no + test262 ES5 套件 + js_dostring 全局读取 + 无 --version CLI"组合在知识库无既有条目 |
| boundary_novelty | true | 明确适用边界：仅嵌入式 JS 解释器类库；反例：非 JS 引擎库无需 test262 |
| test_migration_novelty | true | 将 test262 ES5 全量套件（11724 用例）迁移/运行于 OHOS arm64 并给出双口径统计，属首次记录 |

## 关系字段

- similar_to: []（无既有近似条目）
- caused_by: []（非既有知识引发）
- prerequisite_of: []（无下游条目依赖）
- conflicts_with: []（无冲突）

## 覆盖/新增差异

- 既有条目覆盖部分：E363（/tmp 只读临时目录）、E108（install 缺失）是环境处理层，
  本候选不重复收录；
- 本轮新增部分：①嵌入式 JS 解释器官方测试入口识别（test262 harness）；②mujs
  具体配方要点（HAVE_READLINE=no、cwd=source_folder、conf dict 取编译器）；
  ③js_dostring 全局变量读取 API 语义；④CLI 无 --version 的验证替代。

## 适用边界/反例

- 适用：mujs 及同构嵌入式 JS 解释器（纯 Makefile、无 configure、以 test262
  一致性套件为测试标准）在 OHOS 的适配；
- 反例：非 JS 引擎库（无 test262 入口）；有 make check 的常规 Makefile 库
  （测试入口识别逻辑不同）。
