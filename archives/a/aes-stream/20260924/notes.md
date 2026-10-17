# aes-stream 20260924 适配笔记

## 编译环境
- 构建系统: custom（上游无任何构建系统，配方直接 clang 编译 + llvm-ar 归档）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4 (OHOS SDK aarch64) / llvm-ar
- 状态: built

## 编译步骤

上游仓库仅含 `src/aes-stream.c`（x86 AES-NI intrinsics）+ `src/aes-stream.h`，
无 Makefile/CMakeLists/configure/meson，且核心逻辑依赖 immintrin.h（x86-only），
OHOS arm64 上无法直接编译。适配方案：携带 ARMv8 crypto extension 移植实现
`src/aes-stream-arm.c`，配方 `build()` 直接编译：

```bash
clang -c -O2 -fPIC -march=armv8-a+crypto -Isrc src/aes-stream-arm.c -o aes-stream-arm.o
llvm-ar rcs libaes_stream.a aes-stream-arm.o
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `immintrin.h: "This header is only meant to be used on x86 and x64 architecture"` | 上游 aes-stream.c 全部核心逻辑基于 x86 AES-NI intrinsics（__m128i/_mm_aesenc_si128/_mm_aeskeygenassist_si128），无任何可移植路径 | 新增 ARMv8 crypto extension 移植实现 aes-stream-arm.c（vaeseq_u8/vaesmcq_u8/veor），逐位镜像上游 AES-PRF + key-erasure 构造 |
| 2 | 直接套 `vaesmcq_u8(vaeseq_u8(st, rk))` 无法复现标准 AES 轮（KAT 不命中） | 本平台 AESE 指令为 key-first 语义（先 AddRoundKey 再 SubBytes 再 ShiftRows），与 x86 AESENC 相反 | 穷举 48 组合对 FIPS-197 KAT 实证，唯一命中：内部轮 `veor(AESMC(AESE(st,0)), rk_i)`、末轮 `veor(AESE(st,0), rk_Nr)` |
| 3 | 上游零测试入口 | 源码树仅 2 个源文件，无测试/构建系统 | 可移植标量参考（oracle）过 FIPS-197 KAT 后与 ARM 版 bit-exact 对拍（4 seed × 3 长度，AES-128/256 全空 diff）；test_package 补 KAT/确定性/非全零/key-erasure 断言 |

## 源码修改

无补丁。新增移植源文件 `src/aes-stream-arm.c`（随配方 exports_sources 携带），
官方头 `src/aes-stream.h` 原样使用。

## 依赖版本

- clang 15.0.4 (OHOS SDK 26.0.0.18 native/llvm)
- llvm-ar / llvm-ranlib（同 SDK）
- 无外部 Conan 依赖（requires 为空）

## 验证结果

```bash
# FIPS-197 KAT：AES-128 ct=69c4e0d8...b4c55a, AES-256 ct=8ea2b7ca...496089 → OK
# bit-exact 对拍：diff oracle10.out arm_10.out / oracle14.out arm_14.out → 全空
# conan-verify：G0-G4 + L2/L4/L5 全部 PASS
# W3 本地 CI：conan create + test_package（KAT 断言）通过，.ci-result.json exit_code=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | custom 构建配方（clang 直编 + llvm-ar），携带 src/* 移植源 |
| conandata.yml | 官方 codeload tarball + sha256 |
| test_package/ | 消费者 KAT/确定性/非全零/key-erasure 测试（4 断言块） |
| src/aes-stream-arm.c | ARMv8 crypto extension 移植实现（201 行） |

## 注意事项

{需要特别注意的点；无则删除此节}

## 上游测试枚举台账（R51 三步法第一步：清点证据）

### 源码树全量清点（官方 master tarball，sha256=7facc790b4cbec435fecd9341aabd0a182dfb71f13fc867c193fa803162677d5）
```
aes-stream-master/
├── .gitignore
├── LICENSE
├── README.md
└── src/
    ├── aes-stream.c   (244 行)
    └── aes-stream.h   (29 行)
```

### 逐类枚举结论
| 类别 | 是否存在 | 说明 |
|------|---------|------|
| 用户测试源（tests/ 等独立用例） | 否 | 源码树无 tests/、test/、*_test.c 等任何测试文件 |
| 框架头/源码（gtest/catch/check 等） | 否 | 无 |
| 样例（examples/samples） | 否 | 无 |
| 基准（benchmarks） | 否 | 无 |
| fixture | 否 | 无 |
| 测试脚本（ctest/pytest/./test.sh） | 否 | 无任何 .sh 脚本；无 Makefile/CMakeLists/configure/meson 构建入口 |
| 构建目标 | 否 | 上游无构建系统，仅有纯源码文件 |
| 源码内测试钩子（main()/assert/self-test） | 否 | grep -i "test\|main\|assert\|bench" 仅命中 2 处编译期 COMPILER_ASSERT（sizeof 静态断言，非运行时用例） |

### 双口径统计（R51/R52 口径）
- source_declared_total = 0（官方源码可复制枚举的测试声明总数：0）
- configured_executable_total = 0
- executed_passed_total = 0，失败 0，未运行/未实例化 0
- 全量通过率 = 0/0（无用例，N/A；上游确无测试，清点证据如上）
- 该库无独立上游测试用例可运行；无法运行原因：上游源码不提供任何测试入口，且核心实现依赖 x86 AES-NI intrinsics（immintrin.h / _mm_aesenc_si128），非 arm64 OHOS 原生可执行。

### 计划补充（鸿蒙专项）
按任务要求新增 1 个真实可执行的 HarmonyOS 专项测试用例（消费者验证 + 已知向量校验），计入鸿蒙专项测试计数，不冒充上游用例。
---

**编译结束**: 2026-09-24 04:34
**最终状态**: published

## 知识候选台账 + 七轴查重 + 路径决定（knowledge_candidate_ledger）

### 候选 1（非噪声）：x86 AES-NI intrinsics-only C 库在 OHOS arm64 的移植路径
- 真实错误：immintrin.h:14:2 error "This header is only meant to be used on x86 and x64 architecture"（首个编译错误，clang -c aes-stream.c）
- 根因：上游 aes-stream.c 全部核心逻辑基于 x86 AES-NI intrinsics（__m128i/_mm_aesenc_si128/_mm_aeskeygenassist_si128），无任何可移植路径；OHOS PC 目标为 aarch64。
- 修复：新增 ARMv8 crypto extension 移植实现（arm_neon.h: vaeseq_u8/vaesmcq_u8/vaesimcq_u8），逐位镜像上游 AES-PRF + key-erasure 构造；实证发现本平台 AESE 指令语义为"先 AddRoundKey 再 SubBytes 再 ShiftRows"（与 x86 AESENC 相反），标准 AES 轮必须写作 veor(AESMC(AESE(st,0)), rk_i)（穷举 + FIPS-197 KAT 唯一命中）。
- 验证：标量参考 oracle vs ARM 移植版 bit-exact 对拍（AES-128/AES-256 × 4 seed × 3 长度全部逐字节一致）；静态库 + 消费者 KAT 断言通过。
- 适用范围：所有"仅 x86 SIMD/intrinsics 且无构建系统（或构建系统不可用）"的 C/C++ 库在 OHOS arm64 的移植；可跨库复用（同类 AES/SIMD 库直接套用 AESE 语义映射与对拍验证链）。

### 四范围查重结果
| 范围 | 条目 | 覆盖情况 |
|------|------|---------|
| 正式知识 (graph/E*.kv) | E145/E506/E999（见下） | 未命中：E145=meson subdir 变量序；E506=CMake NEON 源码选择；E999=FindSSE.cmake cache 误判，三者均非 intrinsics 移植 |
| 图谱 index.tsv | 检索 aes/neon/intrinsic/armv8 | 无 aes-stream 或 AES-NI→ARM crypto 移植条目 |
| drafts/ | jsonifier-neon（CPU 指令位按 x86 生成）、E555（sse2neon NaN→int64 UB）、E999 | 均不同故障面：无移植语义映射条目 |
| doc/ | 无相关 | — |

### 七轴查重
| 轴 | 结论 |
|----|------|
| exact_duplicate | 无完全相同条目 |
| causal_duplicate | 无同根因条目（E999 根因是 CMake cache 误判注入 -msse2，非 intrinsics 移植） |
| trigger_overlap | 部分：immintrin.h x86-only 报错与 E999 xmmintrin.h missing 同族（x86 头在 aarch64 不可用），但触发面不同（源码直编 vs CMake 旗标注入） |
| solution_overlap | 无：E999 方案=配方层 cache 拦截；本候选=源码级 ARMv8 crypto 移植 + AESE 语义实证 |
| combination_novelty | 高：AES-NI→ARMv8 crypto 移植 + 实测 AESE 逆序语义 + bit-exact 对拍验证链，组合无先例 |
| boundary_novelty | 新增：对"仅 x86 intrinsics 且无构建系统 C 库"给出完整移植→验证→配方路径 |
| test_migration_novelty | 新增：标量 oracle + FIPS-197 KAT + 多轮 bit-exact 对拍作为移植正确性验证方法，可将上游零测试缺口转为可审计验证链 |

### 路径决定：**new_draft（路径 B 知识库扩展）**
- 依据：任务 task_type=知识库扩展；候选已验证（bit-exact 对拍证据）、可跨库复用、查重未命中且存在新增差异（AESE 语义实证 + 对拍验证链），满足路径 B 必要条件。
- 结论：reuse_existing=false；new_draft=true（建立同 stem 的 .kv/.md 草稿进知识库草案）；path_a_no_knowledge=false。
