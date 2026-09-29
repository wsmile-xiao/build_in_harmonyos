# maskedvbyte 0.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4 (aarch64 OHOS)
- 状态: built

## 编译步骤

```bash
# init-build（tag v0.1.0 tarball，官方 GitHub 源）
python3 scripts/ohc-run.py init-build maskedvbyte 0.1.0 \
  --url=https://github.com/lemire/MaskedVByte/archive/refs/tags/v0.1.0.tar.gz

# 语言预检（R47）：detected=c，task=cpp，兼容族通过
python3 scripts/ohc-run.py lang-preflight maskedvbyte 0.1.0 --src $BUILD_SRC_DIR

# 驱动构建：configure(cmake) → make → staging install（DESTDIR 模式）
python3 scripts/ohc-run.py build maskedvbyte 0.1.0

# conan 配方（CMake 模板）+ 验证（G1-G4 + L2/L4/L5 全绿）
python3 scripts/ohc-run.py conan-init maskedvbyte 0.1.0
python3 scripts/ohc-run.py conan-verify maskedvbyte 0.1.0

# finish（W2/W3）：本地 CI 模拟通过（隔离其他库基线 junk 后）
python3 scripts/ohc-run.py finish maskedvbyte 0.1.0 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `src/varintdecode.c:24: fatal error: 'sse_to_neon.h' file not found` | 上游 v0.1.0 tag（及 master）在 `__aarch64__` 分支引用 `include/sse_to_neon.h`（README/CMakeLists 均声称存在），但该文件从未出现在仓库历史与任何 release tarball 中，AArch64 首建即缺头 | 新增自包含 `include/sse_to_neon.h` 补丁：直接基于 `<arm_neon.h>` 实现 varintdecode.c 实际使用的 SSE2/SSSE3/SSE4.1 内建（`__m128i=int32x4_t`；PSHUFB 用 `vqtbl1q_u8`+`0x8F` 掩码；per-lane 移位用 `vshlq` 负计数；PMOVMSKB 用 vshr+加权水平加；`_mm_cvtepi8_epi32` 用 `vmovl_s8`+`vmovl_s16`），保持 Intel 拼写免改库体，用上游 unit.c + ctest 验证语义 |
| 2 | conan create 中补丁未生效 | 初版 conandata.yml 补丁声明格式不符合仓库惯例（`"1":` dict 形式），且 finish refresh-patch 在 `patch --dry-run`（toybox 不支持 dry-run）下于 orig 目录落盘 0 字节占位，把新增文件误判为编辑生成 `--- a/...` 头 | 改 list 形式补丁声明；安装 GNU patch 2.7.6 到 PATH；修正补丁头为 `--- /dev/null` + 尾换行；删除 orig 占位后重新生成 |
| 3 | W3/finish 的 JC 门禁命中其他库基线隐藏文件 | `archives/c/cloog/0.21.1/.build-closed`、`.staging-verified` 与 `archives/k/kics/2.1.20/.staging-verified`、`archives/t/thc/3.8/.staging-verified` 为提交前已存在的其他库基线文件（空文件，SHA-256 `e3b0c442...`），JC1/JC5 整仓扫描命中 | 按基线隔离复验规则：记录隔离前 SHA-256 → `git rm --cached`+移出临时隔离 → 复跑 W3（L0-L5 全绿，100%）→ 原样恢复并核对 `pre==post`（e3b0c442...）→ 当前库 diff/staged/PR 不含这些路径 |
| 4 | finish Step 8 gen_summary 失败 `'str' object has no attribute 'append'` | 框架 gen_summary 内部问题（非本库构建失败，非阻塞步骤） | 记录为框架非阻塞警告，不影响 W2/W3/W4 结论与交付 |

## 源码修改

- `patches/0001-include-sse_to_neon.h.patch`：新增 `include/sse_to_neon.h`（205 行，AArch64 NEON shim，portability 类）。该头由 `src/varintdecode.c` 在 `__aarch64__`/`_M_ARM64` 分支包含；头文件内部仅用 `__GNUC__`/`__clang__` 控制 `always_inline` 属性，未引入 `__OHOS__` 平台宏（R8/PF5 合规）

## 依赖版本

- conan 2.29.1（OHOS 适配版）
- cmake 4.1.2 / clang 15.0.4（OHOS SDK 26.0.0.18）
- 无第三方 requires（纯 C 库）

## 验证结果

```bash
# 上游单测（ctest 1/1 通过；unit.c 覆盖 length 0..4096 × gap 1..387420489 往返）
cd $BUILD_SRC_DIR/build && ctest --output-on-failure
# → 100% tests passed, 0 tests failed out of 1

# conan create 干净构建 + test_package 消费者用例（vbyte_encode/masked_vbyte_decode 往返）
conan create archives/m/maskedvbyte/0.1.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable

# W3 本地 CI 模拟（隔离其他库基线 junk 后）
zsh ci/conan/build_and_test.sh archives/m/maskedvbyte/0.1.0
# → L0/L1/L4/L5 全 pass，Pass rate: 100% (1/1)
```

上游测试统计双口径台账：
- 源码声明总数（source_declared_total）：1（tests/unit.c，单一 `main()` 程序内循环断言，非框架 TEST_CASE 宏）
- 当前配置实际实例化/注册可执行用例（configured_executable_total）：1（CTest `maskedvbyte_unit`）
- 实际执行并通过（executed_passed_total）：1
- 失败 0、未运行 0
- 通过率：1/1（100%）全量；1/1（100%）当前配置可执行集合
- 逐项映射：`tests/unit.c`(源码声明) → 无条件编译（无互斥分支/条件宏） → `unit` 目标（CMake MASKEDVBYTE_BUILD_TESTS=ON） → CTest 注册 `maskedvbyte_unit` → 实际执行日志见 `reports/test-report.md` 与 build/Testing/

## 消费者用例（硬门禁）

- 源文件：`test_package/test.c`
- 仅通过安装公开头文件（varintencode.h/varintdecode.h）+ 公开 API（vbyte_encode/vbyte_encode_delta/masked_vbyte_decode/masked_vbyte_decode_delta）完成编码-解码往返并断言结果
- 构建/运行：`conan create` 内 test_package 执行，`./test_maskedvbyte`，退出码 0
- 调用 API：vbyte_encode、masked_vbyte_decode、vbyte_encode_delta、masked_vbyte_decode_delta

## 知识候选台账（路径 B 判定）

| 候选 | 类型 | 根因 | 修复 | 验证 | 适用范围 |
|------|------|------|------|------|----------|
| C1: 上游 tag 引用从未发布的 SSE→NEON 翻译头 | 上游打包缺陷 | v0.1.0/master 缺 `sse_to_neon.h`（README/CMakeLists 声称存在，仓库历史从未有） | 最小补丁新增自包含 NEON shim（`<arm_neon.h>` 直写，Intel 拼写） | 上游 unit.c 往返全绿 + ctest 1/1 + conan create 通过 | 任何在 AArch64 分支引用缺失 SSE→NEON 头的 C 库 / 以 SSE 内建写 SIMD 内核的库 |

四范围查重：
- 正式库 knowledge/graph/：E113（compat 头文件创建，BSD 类型域）、E309（生成头未复制，构建期头）、E498（无头库 include 目录）、E506（NEON 源选择/链接期未定义符号）——均非本候选根因（缺随 tag 发布的 SIMD 翻译头），触发面/方案面仅部分重叠
- 知识库索引 index.tsv / doc/：无 maskedvbyte/sse_to_neon 相关条目
- 草稿库 knowledge/drafts/：E544 已有他库草稿（不同 Agent 提交），需七轴比对确认差异

七轴查重（vs 最近邻 E506/E113/E544 相关条目）：
- exact_duplicate: false（无同库同错条目）
- causal_duplicate: false（E506 是 CMake 源选择/链接期符号缺失，E113 是 BSD 类型缺失，根因不同）
- trigger_overlap: partial（E506 同涉 aarch64 NEON 域；E113 同涉“创建缺失头文件”形态）
- solution_overlap: partial（E113 同为新增头文件补丁，但内容为类型兼容而非 SIMD 内建翻译；E506 为源选择而非头文件补齐）
- combination_novelty: true（“上游引用但未随 tag 发布头文件 → 自包含 NEON shim 补齐”组合为本库特有）
- boundary_novelty: true（新增文件补丁必须 `--- /dev/null` 头 + toybox patch dry-run 落盘陷阱 + 尾换行细节，跨库可复用）
- test_migration_novelty: true（上游单测在 OHOS armv8 实测通过 + 消费者用例新增）

关系：similar_to: E113（头文件补齐形态）、E506（NEON 域）；caused_by: 无；prerequisite_of: 无；conflicts_with: 无

路径决定：**new_draft（路径 B）** — 已建 `knowledge/drafts/E544-draft-98FF.kv` + `.md` 草稿对，与三方库归档同 PR 交付；未命中正式库，存在可跨库复用的新增差异（SSE→NEON shim 补齐模式 + 补丁头/工具链陷阱）

## 交付物

| 文件 | 说明 |
|------|------|
| archives/m/maskedvbyte/0.1.0/conanfile.py | CMake 配方（静态库） |
| archives/m/maskedvbyte/0.1.0/conandata.yml | 官方 tag 源 + SHA-256 + 补丁声明 |
| archives/m/maskedvbyte/0.1.0/patches/0001-include-sse_to_neon.h.patch | 缺失头文件补齐补丁 |
| archives/m/maskedvbyte/0.1.0/test_package/ | 消费者用例 + MANIFEST |
| knowledge/drafts/E544-draft-98FF.kv / .md | 路径 B 知识草稿对 |

## 注意事项

- 禁止提交：conandata.yml.ghfast-bak、.patch-backup-*、.staging-verified、.conan-verified、.build-closed、.handoff.json 等运行时/备份文件（JC 门禁）
- W3 中其他库基线 junk（cloog/kics/thc）为提交前已存在文件，已隔离复验并原样恢复，不进入本 PR
- 发布后消费者验证（L0i 自身消费）不属于本阶段（当前库尚未发布）；L0i 本轮仅检查依赖 registry（0 依赖，无阻塞）
---

**编译结束**: 2026-09-28 17:36
**最终状态**: built
