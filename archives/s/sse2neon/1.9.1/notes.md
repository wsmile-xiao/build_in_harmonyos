# sse2neon 1.9.1 适配笔记

## 编译环境
- 构建系统: header-only（上游 Makefile 仅用于测试，无库产物安装目标）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4（OHOS aarch64，`-march=armv8-a+fp+simd`）
- 状态: built（conan-verify 通过、未 upload）

## 适配步骤

1. `init-build sse2neon 1.9.1 --url=<codeload 官方 tar.gz>`：下载、解压、建骨架。
2. `lang-preflight`：detected=cpp，匹配通过。
3. 上游测试枚举与实测（aarch64 本机直接运行，`make check` 驱动）：
   - `tests/main`：525/525 通过（InstructionTest 注册表 525 项）
   - `tests/ieee754`：50 个 TEST_CASE，注册 49 项；-O0 49/49 通过；
     -O2 下 ftz_output_flush/daz_input_flush 失败
   - `tests/nan`：132 个 TEST_CASE，注册 131 项；-O0 131/131 通过；
     -O2 下 cvtss_si64_nan 失败
   - `tests/aes`：21 个 TEST_CASE，注册 20 项；20/20 通过
   - `tests/differential`：需 x86 生成 golden 数据，本机无数据未实例化
4. 重写 conan 配方为 header-only（模板 v12.21 变体 A）：
   `package_type=header-library`、`no_copy_source`、无 `build()`、
   `package()` 拷贝 `sse2neon.h`→include、`LICENSE`→licenses、
   `package_id clear`、`cpp_info` 置空 libs/bindirs/libdirs。
5. 新增消费者测试 `test_package/test.c`（真实调用公开 SIMD API）与
   HarmonyOS 专项测试 `test/ohos_sse2neon_test.cpp`（静态断言
   SSE2NEON_ARCH_AARCH64 + 浮点/整数/置换 SIMD 结果校验，本机实测通过）。
6. `conan-verify` → `finish published` → W3 → W4 审计 → submit/PR。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ieee754 的 ftz_output_flush/daz_input_flush 在 -O2 失败 | clang -O2 将 `FLT_MIN*0.5` 常量折叠为次正规常量，绕过运行时 FPCR.FZ 控制；裸 asm 置 FPCR.FZ 后标量/NEON vmul 实测均 flush 为 0，证明平台 FZ 有效 | 记录为编译器常量折叠 × 运行时控制交互（上游测试对优化敏感），-O0 下 49/49 通过；台账如实列明 |
| 2 | nan 的 cvtss_si64_nan 在 -O2 失败 | sse2neon `_mm_cvtss_si64` 用 `(int64_t)NaN` 静态转换，float→int64 NaN 转换是 UB；clang -O2 生成垃圾值（非 0/INT64_MIN），-O0 返回 0（上游允许） | 记录为 UB 代码生成差异；-O0 131/131 通过；台账如实列明 |
| 3 | 初始生成 autotools 配方模板 | conan-init 按"有 Makefile"判定为 autotools，但 sse2neon 无 configure/安装产物 | 重写为 header-only 变体 A 配方 |

## 依赖版本

无第三方依赖（header-only，零依赖）。

## 验证结果

```bash
# 上游测试（aarch64 本机）
./tests/main            # Passed: 525, Failed: 0
./tests/ieee754         # -O0: 49 passed / -O2: 47 passed 2 failed(常量折叠)
./tests/nan             # -O0: 131 passed / -O2: 130 passed 1 failed(UB)
./tests/aes             # Passed: 20, Failed: 0
# HarmonyOS 专项
./ohos_sse2neon_test    # PASS（8 项 CHECK 全过）
# 消费者测试（conan test_package）
./test_sse2neon         # PASS（4 项 CHECK 全过）
```

## 交付物

- `conanfile.py`（header-only）、`conandata.yml`（官方 codeload URL + SHA-256）
- `test_package/`（CMake + test.c 消费者测试 + MANIFEST.yml 上游测试声明）
- `test/ohos_sse2neon_test.cpp`（HarmonyOS 专项测试）

## 注意事项

- 上游测试对 -O2 优化敏感：FTZ/DAZ 用例依赖运行时 FPCR 控制，clang 常量折叠会使其失效；属编译器行为，非平台缺陷（裸 asm 已验证 FZ 有效）。
- `(int64_t)NaN` 在 clang aarch64 -O2 为 UB，业务代码应避免依赖该转换结果。

## 知识候选台账（路径 B · 知识库扩展）

任务类型为【知识库扩展】，按 knowledge-reuse-governance 完成候选台账与四范围查重（knowledge/doc 正式条目、knowledge/graph 图谱、knowledge/drafts 草稿、index.tsv 索引）：

| # | 候选 | 真实错误 | 根因 | 修复/验证 | 适用范围 | 查重结果 |
|---|------|---------|------|-----------|---------|---------|
| 1 | clang -O2 常量折叠绕过 FPCR.FZ/DAZ 运行时控制 | ieee754 ftz_output_flush/daz_input_flush 失败 | clang -O2 将 FLT_MIN*0.5 折叠为次正规常量，运行时 FZ 位对已折叠常量无效 | -O0 49/49 通过；裸 asm 置 FPCR.FZ 后标量/NEON 运行时输入均 flush（平台 FZ 有效） | 任何靠运行时 CSR 控制的 SIMD/数值库上游测试 | 未命中（FPCR/FTZ/常量折叠关键词全库为零） |
| 2 | clang aarch64 `(int64_t)NaN` -O2 UB 生成垃圾值 | nan cvtss_si64_nan 失败 | sse2neon _mm_cvtss_si64 static_cast NaN→int64 是 UB；-O2 返回垃圾值（非 0/INT64_MIN） | -O0 131/131 通过（返回 0 为上游允许值）；实测 -O2 垃圾值复现 | 一切 aarch64+clang 下 float→int64 标量转换 | index.tsv E432 为 native 资源所有权/坐标收敛契约，非同题；无直接命中 |

### 七轴查重

候选 1（FPCR.FZ × 常量折叠）：
- exact_duplicate: 无（全库 FPCR/FTZ/denormal 零命中）
- causal_duplicate: 无同因条目
- trigger_overlap: 与 E145（meson arm intrinsics 变量）、DRAFT-E429（libbacktrace noclone 优化测试）同为"优化/检测影响测试"，但触发机制不同（常量折叠 vs 尾调用消除），无指令级重叠
- solution_overlap: 无重叠方案（-O0 复验平台能力，非补丁方向）
- combination_novelty: ✅ 新增（运行时 CSR 控制 × 编译期常量折叠）
- boundary_novelty: OHOS aarch64 FPCR.FZ 实测有效为本仓首证
- test_migration_novelty: 可迁移到其他 SIMD/数值库的 FTZ 段测试

候选 2（float→int64 NaN UB）：
- exact_duplicate: 无
- causal_duplicate: E432 涉及 NaN 但为资源所有权/坐标契约，非类型转换 UB，非同因
- trigger_overlap: 无
- solution_overlap: 无（E432 方案为 checked narrowing，非同题）
- combination_novelty: ✅（类型转换 UB × clang 优化代码生成）
- boundary_novelty: aarch64+clang 行为差异（-O0=0 vs -O2=垃圾值）首证
- test_migration_novelty: 可迁移到 cvtss/cvttss 类 SIMD 转换测试

### 路径决定

- **候选 1、2 均已实测验证、可跨库复用、查重未命中 → 路径 B 成立，new_draft**
- 已用 `ohc-run.py graph add` 建立同 stem 草稿对：
  - `knowledge/drafts/E554-draft-PC32.kv` + `.md`（FPCR.FZ × 常量折叠）
  - `knowledge/drafts/E555-draft-PC32.kv` + `.md`（float→int64 NaN UB）
- 草稿随本库 PR 一同交付；不建 Issue、不建正式条目（审查权在主编）
- 关系字段：similar_to=E432（NaN 主题）；caused_by=clang 优化/UB 语义；prerequisite_of=无；conflicts_with=无
---

**编译结束**: 2026-09-17 00:10
**最终状态**: built

## R05 differential golden 闭环（2026-09-17）

- golden 制品经 8080 主服务制品端点下载（size=132468），SHA-256=0a055220…87c758e 核验一致；解包 132 个 `.golden` 至 `test/golden/`，逐文件 sha256 清单 132/132 OK。
- `make check-differential GOLDEN_DIR=<test/golden>` 首跑：默认 -O2 下 66 passed / 66 failed / 27 skipped——失败均为与 golden 相差末位 1 ULP（如 479a08ec vs 479a08ed），根因是 clang aarch64 默认启用 FP 收缩（FMA fusion）导致与 x86 SSE golden 的在舍入差异。
- 最小构建配置修复（任务规则 2：修复构建配置后复验）：differential 测试目标以 `-ffp-contract=off` 编译，复验 **132 passed / 0 failed / 27 skipped（exit 0）**。
- 台账更新：differential 由「未实例化」更新为「已运行」；132 项与 main/ieee754/nan/aes 无重叠（独立差分 harness，非重复计数）；双口径：source_declared_total=726（main 525 + ieee754 50注册49 + nan 132注册131 + aes 21注册20 + differential harness 132 独立项），configured_executable_total 与 executed_passed 见 MANIFEST 口径；differential 132/132（-ffp-contract=off 配置下全量通过）。

## R06 CI 交付修复（2026-09-17）

- **CI 失败根因**：R05 将 132 个二进制 .golden 文件作为测试资产直接提交进 PR，CI diff 应用机制无法处理大量纯二进制文件（"missing binary patch data for .../mm_*.golden" / "binary patch does not apply"），PR diff 应用失败归类为"与 main 冲突"。
- **修复方案 A（本轮实施）**：golden 移出 PR/git 跟踪，改由分析端制品端点交付。
  - `git rm` 132 个 .golden（`archives/s/sse2neon/1.9.1/test/golden/` 不再进入 base..HEAD diff / staged / commit / PR 文件列表）。
  - 新增文本类可复现入口 `test/fetch_golden.sh`：下载 URL `http://192.168.31.248:8080/artifacts/sse2neon/sse2neon-1.9.1-golden-x86.tar.gz`（SHA-256 `0a055220636fa0d611c51577e169dfc4b7f24578e2011388be5aad37d82c758e`，清单整体 `cdd8d4e8db1271a5950d2b805d72d68a69fa21e705e357906706eaf4d721f5b1`），下载→sha256 核验→解包 132 个 .golden→供 `make check-differential` 使用；实测通过。
  - conandata.yml 仍仅官方 HTTPS 归档 URL，无 file:// / 绝对路径 / 缓存路径污染。
- **本地差分复验（本轮重跑）**：制品端点重新下载 golden（SHA-256 核验一致）后，以 `-ffp-contract=off` 编译 differential 测试目标运行 `make check-differential GOLDEN_DIR=<golden 目录>` → **132 passed / 0 failed / 27 skipped（exit 0）**；R05 已运行且通过结论保留（以本轮重跑日志为准）。
- **台账口径不变**：双口径、去重口径与 R05 一致（differential 132 项与既有入口 main/ieee754/nan/aes 无重叠不重复计数）；执行端/CI 测试时按 fetch_golden.sh 按需下载 golden 即可复现。
