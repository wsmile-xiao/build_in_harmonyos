# E544 — 上游发布 tag 引用其从未随包发布的 SSE→NEON 翻译头

> 草稿（路径 B 候选），来源：maskedvbyte 0.1.0 首轮 HarmonyOS PC 适配。

## 错误特征

```
src/varintdecode.c:24:10: fatal error: 'sse_to_neon.h' file not found
#include "sse_to_neon.h"
         ^~~~~~~~~~~~~~~
1 error generated.
```

首次 AArch64（含 OHOS armv8）交叉构建即缺头失败；x86-64 路径不受影响。

## 触发条件

- 构建系统: CMake（Makefile 相同病根）
- 阶段: compilation
- 前置: `target_compile_features(... c_std_99)` + aarch64 目标；源码在 `__aarch64__`/`_M_ARM64` 分支引用 SSE→NEON 翻译头

## 根因分析

上游 README 与 CMakeLists 都声称 "On 64-bit ARM it uses the NEON baseline via `include/sse_to_neon.h`"，但该文件从未出现在仓库 git 历史与任何 release tarball 中（`git log --all --name-only | grep sse_to_neon` 零命中）。上游把"应该附带"的 SIMD 翻译头漏发，导致 aarch64 分支编译直接断链。这是上游打包缺陷，不是平台限制，必须在当前库内以最小补丁修复并复验（不得以外部阻塞停止）。

## 解决方案

### 推荐方案

新增自包含 `include/sse_to_neon.h` 补丁（portability 类），直接基于 `<arm_neon.h>` 实现库源码实际使用的 SSE2/SSSE3/SSE4.1 内建，并保持 Intel 拼写（`__m128i`/`_mm_*`）使库体零改动：

- `typedef int32x4_t __m128i;`
- PSHUFB（`_mm_shuffle_epi8`）：`vqtbl1q_u8` + 控制字节 `& 0x8F`（bit7 置位选 0，与 SSE 语义一致）
- per-lane 逻辑移位（`_mm_srli_epi32/16/64`、`_mm_slli_epi64`）：`vshlq` 负计数右移，计数≥位宽自然归零
- PMOVMSKB（`_mm_movemask_epi8`）：`vshrq_n_u8(7)` + 加权水平加
- `_mm_cvtepi8_epi32`：`vmovl_s8(vget_low_s8(...))` → `vmovl_s16(vget_low_s16(...))`

验证：上游 `tests/unit.c`（length 0..4096 × gap 1..387420489 往返）经 `ctest` 全绿 + `conan create`（G2）通过 + test_package 消费者用例（公开 API 往返断言）通过。

### 操作陷阱（跨库可复用）

- 补丁头必须是 `--- /dev/null`（新增文件），不能是 `--- a/...`；否则 Conan `apply_conandata_patches` 报 `source/target file does not exist`
- 工作环境 `patch` 若是 toybox（非 GNU），其 `--dry-run` 行为会在 orig 目录落盘 0 字节占位，导致 refresh-patch 把新增文件误判为"编辑"并重新生成坏补丁头；需先安装 GNU patch 2.7.6 到 PATH
- 补丁文件末尾必须有换行，否则 GNU patch dry-run 报 malformed

### 禁止做法

- ❌ 用 `ln -s` 硬链补齐（HMDFS 不支持）
- ❌ 在补丁文件里写 `#ifdef __OHOS__` 平台宏（R8/PF5）
- ❌ 修改源码 URL 为镜像/缓存/`file://`（R39/PF7）
- ❌ 把缺头当作外部阻塞回报而不修

## 验证

```bash
cd $BUILD_SRC_DIR/build && ctest --output-on-failure          # 1/1 passed
conan create archives/m/maskedvbyte/0.1.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing        # G2 PASS
zsh ci/conan/build_and_test.sh archives/m/maskedvbyte/0.1.0   # W3 100%
```

## 关联条目

- 相关: E113（创建兼容头文件的补丁形态）、E506（aarch64 NEON 域、源选择/链接期符号）
- 差异: E113 是 BSD 类型兼容；E506 是 CMake 源选择与链接期符号——根因均不同（本条目是"上游引用但未随 tag 发布头文件"）