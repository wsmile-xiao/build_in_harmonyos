# vc 1.4.5 适配笔记

## 编译环境
- **类型**: header-only C++（无库编译）
- **编译日期**: 2026-08-28
- **编译器**: clang 15（OHOS 6.0 交叉工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/v/vc/1.4.5 --build=missing
```

### 1. 源码获取（source()）
`get()` 下载 GitHub 1.4.5 tag tarball（645KB），`strip_root=True` 解压。

### 2. 打包（package()）
header-only——`shutil.copytree` 拷贝 `Vc/` 头文件目录（含 common/ 子目录 +
Allocator/IO/Memory/SimdArray/Utils）+ CMake 生成的 `Vc/config.h` 到 include。

### 3. 上游测试（build() 集成——rule 4 实测回填）
`BUILD_TESTING=ON` 单独构建 tests（unittest 框架，31 个 ctest 用例）+ ctest 运行：
```bash
cmake <src> -DBUILD_TESTING=ON -DBUILD_EXAMPLES=OFF \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_CXX_FLAGS='-std=c++14 -DVc_IMPL=Scalar'
cmake --build <bdir> -j4
ctest --test-dir <bdir>
```
aarch64 OHOS 走 Scalar 实现（无 SSE/AVX），测试全量运行。

**实测结果：29 passed / 2 failed / 0 skipped（31 用例 = 93.5%，分母=全部用例）**

两轮提升过程：
- **第 1 轮**：3 个失败（logarithm/trigonometric/alignedbase）→ 修复 testdata 子模块
  下载（272MB codeload 整包，raw 端点超时）→ logarithm 通过（3→2 失败）
- **第 2 轮**：诊断剩余 2 个失败原因（见下）

**再次两轮提升尝试（2026-08-28，实测确认不可修）**：
- **第 1 轮**：实测 OHOS `atanf(+inf)` 返回 `0x3fc90fda` vs 参考 `0x3fc90fdb`
  （1 ULP）——`-ffast-math` 编译也无法改变该返回值（libm 实现差异）；
  `alignedbase` 为 Scalar 实现固有行为
- **第 2 轮**：确认 `Vc::SimdMaskArray<int,N>` 的 `MemoryAlignment=1` 与
  `alignof(V)=4` 在 Scalar 下固有（AVX 模拟在 aarch64 不可用）——无编译
  选项/宏可修
- **结论**：29/31 = 93.5% 保持——2 failed 均为环境/实现模式差异，如实记录

**剩余 2 个失败原因（如实记录，环境/实现差异）**：
1. `trigonometric_scalar`（3 个子断言）：`Vc::atan(+inf)` float 精度——
   OHOS libm 返回 `1.570796251` vs 参考 `1.570796371`（差 ~1 ulp）；非 Apple
   平台上游用严格比较（`ATAN_COMPARE=COMPARE`，仅 Mac 用 FUZZY_COMPARE），
   OHOS libm 的 atanf 对 +inf 的返回与 glibc 参考值不一致——环境 libm 精度差异
2. `alignedbase`（7 个子断言）：`MemoryAligned<V>` 的 `alignof(T)=4` vs
   `V::MemoryAlignment=1`——标量实现（Vc_IMPL=Scalar）下 SIMD 对齐假设不成立
   （上游测试按 SIMD 架构设计，Scalar 模式 alignof 由元素类型 int 决定）——
   实现模式差异

## 验证结果
- **构建**: `vc/1.4.5: Package created`
- **上游测试**: 实测 **29/31 通过（93.5%）**——2 failed 环境/实现差异（原因见上），build() 集成回填（rule 4）
- **R34 消费者验证**: test_package——头文件存在 + 编译运行使用 Vc 类型的 smoke（Vc::int_v 加法，1/1 = 100%）
