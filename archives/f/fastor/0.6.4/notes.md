# fastor 0.6.4 适配笔记

## 编译环境
- 构建系统: cmake（header-only，无编译产物；上游 CMake INTERFACE target）
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4（OHOS aarch64 工具链 /data/service/hnp/bin/clang++）
- 状态: published

## 编译步骤

1. 官方源码核验：GitHub 标签 `V0.6.4`（commit bc8b06b04346b02c60cf29fc46d032e831212cf9），
   官方 tarball sha256=`c97a3b9dbb92413be90689af9d942cddee12a74733cf42f1a8014965553a11f8`。
2. `ohc-run.py init-build fastor 0.6.4 --url=<官方 V0.6.4 tarball>`（网络不可达时预放 tarball 到
   `$TMPDIR/builds/fastor-0.6.4.tar.gz` 跳过下载）。
3. 上游测试：`cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 4.x 拒绝 <3.5）→ 构建 52 个测试 →
   `ctest` 52/52 全部通过（scalar ABI 回退路径）。
4. 生成补丁：`ohc-run.py refresh-patch --auto fastor 0.6.4`（6 个补丁，per-file difflib）。
5. 配方：header-only 变体（conanfile-headeronly.py.tmpl），`conan-verify fastor 0.6.4` 八门禁全过
   （G1/G2/G3/G4/L2/L4/L5）。
6. `finish fastor 0.6.4 published`：W2 原子性 + W3 本地 CI（setup.sh + build_and_test.sh）通过，
   `.ci-result.json` 已写入（integrity_hash + log_sha256），submit 就绪预检全绿。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aarch64 编译失败 `invalid output constraint '=a' in asm`（cpuid.h / timeit.h） | Fastor 主头链（Fastor.h→util.h→timeit.h→cpuid.h）内嵌 x86 专用内联汇编 cpuid/rdtsc，aarch64 无此指令 | 补丁 0002/0006：`#if defined(__x86_64__)||defined(__i386__)` 守卫，非 x86 回退（CPUID 寄存器清零；rdtsc 用 std::chrono::steady_clock） |
| 2 | `cannot assign to non-static data member 'value' with const-qualified type 'const int'`（simd_vector_scalar.h） | 只读 TensorMap eval 实例化 `SIMDVector<const T, scalar>`，scalar 特化成员 `T value;` 为 const 无法写入 | 补丁 0005：scalar 特化加 `storage_type = remove_cv_ref_t<T>`，成员与 store/load 写路径用可变存储（与上游 base 模板剥 cv 语义一致） |
| 3 | `no matching function for call to 'vector_setter'`（complex<double> scalar ABI） | 16-word（sizeof==16, bitsize==64）scalar vector_setter 被上游注释，complex 标量回退无 setter | 补丁 0003：恢复 16-word scalar vector_setter（`vec.set(data[idx])`） |
| 4 | `call to '_matmul' is ambiguous`（complex 矩阵） | matmul_specialisations_kernels.h 非 SSE2 回退 `_matmul`（M==2 任意 T）与 matmul.h 通用 `_matmul` 同时匹配 complex | 补丁 0001：回退特化限定 float/double（与 SSE2 分支语义一致），complex 走通用路径 |
| 5 | `call to constructor of 'SIMDVector<complex<double>, scalar>' is ambiguous`（(0,0)） | `SIMDVector(0,0)` 同时匹配 `(value_type,value_type)` 与 `(const scalar_value_type*, bool)` | 补丁 0004：改为显式 `std::complex<T>(0,0)` 单参构造 |

## 源码修改

- 0001-Fastor-backend-matmul-matmul_specialisations_kernels.h.patch（+2/-1）
- 0002-Fastor-config-cpuid.h.patch（+5/-1）
- 0003-Fastor-simd_vector-simd_vector_common.h.patch（+7/-6）
- 0004-Fastor-simd_vector-simd_vector_complex_scalar.h.patch（+1/-1）
- 0005-Fastor-simd_vector-simd_vector_scalar.h.patch（+8/-4）
- 0006-Fastor-util-timeit.h.patch（+7/-0）

## 依赖版本

- 无第三方依赖（header-only 库）。构建工具：cmake 4.1.2、clang 15.0.4、conan 2.29.1。

## 验证结果

```bash
# 上游测试（aarch64 实跑）
cd builds/fastor-0.6.4.work/build-upstream
ctest   # 52/52 passed, 0 failed

# 配方验证
ohc-run.py conan-verify fastor 0.6.4   # G1-G4 + L2/L4/L5 全过

# W3 本地 CI
ohc-run.py finish fastor 0.6.4 published  # setup.sh + build_and_test.sh 通过
```

## 知识判定（路径 A — reuse_existing）

- 快照：`/storage/Users/currentUser/runnerljs002/kb-snapshot-fastor-0.6.4-r01`（repository
  https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git，ref main，HEAD
  dfe3d3ac77fa7afa801d0a7223122e63f43802c3，sparse=knowledge，只读审计见快照内 AUDIT.md）。
- 扫描范围：knowledge/graph/*.kv（542）+ doc/*.md + knowledge/drafts/*.{md,kv}（197）+ 根 DRAFT-* 对。
- 候选 1（rdtsc/cpuid x86 内联汇编在 aarch64 报 `invalid output constraint '=a'`）：
  **等价命中 DRAFT-E544**（libco，musl/OHOS 无 rdtsc，rec_approach=musl-portable-replacement
  clock_gettime 回退，forbid rdtsc/rdtscp）——错误签名、根因、方案、验证方式逐字段适用。
- 候选 2（CMake 4.x 拒绝 cmake_minimum_required <3.5）：**等价命中 E103 + E187 正式条目**
  （rec_approach=bump-cmake-minimum-version / add-cmake-flag
  `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`，实测命令一致）。
- 结论：`knowledge_decision: reuse_existing` → 路径 A；不创建草稿（新增跨库价值未被证明，
  核心错误模式已有等价条目）。

## 注意事项

- 上游 CMake 需要 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（仅测试构建用；配方 header-only 无构建）。
- 本机 /tmp 只读，构建目录使用 `$TMPDIR=/storage/Users/currentUser`。
- 环境噪声（archives/s/SDL2、libXext 等未跟踪文件）不属于本任务 diff，未提交。
- JC5 曾对历史基线 `archives/u/util-linux-login/2.42.2/.ci-trigger`（HEAD 已提交的空文件）误报：
  按基线隔离规则做临时索引隔离复验 W3 通过后无条件恢复，最终零 diff（blob e69de29b，空文件）。
---

**编译结束**: 2026-09-07 01:05
**最终状态**: published
