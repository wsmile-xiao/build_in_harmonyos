# 知识候选台账 — random123 1.14.0（task random123-1.14.0-r01-pc5-13）

## 候选 C1：lang-preflight 对仅有 GNUmakefile 的 C/C++ 库误判 mixed（高价值）

- 真实错误：`ohc-run.py lang-preflight random123 1.14.0 --src <src>` exit 2，
  `detected_language=mixed（build_system=none）`，自动写终态 env_unsupported。
- 根因：random123 顶层只有 GNUmakefile（header-only，无 CMakeLists.txt / Makefile /
  configure.ac），`_manifest_scan` 的 names 检查含 `"Makefile"` 精确匹配但不含 `GNUmakefile`
  → m_lang=None；`_source_stats` 得 cpp:25 / c:11（bash 不计），cpp 主体占比 25/36=69.4%
  < 70% 阈值 → 落入 generic 分支「无 manifest 且主体占比 <70% → mixed」。
- 修复/处理：按 SKILL R47 边界规则（C/C++ 混编按主体判不算 mixed，E13；c↔cpp 兼容族
  不迁移，_COMPAT_FAMILY={"c","cpp"}）判定为 cpp，继续主流程，不触发迁移。
- 验证：.ohc-logs/lang_preflight_analysis.log（SHA-256 12c55dc7…）；cpp 源码 25 个 vs c 11 个
  全部为 C/C++ 族；random123 全量编译/测试在 cpp 口径下完成。
- 适用范围：所有仅有 GNUmakefile（无 CMake/Makefile/autotools manifest）的 C/C++ 库；
  cpp 主体占比落在 [50%, 70%) 且无 manifest 的 C/C++ 混编库。
- 四范围查重：正式知识 knowledge/graph/ 无命中（grep random123/lang_detect 0 条）；
  图谱 index.tsv 无 GNUmakefile+语言预检条目；草稿仅有 DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect
  （emio：辅助 Cargo.toml 干扰 manifest 扫描优先级，触发机制不同）；文档无覆盖。

## 候选 C2：Conan 2 header-only 配方 package() 标准写法（中价值）

- 真实错误：conan-verify G2 两次失败 —— `'Random123Conan' object has no attribute 'copy'`
  （Conan 2 无 self.copy，需 `from conan.tools.files import copy` 并调用 `copy(self, ...)`）；
  随后 `copy() 'src' and 'dst' arguments must have different values`（src/dst 用相同相对串触发）。
- 根因：模板配方假设 autotools；header-only 库需直接拷贝 include 树；Conan 2 API 与 1.x 差异。
- 修复：`copy(self, "*", os.path.join(self.source_folder, "include"),
  os.path.join(self.package_folder, "include"), keep_path=True)`，package_type="header-library"。
- 验证：conan-verify G0-G4/L2/L4/L5 全 PASS；test_package 消费者测试通过；独立消费者程序编译运行通过。
- 适用范围：所有无 CMake 的 header-only 库（GNUmakefile 直拷头文件型）。
- 四范围查重：E321（martinmoene lite 系）覆盖 CMake INTERFACE 消费型 header-only，非纯拷贝型；
  E035 header-only-install 无 Conan 2 细节；无 GNUmakefile 纯拷贝型 Conan 2 配方条目。

## 候选 C3：ut_uniform_IEEEkat 在 ARM/FMA 平台为上游已知失败（低价值/噪声级记录）

- 现象：ut_uniform_IEEEkat exit 1，MISMATCH 打印的 computed/reference 21 位有效数字相同。
- 根因：上游头注释明确记载「likely to fail on … newer ARMs … Failures in these cases are
  *not* necessarily problematic」——x86-64 严格 IEEE 参考值在 FMA 融合的 ARM 上不逐位匹配。
- 处理：如实记录 13 项独立用例中 1 项上游已知平台失败；-ffp-contract=off 复测仍不逐位一致；
  不修改上游。属上游文档已覆盖，不建草稿。

## 七轴查重（针对候选 C1/C2 与既有条目）

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | false | 无 random123/GNUmakefile+lang 条目 |
| causal_duplicate | false | emio 草稿根因=辅助 Cargo.toml manifest 优先级；本候选根因=无 manifest+GNUmakefile 未识别+69%<70% |
| trigger_overlap | 部分 | 都触发 lang-preflight/R47，但触发机制不同（manifest 冲突 vs 无 manifest 边界） |
| solution_overlap | 部分 | 都按 R47 复核判 cpp；emio=顶层 manifest 复核，本候选=主体占比+兼容族判定 |
| combination_novelty | true | GNUmakefile-only + lang_detect 无 manifest 边界（69% vs 70%）组合未见既有条目 |
| boundary_novelty | true | GNUmakefile 未列入 manifest 识别集合；50-70% 主体占比边界行为首次记录 |
| test_migration_novelty | false | 不涉及测试迁移 |

## 路径判断

- C1：已验证、可跨库复用、查重未命中/部分覆盖且存在新增差异 → **路径 B（知识库扩展），
  建同 stem 草稿** DRAFT-random123-1.14.0-lang-preflight-gnumakefile-mixed.kv/.md。
- C2：同 PR 内并入草稿的 Conan 2 header-only 配方要点（solution 部分与 E321 有区分度）。
- C3：噪声级，仅台账记录，不建草稿。
- 决定：`new_draft`（C1+C2 合并为一条草稿，同 stem .kv/.md 配对）。
