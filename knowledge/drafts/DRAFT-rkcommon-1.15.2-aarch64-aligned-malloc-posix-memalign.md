# DRAFT-rkcommon-1.15.2-aarch64-aligned-malloc-posix-memalign

- **软件**：rkcommon 1.15.2（RenderKit/OSPRay 公共基础库）
- **触发门**：conan create（OHOS aarch64，clang 15.0.4，ohos-sdk 26）
- **日期**：2026-09-21

## 可复现症状与稳定错误签名

`rkcommon/memory/malloc.cpp` 编译失败，首错：

```
xmmintrin.h:14:2: error: "This header is only meant to be used on x86 and x64 architecture"
mmintrin.h:37:5: error: use of undeclared identifier '__builtin_ia32_emms'
```

触发条件：Linux/OHOS aarch64 + clang（x86 专属内建头被无条件包含）。

## 根因与最小复现

上游平台守卫只枚举三类（malloc.cpp L10-L15）：

```cpp
#ifdef _WIN32                     // Windows
#elif defined(__APPLE__) && (defined(__aarch64__) || defined(__arm64__))  // 仅 Apple arm64
#include <stdlib.h>
#else
#include <xmmintrin.h>            // 其余全部平台 → x86 专属
#endif
```

Linux-aarch64/OHOS 不匹配 `_WIN32`、也不匹配 `__APPLE__ &&`，落入 `#else` 分支引用
`xmmintrin.h` 并调用 `_mm_malloc/_mm_free`。最小复现：任意 aarch64 musl 环境编译该文件。

## 已尝试方案（含失败）

1. 配方侧 `-DRKCOMMON_TASKING_TBB=OFF`（交接预检方案）——**无效且与本错无关**：上游
   tasking 真开关是缓存变量 `RKCOMMON_TASKING_SYSTEM`（TBB/OpenMP/Internal/Debug，默认
   TBB），`RKCOMMON_TASKING_TBB` 是 `rkcommon_configure_tasking_system` 宏的输出变量，
   配方设的值在 configure 阶段被无条件覆盖；且 TBB 探测失败先于本错出现。改设
   `RKCOMMON_TASKING_SYSTEM=Internal`（源内捆绑 enkiTS）后才暴露本错。此坑单列供同族库参考。
2. 关 SIMD（`RKCOMMON_NO_SIMD=ON`）——不适用：该选项只影响 math SIMD 路径，不进 malloc.cpp。

## 最终方案与真实验证

补丁 `patches/0001-aarch64-aligned-malloc-posix_memalign.patch`：三处（include、
alignedMalloc、alignedFree）把 `defined(__APPLE__) && (defined(__aarch64__) || defined(__arm64__))`
放宽为 `defined(__aarch64__) || defined(__arm64__)`，使 Linux/OHOS aarch64 走
`posix_memalign/free`。等效性：musl 提供 posix_memalign（C11 POSIX），对齐参数同为 2 的幂，
free 释放；x86/Windows/Apple 路径一字未动，32 位 ARM 仍走原分支（两个宏在其上不定义）。

实测：OHOS aarch64 conan create 全绿——上游 ctest **16/16**（bundled catch v2 单套件
`rkcommon_test_suite`，**137 个 TEST_CASE** 经 16 个 `[tag]` add_test 注册项全量执行，
0 失败）+ 消费者测试 `test_probe` **10 断言**通过（math::vec/dot/cross/length、
utility::Optional、containers::AlignedVector、utility::OnScopeExit）。

## 适用范围/反例/解除条件/风险

- **适用**：RenderKit 系（OSPRay/Embree/openvkl/rkcommon 及衍生 fork）的
  alignedMalloc/alignedFree 家族；泛化为"对齐分配按平台分支但未给 Linux-aarch64 留 POSIX
  路径"的任意 C++ 库。
- **反例**：把 `_mm_malloc` 用在 SIMD 计算中间（非纯分配）的场景——应走
  `similar_to` 条目的 NEON 位重配方案，而非本条的条件放宽。
- **解除条件**：上游补全 Linux-aarch64 分支或改用 std::aligned_alloc 后升级源码、移除补丁。
- **风险**：极低——仅扩宽条件分支；已由 16/16 ctest + 消费者断言验证行为不变。

## 查重与新增价值

- 四范围查重：knowledge/graph（G0 命中 E540 = runner PATH，无关）；knowledge/drafts 含
  `DRAFT-jsonifier-neon-cpu-instructions-bits`（错误签名相同，但根因=库内 CPU 指令集位选头、
  解法=改 NEON 位组合 + `__aarch64__` 内建分支，与本条"平台条件枚举缺失 → 放宽走
  posix_memalign"互不覆盖）；`经验文档/适配经验汇总.md` 与已合入 PR 草稿无
  xmmintrin/_mm_malloc/posix_memalign 主题条目。
- **新增价值**：a) 给 RenderKit 全家族（OSPRay 生态适配高发）提供可直接套用的对齐分配
  aarch64 修法；b) 记录 `RKCOMMON_TASKING_SYSTEM` 缓存变量这一"配方变量被宏覆盖"陷阱，
  同族（Embree/openvkl）同样存在；c) 与既有 jsonifier 草稿组网，形成"同签名、双根因、
  双解法"的判重对。
