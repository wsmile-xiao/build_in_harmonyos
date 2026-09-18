# vdt 0.4.6 知识候选台账（knowledge_candidate_ledger）

任务: vdt-0.4.6-r01-pc3-7-20260917T182015Z · task_type: 知识库扩展
查重范围: knowledge/doc/（正式 E###.md）、knowledge/graph/（E###.kv + index.tsv）、
knowledge/drafts/（草稿）、SUMMARY.md 四范围

## 候选 1：CMake <3.5 minimum_required 与 CMake 4.x 不兼容（vdt 声明 3.2）
- 真实错误: CMake Error: "Compatibility with CMake < 3.5 has been removed"（configure 阶段）
- 根因: CMake 4.x 移除了对 3.5 之前版本的兼容模式；vdt CMakeLists.txt 顶层声明
  cmake_minimum_required(VERSION 3.2)
- 修复: conanfile.py generate() 中 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"`
  （cache_variables 走 -D 命令行，在 cmake_minimum_required 解析前生效）
- 验证: conan create rc=0（W3 本地 CI 通过）、手动 `cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5` 配置成功
- 适用范围: 所有 cmake_minimum_required(<3.5) 的库在 CMake 4.x（OHOS SDK 当前 4.1.2）下交叉编译
- 查重: **完全重合（exact_duplicate）** — E103（error_signature/root_cause 逐项一致，
  fallback 即 CMAKE_POLICY_VERSION_MINIMUM）、E187（add-cmake-flag 同方案）、
  DRAFT-E321-cmake4-policy-version-minimum（conanfile cache_variables 写法完全一致）已有
  → **reuse_existing**（复用 E103/E187/DRAFT-E321，不建新草稿）

## 候选 2：github.com 不可达时 conan 源码下载走 gh-proxy 镜像
- 真实错误: conan create source() 阶段 `ConnectTimeoutError github.com:443`（conan 重试仍失败）
- 根因: 执行机到 github.com 网络不可达；gh-proxy.com 可达且内容 SHA-256 与官方源逐字节一致
- 修复: conandata.yml 临时写 URL 列表 `[gh-proxy 镜像, 官方 URL]` 供本地 W3 验证；
  提交前恢复官方单 URL（PF7 源 URL 闸禁 gh-proxy 域），CI 构建时由 build_and_test.sh
  自动 mirror fallback 改写为镜像列表
- 验证: gh-proxy 下载 sha256=1820feae...（与官方一致）；conan create rc=0；提交 conandata 无 gh-proxy 残留
- 适用范围: 官方源网络不可达的 CI/执行机环境（通用基础设施行为，非 vdt 特有）
- 查重: **部分覆盖（solution_overlap）** — E415（CI Mirror-fallback 改写 conandata 需恢复、
  gh-proxy、逐字节一致核验）已覆盖核心方案与验证命令；本轮为"本地 W3 预绕行"的应用实例，
  无新增跨库可复用差异 → **reuse_existing**（复用 E415，不建新草稿）

## 候选 3：JC junk_check 命中 main 上其他库既有运行时状态文件（cloog .build-closed/.staging-verified）
- 真实错误: W3 本地 CI `JC_RESULT=fail`，`archives/c/cloog/0.21.1/.build-closed`、`.staging-verified`
  被拦（full 模式 git ls-files 扫描）
- 根因: main 上 cloog PR(906cc59ae7) 将运行时状态文件混入归档；当前库 W3 在本地以
  full 模式（无 origin/main diff 时回退）整仓扫描命中，非 vdt 引入
- 修复: 按基线隔离规则 `git rm --cached` 临时隔离 → 复跑 W3（pass）→
  `git restore --staged` 原样恢复；pre/post sha256 均为 e3b0c442...（空文件），
  vdt diff/staged/PR 不含该路径（隔离审计见 notes.md）
- 验证: 隔离后 junk_check Junk Files: 0，W3 L0 pass；恢复后 git status 该路径无变更
- 适用范围: 本地 W3 full 模式扫描受其他库已提交基线文件干扰的通用操作（属流程/操作规范，
  非跨库编译知识；CI prdiff/incremental 模式天然不受影响）
- 查重: **无既有条目直接覆盖**（E291 是 graph validate 基线阻塞，非本案）——但该信息
  属 oh-executor 基线隔离流程规范，已在任务级固定规则中固化，不足以作为跨库知识草稿
  → **reuse_existing（流程规范），不建新草稿**

## 候选 4：vdt 公开 API 命名为 fast_exp/fast_sinf（非裸 exp/sin）
- 真实错误: test_package 首版写 vdt::exp 编译报 `no member named 'exp'`（consumer 侧）
- 根因: vdt 库按函数名省略 fast 前缀约定 fast_*；数组签名 expv/sinv 才对导出声明的符号
- 修复: consumer.cpp 改用 vdt::fast_exp/vdt::fast_isqrt/vdt::expv（对照 include/vdt/*.h 真实声明）
- 验证: consumer_probe 12/12 PASSED
- 适用范围: 仅 vdt 库特有 API 命名（库文档已声明），无跨库复用价值
- 查重: **非知识候选**（库特定命名，不足以形成独立可复用条目）

## 七轴查重结论
| 轴 | 结论 |
|----|------|
| exact_duplicate | 候选1 与 E103/E187 逐项一致；候选2 方案与 E415 一致 |
| causal_duplicate | 候选1 根因（CMake 4.x 移除 <3.5 兼容）与既有条目同根因 |
| trigger_overlap | 候选1 触发（configure 阶段 cmake_minimum_required 报错）覆盖 |
| solution_overlap | 候选1/2 解与 E103/E187/E415/DRAFT-E321 完全重叠 |
| combination_novelty | 无新组合（vdt 为常规 CMake 库 + 无依赖） |
| boundary_novelty | 无（vdt 0.4.6 在既有适配模式边界内） |
| test_migration_novelty | 无（上游测试 12/12 原生运行，无迁移差异） |

## 关系字段
- similar_to: E103, E187, E415, DRAFT-E321
- caused_by: （无新条目）
- prerequisite_of: （无）
- conflicts_with: 无

## 路径决定
- reuse_existing: **是**（候选全部被既有条目覆盖，无新增差异）
- new_draft: **否**（不满足"已验证、可跨库复用且查重未命中/部分覆盖并存在新增差异"）
- path_a_no_knowledge: 否（既有知识可复用，走路径 A 语义）
- 结论: **reuse_existing → 路径 A**；PR 前缀按任务头 initial_pr_prefix 使用【知识库扩展】