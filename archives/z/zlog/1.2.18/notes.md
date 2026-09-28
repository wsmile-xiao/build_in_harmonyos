# zlog 1.2.18 — adaptation notes (R02 归档收敛)

## Source（官方归档来源，不提交上游源码树）
- Upstream: https://github.com/HardySimpson/zlog
- Tag: 1.2.18
- Official tarball: https://github.com/HardySimpson/zlog/archive/refs/tags/1.2.18.tar.gz
- SHA-256: `3977dc8ea0069139816ec4025b320d9a7fc2035398775ea91429e83cb0d1ce4e`（与任务头 `source_sha256` 一致）
- 获取方式：`conanfile.py source()` 经 `conandata.yml sources."1.2.18"` 从官方归档下载并校验 SHA-256（`get(..., strip_root=True)`）；
  不再使用仓库内 `src/` 本地树（R02 已移除 vendored 上游源码树，归档收敛到 ARCHIVE-SPEC v3.0）。

## Build system
- CMake（上游 `CMakeLists.txt` + `src/CMakeLists.txt`），产物 `libzlog.so`（shared）与 `libzlog.a`（static）。
- `generate()`：`UNIT_TEST=OFF`、`CMAKE_POSITION_INDEPENDENT_CODE`（fPIC）、`CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游
  `cmake_minimum_required 2.8.5` 在 CMake ≥ 3.27 被移除，抬升策略下限）、`os=OHOS` 时 `ZLOG_OHOS_BUILD=ON`。
- `package_info()`：`cpp_info.libs=["zlog"]`，`system_libs=["pthread","m"]`（Linux/OHOS/FreeBSD）。

## HarmonyOS PC arm64 adaptation
- Conan profile: `ci/conan/profiles/ohos-aarch64`；工具链 clang-15（target `aarch64-linux-ohos`）。
- Patch `0001-fix-ohos-build.patch`（在 `conandata.yml patches` 声明，`build()` 经 `apply_conandata_patches` 应用）：
  1. `cmake_minimum_required(VERSION 2.8.5)` → `3.5`；
  2. `src/version.h` 版本字符串 `"1.2.12"` → `"1.2.18"`（与 tag 一致；上游内部字符串与 release tag 不同步，见 Known observations）。
- 补丁 hunk 在 R02 收敛后仍可应用到官方归档源码（R02 用官方 tarball 实证验证）。

## Verification
- `conan create`（`-pr:h=ci/conan/profiles/ohos-aarch64`）：PASS（R02 重跑）。
- L1 `test_package/test_zlog`：编译并运行，输出 `test_zlog:OK`，`zlog_init_from_string` / `dzlog_init` 流程均验证。
- 上游测试三步法（R51）与本轮鸿蒙特有测试台账：见 `notes.md` 测试申报表与本轮回报（`reports/`）。

## Recipe notes
- 无第三方 Conan 依赖（纯 C）；`test_package` 使用 CMakeDeps，`find_package(zlog)` + `zlog::zlog` 可解析。
- 纯库包（无 bin/ 可执行产物需要声明 R38 commands.json；`zlog-chk-conf` 在上游构建为测试辅助，不随库安装）。

## Known observations
- 上游 `Changelog` 只到 1.2.17，`src/version.h` 内部为 "1.2.12"，而 tag 为 1.2.18 — 上游内部版本字符串与 release tag
  不同步；本地发布包以官方 tag 为准，补丁将版本字符串与 tag 对齐。
- Arbiter: r01 声称的 `reports/conan-verify-report.md` 已实际生成并纳入本 PR 文件列表（R02 修正）；reports/ 下日志均带
  SHA-256 可在回报中追溯。
---
**编译结束**: 2026-09-21（R02 返工轮）
**最终状态**: built（R02 本地门禁通过后远端交付，PR #9001 更新）

## 上游测试申报表（R51，R03 重数修正；官方归档 test/ 目录 27 个 `test_*.c` 入口）

> R03 修正说明：R02 正文测试统计与所附 ledger 冲突（分析端核出），本轮以**实际重跑结果**为准重新出具台账，
> 统计口径与 `reports/upstream-tests-r03.log`（逐入口 ledger，SHA-256 见回报）完全一致；带参数入口一律按官方参数运行。

- 清点与注册规则：`test/` 下 `test_*.c` 共 **27** 个；`test/makefile` 的 `exe` 列表注册全部 27 个；
  `test/CMakeLists.txt` 通过 `aux_source_directory` 自动注册，`not_auto_add_test` 排除
  hello/bitmap/hex/leak/press_*×4/syslog/longlog 共 11 个，再以 `add_test` 补回 hello/longlog/bitmap。
- 运行方式：官方补丁源码经 OHOS clang-15（`--target=aarch64-linux-ohos`）构建 `libzlog.so/a`，27 个入口
  全部编译通过并实际运行（本机为 aarch64 OHOS PC，OHOS 二进制可原生执行）；带参数入口按官方/CMake 参数运行。
- 实测统计（实际运行，与 ledger 一致）：**通过 25 / 失败 1 / 受控观察 1 / 未运行 0**。
  - 单元测试 17 个：16 通过 + test_conf2 失败（exit 255）；
  - 集成测试 5 个：4 通过（hello/longlog 2222/pipe/syslog）+ test_multithread 受控观察（timeout 25s rc=124）；
  - 其他测试（压力）5 个：全部通过（press_write/press_write2/press_zlog/press_zlog2 各 `1 1 3`、press_syslog `1 3`）。

| 入口 | 结果 | 证据 |
|------|------|------|
| test_buf / test_category / test_conf / test_default / test_enabled / test_hashtable / test_hello / test_init / test_level / test_mdc / test_pipe / test_profile / test_record / test_syslog / test_tmp | pass（exit 0，真实输出） | 见 `reports/upstream-tests-r03.log`（逐入口退出码+首行输出） |
| test_bitmap 0xaa55 0x66 / test_hex test_hex.conf 3 / test_leak 5 / test_longlog 2222 | pass（exit 0，带官方参数） | 同上 |
| test_press_write 1 1 3 / test_press_write2 1 1 3 / test_press_zlog 1 1 3 / test_press_zlog2 1 1 3 / test_press_syslog 1 3 | pass（exit 0，压力入口限定参数后自然终止） | 同上 |
| test_conf2 | fail（exit 255，`zlog_init` 失败） | 内嵌配置经 `zlog-chk-conf` 实证：`[formats] null = "%n"` 解析失败（`the 1st char of pattern is not "`），为上游该配置与 1.2.18 解析器的真实行为；非本库适配缺陷，须上游侧处理 |
| test_multithread | 受控观察（无稳定终止条件，timeout 25s rc=124） | `while(1)` 多线程持续运行（`NB_THREADS` 固定、无官方数量/时长参数可终止），限定 `timeout 25s` 观察运行正常输出多线程日志后超时结束；**不改写为自然 exit 0**，不计入通过/失败 |

- 阻塞归属：test_conf2 = 上游用例问题（当前库非适配缺陷，最小复现证据见 `zlog-chk-conf` 输出）；test_multithread = 持续运行压力入口（无自然终止，
  按 SKILL 受控完成规则处理并如实记录）。恢复条件：前者由上游修正配置；后者如需计数验证需上游提供终止参数。

## 知识路径判定（R03 更新；knowledge_governance: executor_local_required）

- **外置只读稀疏快照（R03 task_id 专用）**：
  - 绝对路径：`/storage/Users/currentUser/.ohpc-executor/zlog-r02/knowledge-snapshot-zlog-1.2.18-r03`
  - 远端：`https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git`，ref `main`，HEAD commit `48d9cee6844d0fca1f25e86c2df1293b904855d8`
  - 稀疏目录：`knowledge`（`git clone --no-checkout --sparse --depth 1` + `sparse-checkout set --cone knowledge`）；建立后 `chmod -R a-w` 只读审计
  - 扫描范围：正式 `knowledge/graph/E*.kv`（540）+ `knowledge/doc/E*.md`（540）+ 根目录 `DRAFT-*` 配对（6 对）+ `knowledge/drafts/DRAFT-*.kv`（978）
- **查重结论（本轮候选 → 判定）**：
  - C1 `cmake_minimum_required(<3.5)`（CMake≥4.x 拒绝）→ **等价命中** `DRAFT-E321-cmake4-policy-version-minimum.kv`，逐字段适用性通过 → 沿用 r02 路径 A（reuse_existing）
  - C2 补丁缺尾换行（`git apply: corrupt patch`）→ **等价命中** `DRAFT-no-tail-newline-hunk-unappliable.kv` → 沿用路径 A（reuse_existing）
  - C3 「PR 测试统计与 ledger 不一致/高估被分析端核出并纠正」（R03 本轮经验）→ **无等价命中**（E215/E220/E231/E234 与既有统计类草稿均不覆盖该 error signature），且具跨库复用价值 → 按任务允许"评估沉淀配对草稿"，在本库 `knowledge/drafts/` 创建同 stem 配对草稿：
    - `DRAFT-zlog-1.2.18-test-statistics-ledger-consistency.kv`（SHA-256 `110ff04c…`）
    - `DRAFT-zlog-1.2.18-test-statistics-ledger-consistency.md`（SHA-256 `f21ab1b1…`）
    - 字段一致性/成对/哈希审计已完成，未写正式 E###、未改其他库目录
- **路径结论**：C1/C2 路径 A（reuse_existing）沿用；C3 新增配对草稿（路径 B 相关的知识沉淀），随本 PR 交付（`delivery_allowed_paths` 允许 `knowledge/drafts/DRAFT-zlog-1.2.18-*`）；`issue_action: none` 不变。

## R02 知识路径判定（历史，已并入 R03 复核）

- **外置只读稀疏快照**（task_id 专用，位于 Git worktree 之外，不属本库 diff/暂存/提交/PR）：
  - 绝对路径：`/storage/Users/currentUser/.ohpc-executor/zlog-r02/knowledge-snapshot-zlog-1.2.18-r02`
  - 远端：`https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git`，ref `main`，HEAD commit `48d9cee6844d0fca1f25e86c2df1293b904855d8`
  - 稀疏目录：`knowledge`（`git clone --no-checkout --sparse --depth 1` + `sparse-checkout set --cone knowledge`）
  - 只读审计：建立后 `chmod -R a-w`；扫描范围：正式 `knowledge/graph/E*.kv`（540）+ `knowledge/doc/E*.md`（540）+ 根目录 `DRAFT-*` 配对（6 对）
- **查重结论（本轮候选 → 命中）**：
  - C1 `cmake_minimum_required(<3.5)` 在 CMake≥3.27/4.x 被拒 → **等价命中** `DRAFT-E321-cmake4-policy-version-minimum.kv`（error_signature/root_cause/approach/affected_scope 逐字段适用性已验证，见回报 evidence）
  - C2 补丁缺尾换行（`git apply: corrupt patch at line 10` / `Hunk 1 FAILED`）→ **等价命中** `DRAFT-no-tail-newline-hunk-unappliable.kv`（无尾换行文件末行 hunk 不可应用；本轮补丁文件自身缺尾换行同属该类，修复为带上下文规范补丁后双工具实证可应用）
  - C3 归档 src/ 树未登记点文件被 JC5 拦截 → 归档形态/共享框架白名单问题，**不走路径 B**（任务边界：归档收敛经验不得改写既有草稿）
  - C4 上游 version.h 内部版本与 tag 不同步 → zlog 特有观察，非跨库可复用新知识
- **路径结论：A（reuse_existing）**，`knowledge_decision: reuse_existing`；不创建草稿、不写正式 E###、不修改其他库目录。

## R02 归档收敛说明
- 移除 vendored 上游源码树 `archives/z/zlog/1.2.18/src/`（上游 tarball 自带未登记点文件 `.clang-format` 等一并移除，
  JC5 红灯消除）；源码改由配方从官方归档获取并校验 SHA-256。
- 补齐软件级 `archives/z/zlog/README.md`、`archives/z/zlog/manifest.yaml`。
- 版本级 `manifest.yaml`/`notes.md` 与 conandata.yml 逐字段一致；补丁重写为带上下文规范格式，
  已在官方归档上经 `git apply --check` 与 `patch --dry-run` 双实证可应用。
---

**编译结束**: 2026-09-21 22:05
**最终状态**: built
