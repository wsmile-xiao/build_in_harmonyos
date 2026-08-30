# 草稿：ankerl-unordered-dense 4.5.0 OHOS header-only 库的 finish 交付边界与平台能力边界

> 配对文件：`DRAFT-ankerl-unordered-dense-4.5.0-ohos-header-only-finish-boundaries.kv`（同 stem，逐字段对应）

> 状态：DRAFT（未分配 E### 编号，待主审 `graph add` 定稿）。
> 来源轮次：ankerl-unordered-dense 4.5.0 r03（Path B 知识草稿），executor pc3-30。
> 证据根目录：`/storage/Users/currentUser/tmp/ankerl-r02/`（r02 终态报告已回传确认）。

## 1. 问题（What）

header-only Conan 库（`package_type=header-library`）在 OHOS 适配跑 `finish` 时，
三类现象会被误判为当前库失败或阻塞，实际分别是「交付标记 N/A」「平台 libc++
能力边界」「框架预下载 URL 改写缺陷」：

1. **finish Step6/10 归档校验与 Step10 就绪预检警告**：缺 `packaging/` 目录、
   `release`/`debug` tar.gz、`reports/test-report.md`、`packages/<lib>/<ver>/.staging-verified`。
   对 header-only 包这些交付物**本就不存在**（无二进制、无 tar.gz 可打包），
   警告属 N/A 而非缺陷，不应触发本库返工，也不应阻塞本地交付预览。
2. **上游 meson 测试链接失败**：`ld.lld: undefined symbol: std::experimental::
   fundamentals_v1::pmr::get` 等 —— OHOS sysroot 的 libc++ 未提供
   `std::experimental::pmr`（fundamentals v1 poly-allocation 设施）。引用 pmr 的
   单元测试文件在 OHOS 目标下无法链接，属**平台能力边界**，不是当前库配方错误，
   也不应作为 OHOS PR 门禁；消费者侧验证由 Conan `test_package` 覆盖。
3. **finish/W3 阶段 conandata.yml 被改写**：框架预下载（predl）把 sources.url
   改写为 `file://./.build-cache/predl_cache/<hash>_v<ver>.tar.gz` 相对 URL，
   当 finish 以**相对** `--project-dir .` 启动时 `CI_REPO_ROOT=.`，conan 把相对
   file URL 解析到文件系统**根目录**（`/.build-cache/...`）而非 worktree，
   导致 W3 失败。缓存 tarball 的 sha256 与官方源一致，仅 URL 形态错误。

## 2. 根因（Why）

1. finish 的 Step6/10 就绪清单面向**二进制交付**设计（packaging + 双 arch tar.gz +
   staging 标记），未对 header-only 包类型做条件分支；header-only 的合法产物只有
   `include/` 头文件，因此清单命中为「缺失」而非「通过」。
2. OHOS aarch64 sysroot 的 libc++（clang-15 HNP 工具链 `/data/service/hnp/bin/`）
   的 experimental 设施只覆盖到部分 TS 组件，`<experimental/memory_resource>`
   （pmr）未包含。上游测试对 pmr 的引用是**测试代码**的依赖，不是库头文件
   （`unordered_dense.h` 本身不使用 pmr）的依赖，故库本体不受影响。
3. 框架预下载改写逻辑以 `CI_REPO_ROOT` 拼接相对路径；conan 对 `file://` +
   相对路径的解析基准是**当前工作目录/根**而非 `CI_REPO_ROOT`。finish 以相对
   `--project-dir .` 启动时该变量退化为 `.`，触发根目录解析。

## 3. 方案（How）

1. **header-only 交付边界**：header-only 库的 finish 中，Step6/10 对
   `packaging/`、release/debug tar.gz、`.staging-verified`、`test-report.md`
   的缺失按 N/A 记录（notes.md 注明「header-only，无二进制交付物」），
   不返工、不伪造产物；本地交付预览与审计以「G1-G4 + W3 + W2 + W4」为准，
   不要求这些二进制交付标记。
2. **pmr 平台边界处理**：上游含 pmr 测试的库，OHOS 适配时
   (a) 库头文件若引用 pmr → 记录为平台阻塞，回报分析端（属强制依赖缺失）；
   (b) 仅测试文件引用 pmr → 在**临时诊断副本**中排除 pmr 测试文件后实测
   其余测试，OHOS PR 门禁改用 Conan `test_package` 消费者验证；
   报告中必须写明排除文件清单、排除仅在临时副本（worktree 源码零修改，
   `patches: {}`）以及 doctest/ctest 实测计数。
3. **predl 相对 URL 规避**：`finish` 一律以**绝对路径** `--project-dir
   <worktree 绝对路径>` 启动，使 `CI_REPO_ROOT` 为绝对路径；W3 的
   `build_and_test.sh` 由框架以 `CI_REPO_ROOT=<绝对 worktree>` 调用。
   若发现 conandata.yml 被改写为相对 `file://`，先核对缓存 tarball sha256
   与官方源一致，再恢复官方 HTTPS URL 后用绝对路径重跑 finish，
   不得直接绕过框架校验。

## 4. 验证（Verification）

全部来自 r02 任务（task_id `...r02-finish-w4-delivery-preview-pc3-30-20260829T132729Z`）
实际执行，日志在 `/storage/Users/currentUser/tmp/ankerl-r02/`：

| 验证项 | 结果 | 证据 |
|--------|------|------|
| finish 自然终态（绝对 --project-dir） | banner `EXIT_REASON: finish_success, EXIT_CODE: 0`；W3 阻塞门禁 PASS | `finish.log`（sha256 `cf225e96…b8361`） |
| 绝对路径下 W3 conandata 未被改写为相对 file:// | `.ci-result.json exit_code=0` | `archives/a/ankerl-unordered-dense/4.5.0/.ci-result.json`、`reports/w3-local-ci.log` |
| pmr 排除后上游 doctest 实测 | 320 用例 / 1804141 断言 / 0 failed / 23 skipped，`Status: SUCCESS!`，exit 0 | `upstream-unit-run.log`（sha256 `9fb55725…b73c`） |
| pmr 排除取证（仅临时副本） | 临时副本 `test/meson.build` 61/63 列出，排除 `unit/pmr.cpp`、`unit/pmr_move_with_allocators.cpp`；worktree 源码未动 | `meson-pmr-exclusion.log`（sha256 `0f33b705…60a6`） |
| OHOS 消费者验证 | `conan test` 实跑 OHOS aarch64 二进制，22 项 CHECK，`all assertions OK`，exit 0 | `conan-test.log`（sha256 `1c35e824…d705`） |
| 相对路径首次失败的对照证据 | 根目录 `/.build-cache/predl_cache/fb36b438_v4.5.0.tar.gz` 被 conan 引用（W3 首错） | r02 报告 `external_first_errors_and_isolation.predl_relative_url` |

## 5. 适用边界（Scope / Limits）

- 适用：`package_type=header-library` 的 Conan 配方在 OHOS aarch64（clang-15
  HNP 工具链）跑 `finish`/W3 的场景；上游测试引用 `std::experimental::pmr` 的场景；
  框架 predl 缓存改写 conandata 的场景。
- 不适用：二进制库（packaging/tar.gz/staging 标记仍然必须，本条目不得用于豁免）；
  库头文件本体依赖 pmr 的场景（那是平台阻塞而非测试排除）；非框架 predl 的
  手写相对 file:// URL（应按代码规范直接改绝对/HTTPS）。
- 本条目不改变 `finish` 门禁的阻塞级别定义，只定义「缺失项在 header-only 下的
  N/A 定性」与「平台能力边界 vs 配方错误」的判别。

## 6. 查重差异（Dedup diff）

（完整查重命令与命中清单见 `duplicate-check.log`，摘要如下）

| 既有条目 | 覆盖内容 | 与本草稿差异 |
|----------|----------|--------------|
| E291 | graph validate 基线问题导致 finish Step6 顶层 rc=1 | 根因是知识图谱校验基线，不含 header-only 交付标记 N/A 定性 |
| E213/E214（E291 提及） | 既有正式条目 non-standard fields | 与本条目三个知识面均无交集 |
| DRAFT-jc-full-scan-baseline-noise-exemption | JC 三向 diff 为空回退 full 扫描命中他库基线文件 | 覆盖 JC 扫描层，不覆盖 Step6/10 交付清单与 pmr/predl |
| DRAFT-jc6-origin-main-stale-ref | origin/main 陈旧 ref 导致 full 模式 | 同上，JC 层 |
| DRAFT-2045 / E327-draft | restinio 编译/finish 外层警告 | E327 提到 Step8 缺 test-report.md/packaging 但归因为「禁提交未补」，未定性 header-only N/A |
| E212（任务文本称 ci-predl-regex） | 实为 hmmac 安全标签阻止用户路径 .so dlopen（index.tsv 核对） | 与 predl file:// 解析无关；任务引用编号与索引不符，已在报告说明 |
| pmr/std::experimental 相关 | knowledge/** 零命中 | 无既有覆盖 |
| predl 相对 file:// 解析 | knowledge/** 零命中 | 无既有覆盖 |

同 stem 检查：`knowledge/drafts/` 无 `ankerl-unordered-dense-4.5.0-ohos-header-only-finish-boundaries`
（0 命中），不冲突。
