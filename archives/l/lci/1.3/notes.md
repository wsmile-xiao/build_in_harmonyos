# lci 1.3 OHOS PC adaptation notes

Date: 2026-09-21. Environment: HarmonyOS PC (aarch64), self-hosted toolchain
(clang 15.0.4, CMake 4.1.2, make 4.4.1), conan 2.29.1 with the repo's
`ci/conan/profiles/ohos-aarch64` profile. Worktree: `feat/lci-1.3`
(HEAD 59013dda, synced to origin/main before adaptation).

## Upstream identity

- Upstream: https://github.com/justinmeza/lci — **LOLCODE 1.3 language
  interpreter written in C**, MIT-family GPL-3.0-or-later. NOT the same
  project as the previously archived `chatziko/lci` 1.1 (pure lambda
  calculus interpreter, GPL-2.0) that shares this `archives/l/lci/`
  directory. The two projects are unrelated; software-level README and
  commands.json document both versions explicitly.
- Version: v1.3 tag, archive `lci-1.3.tar.gz` SHA256
  `56a77f8a19e6284868e609dad0e4f1d7c9fe59a61398e338726b58016c1eecef`
  (verified against the GitHub release tarball).

## Build

CMake >= 3.31 (upstream CMakeLists.txt requires 3.31). Single `lci`
executable linking only libm; no third-party dependencies. Builds cleanly
with clang 15 + the OHOS profile; `cmake_minimum_required(VERSION 3.31)`
is satisfied by the device's CMake 4.1.2.

`conanfile.py` is a CMake-based application recipe (`package_type =
"application"`), R38 CLI tool declared in software-level commands.json.
During conan-verify, G2 conan create passed from a clean build (G0-G4 + L2
all PASS); `package()` installs `bin/lci` and the COPYING license.

## Upstream tests (source-declared ledger)

Enumeration method: official v1.3 source tree, `test/1.3-Tests/` — each
leaf directory is one CTest case registered by `ADD_LOL_TEST` (macro in
`cmake/AddLolTest.cmake`, runs `testDriver.py` against `build/lci` with
`test.lol` + expected `test.out`, optional `test.in` / `-e` error mode).
`ctest -N` registers **319 tests total**.

Independent user test cases: **318** (319 registered minus 1 benchmark).
The single benchmark `0-Benchmarks/1-BFInterpreter` (a Brainfuck
interpreter in LOLCODE, listed per rule but not counted as an independent
user test case).

Category breakdown (independent cases): 1-Structure 17, 2-Comments 17,
3-Types 21, 4-Output 7, 5-Input 2, 6-Variables 16, 7-Operators 184,
8-Conditionals 10, 9-Functions 11, 10-Loops 9, 11-Unicode 9, 12-Arrays 15
= 318. Plus benchmark 0-Benchmarks 1.

Execution: `ctest --output-on-failure -j2` in the build tree →
**319/319 PASS (100%)**, including the benchmark. Full ledger is in
`reports/test-report.md`.

## test_package / consumer verification

`test_package/test.sh` runs the installed `lci` interpreter as a real
consumer (R34): executes two LOLCODE 1.3 programs (VISIBLE output +
arithmetic/variables) and checks observable output and exit codes, plus a
CLI help probe. Runs inside `conan create` via `VirtualRunEnv` + bash
wrapper (mksh cannot exec ELF).

## OHOS-specific notes

- /tmp is read-only on this device; all scratch files used `$TMPDIR`
  (`/storage/Users/currentUser/tmp`).
- No config.guess/sub issues: pure CMake project, no autotools step.
- Only C sources — the CXX probe is unnecessary but harmless; the
  upstream `project(lci)` defaults to enabling C and CXX; clang 15 rejects
  `-stdlib=libstdc++` from the default conan profile only if that profile
  is used — the repo `ohos-aarch64` profile (libc++17) is correct and
  builds fine.

## Knowledge candidate ledger（知识候选台账）

任务: lci 1.3 (justinmeza/lci, LOLCODE 1.3 interpreter), task_id
lci-1.3-r01-pc1-23-20260921T082905Z, task_type=知识库扩展.

### 候选观察（非噪声候选）

候选 C1 — "纯 CMake C 语言单可执行解释器零依赖直通"：
- 真实错误: 无（configure/make/ctest 全部一次通过，无编译/链接/测试错误）
- 根因: 不适用（无错误发生）
- 修复: 不适用
- 验证: cmake configure + make + ctest 319/319 PASS + conan-verify G0-G4 PASS
- 适用范围: 仅适用于 LOLCODE 场景本身，无通用可复用错误模式

候选 C2 — "上游 CMake ADD_LOL_TEST 宏注册 ctest 用例（testDriver.py 驱动）"：
- 真实错误: 无（319 例全部一次运行通过）
- 根因/修复: 不适用（无错误）
- 验证: `ctest -N` = 319，全量执行 319/319 PASS
- 适用范围: lci 自有的测试框架形态，属上游元数据形态而非 OHOS 平台知识；
  不构成跨库可复用的排错方案

候选 C3 — 基线噪声观察（非知识候选）: W3/CG 的 JC 门禁在 full 模式下命中
main 中已提交的其他库空标记文件（cloog/0.21.1/.build-closed、
cloog/0.21.1/.staging-verified、kics/2.1.20/.staging-verified，三者均为
空文件，SHA-256 = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855）。
按 SKILL 基线隔离规则完成隔离复验（index 级临时隔离 → W3 重跑通过 →
原样恢复，恢复后 SHA-256 与隔离前一致），不修改/提交/入库该基线文件。

### 四范围查重结果

| 范围 | 检索方式 | 结果 |
|---|---|---|
| 正式知识 (knowledge/doc/*.md) | grep lolcode/lci/interpreter | 无 LOLCODE 相关知识；E037/E049/E105 等为无关主题 |
| 知识图谱 (knowledge/graph/E*.kv + index.tsv) | grep lolcode/lci/ADD_LOL_TEST/ADD_TEST | 无 justinmeza/lci 相关条目 |
| 草稿 (knowledge/drafts/) | grep -il lolcode/lci | 仅 chatziko/lci 1.1 的 E565/E567（termio/TCGETA/TCSETA，musl ioctl 宏守卫）——属另一项目（λ演算解释器），与本 LOLCODE 库无关，且本库无该错误 |
| 元数据命名冲突 | archives/l/lci/ 软件级文件 | 现有 1.1 为 chatziko/lci（λ演算），本 1.3 为 justinmeza/lci（LOLCODE），已在软件级 README/commands.json 双注释说明 |

### 七轴查重

- exact_duplicate: false（不存在 LOLCODE 解释器适配条目）
- causal_duplicate: false（无同类根因条目）
- trigger_overlap: false（检索关键词无重叠命中）
- solution_overlap: false（无既有解决方案）
- combination_novelty: false（无组合创新的需求——适配零修改）
- boundary_novelty: false（无平台边界新发现）
- test_migration_novelty: false（上游测试 319 例原生 ctest 直接运行，无迁移改造）

### 关系字段

similar_to: none；caused_by: none；prerequisite_of: none；conflicts_with:
chatziko/lci 1.1 仅共享目录名，软件级文件已双向注明，无知识图冲突。

### 路径决定

**path_a_no_knowledge** — 本库适配全程零错误、零补丁、零配置修改，
无已验证、可跨库复用的新增知识；候选 C1/C2 均不满足路径 B 的
"新增差异已由真实日志验证并可跨库复用"条件。按任务规则不硬凑路径 B，
不建草稿；PR 前缀按任务头 initial_pr_prefix=【知识库扩展】。
---

**编译结束**: 2026-09-21 17:20
**最终状态**: published
