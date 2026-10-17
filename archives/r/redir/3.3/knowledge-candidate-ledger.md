# 知识候选台账 — redir 3.3

任务类型: 知识库扩展（knowledge_candidate_observation: required）
判定日期: 2026-09-21
判定: **reuse_existing**（路径 A，无新增可跨库复用差异，不建草稿）

## 候选收集（非噪声）

| # | 候选 | 真实错误/现象 | 根因 | 修复 | 验证 |
|---|------|--------------|------|------|------|
| C1 | git archive 快照无 configure 且本机缺 automake/aclocal | `autoreconf -fi` 报 `Can't exec "aclocal"` | 最小 OHOS 镜像仅带 autoconf 套件；上游 tag tarball 为 git archive 快照，无 configure | `tool_requires("automake/1.18") + tool_requires("libtool/2.5.4")`，build() 中 `autoreconf -fi` | conan create G2 PASS |
| C2 | config.status 创建临时目录失败 | `./config.status: ./confXXXXXX/subs1.awk: Permission denied` | E114：HMDFS 强制 setgid；`umask 077 && mktemp -d` 产生 drwx--S--- 目录属主不可写 | build() 中生成 configure 后移除 `umask 077`（E114 方案） | conan create G2 PASS |
| C3 | CLI 工具包缺 commands.json 声明 | （预期 L0k 拦截） | CI L0k/R38 要求 application 包软件级 commands.json | 软件级 `archives/r/redir/commands.json`（name/type=tool/versions.ref 对齐） | 文件就位，commit 后由 R38/L0k 复验 |
| C4 | CLI 工具 test_package 无法 CMake find_package | 模板默认 CMake lib 消费方式不适用（无库产物） | redir 是纯 CLI，未生成库文件 | test_package 改为 VirtualRunEnv + `/bin/sh test_redir.sh <abs redir>`，用绝对路径避免 PATH 依赖 | test_package L1 实际运行通过 |
| C5 | E2E 消费者验证监听连接失败 | `Connection refused`：redir listener 未起来 | 上游 CLI 语法要求 `[SRC]:PORT` 必须带冒号（`parse_ipport` 对无冒号参数返回 -1） | 测试脚本传 `127.0.0.1:<port>` 格式 | E2E round-trip 通过 |

## 四范围查重

| 候选 | 正式 doc/ | graph/ | drafts/ | 错误模式 | 覆盖判定 |
|------|-----------|--------|---------|----------|----------|
| C1 | doc/E443.md、doc/E337.md | E443、（abiword E-family） | DRAFT-10251-libnfc-tools-automake-*.kv | automake/aclocal missing | 完整覆盖（E443 同类触发+方案，abiword-plugin-clarisworks 先例） |
| C2 | doc/E114.md、doc/E129.md | E114、E129 | — | subs1.awk Permission denied / mktemp | 完整覆盖（E114 根因+bypass 方案一致） |
| C3 | doc/E424.md | E424 | DRAFT-pico-sdk-cli-commands-json-r38 已提升为 E424 | L0k commands.json | 完整覆盖（E424 完全同场景） |
| C4 | doc/E298.md、doc/E428.md、doc/E529.md | E298、E428、E529 | — | VirtualRunEnv / bin 绝对路径 | 完整覆盖（E298/E428 同场景+方案） |
| C5 | — | — | — | 上游 CLI 参数语法 | 库特定（redir 自身用法），**不可跨库复用** → 噪声边界 |

## 七轴查重

- **exact_duplicate**: C2（E114/E129 同根因同方案）、C3（E424 完全同场景）→ 完整重复
- **causal_duplicate**: C1（E443 同根因：缺失 automake/libtoolize）
- **trigger_overlap**: C1/C4 与 E443/E298/E428 触发条件相同（archive 无 configure / test_package 无运行环境）
- **solution_overlap**: C1（tool_requires 引导 = abiword-plugin-clarisworks 已有方案）、C4（VirtualRunEnv + 绝对路径 = E298/E428 已有方案）
- **combination_novelty**: 无——所有修复均为既有条目方案的直接应用，无新组合
- **boundary_novelty**: 无——redir 为单文件 C 程序，无私有接口/特殊工具链/汇编依赖
- **test_migration_novelty**: 无——消费者 E2E 为 R34 常规要求（至少 1 个有业务意义的公开 API 调用）

关系字段:
- similar_to: E114, E129, E424, E443, E298, E428
- caused_by: []
- prerequisite_of: []
- conflicts_with: []

## 适用边界 / 反例

- C2（umask 077）适用于所有 autotools 项目在 HMDFS 上 config.status 建临时目录的场景；不适用于非 HMDFS 平台（无需处理）。
- C5 是 redir 库自身的 `[SRC]:PORT` 语法，属于库 API 用法而非 OHOS 平台知识，反例是任何不要求冒号参数的 CLI。

## 路径决定

**reuse_existing** — 完整重复（C2/C3）+ 因果重复（C1）+ 方案重叠（C4），且无跨库可复用的新增差异。
knowledge_gained 引用既有条目：E443/E337、E114/E129、E424、E298/E428。
按任务要求生成 `reuse_existing` 决定；若分析端复核认为 C4（纯 CLI application 包
test_package 全流程改造）值得沉淀，可下发 follow-up 扩展，当前轮不建草稿。