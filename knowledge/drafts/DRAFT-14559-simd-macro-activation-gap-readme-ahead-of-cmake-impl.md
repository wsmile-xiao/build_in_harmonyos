# DRAFT-14559：SIMD 宏激活链断裂——README 选项超前于 CMake 实现，构建成功但静默退化标量路径

## 错误特征（如何发现）

- 编译日志出现 pragma：`building float with simd disabled !`（src/simd/pf_float.h:68）与
  `float SCALAR1 macros are defined`（pf_scalar_float.h）——**构建完全成功，无任何 error**。
- 运行期：`pffft_simd_size()` 返回 1（应为 4）、`pffft_simd_arch()` 返回 `"Scalar"`（应为 `"NEON"`）。
- 对照实验（pffft 1.1.0，OHOS aarch64 工具链 clang --target=aarch64-linux-ohos）：
  - 默认编译 `pffft.c` → `building float with simd disabled !`
  - 加 `-DPFFFT_ENABLE_NEON=1` → `ARM NEON macros are defined`（pf_neon_float.h:40）

这是最阴险的一类问题：**不失败、只降级**，数值测试全绿，唯一差别是性能。

## 根因（平台机制因果）

1. **文档超前于实现**：上游 README 宣称选项 `PFFFT_USE_SIMD_NEON`（"force using NEON on ARM, default: OFF"），
   但 v1.1.0 的 CMakeLists.txt 与 cmake/ 目录中该选项**不存在**（grep 全源码零命中）。
2. **宏激活链在非 Apple aarch64 断链**：NEON 后端头 `pf_neon_float.h` 的 guard 要求
   `defined(PFFFT_ENABLE_NEON)`；该宏唯一注入点是 `cmake/target_optimizations.cmake:143-144`
   的 `TARGET_C_EXTRA` 非 none 分支，而 `GCC_EXTRA_OPT_neon_*` extra 值**仅在 armv7l 分支提供**；
   非 Apple aarch64 分支 `GCC_EXTRA_VALUES=""`，`TARGET_C_EXTRA` cache 变量根本不创建 → 宏永不被定义。
3. **静默兜底**：`pf_float.h` 在 SIMD_SZ 未定义时 `#define PFFFT_SIMD_DISABLE` 走标量路径——
   上游 x86 CI（TARGET_C_ARCH=native 走 SSE 宏链）从不暴露此问题。

## 解法（代码级）

```python
def generate(self):
    tc = CMakeToolchain(self)
    arch = str(self.settings.arch)
    if arch.startswith("armv8") or arch in ("arm64", "aarch64"):
        tc.variables["CMAKE_C_FLAGS"] = "-DPFFFT_ENABLE_NEON=1"
    tc.generate()
```

要点：
- NEON 是 aarch64 **基线指令集**，无需 `-march`；`TARGET_C_ARCH` 保持上游默认 `none`，
  与 OHOS 交叉工具链零 -march 冲突。
- 不碰 `TARGET_C_EXTRA`（aarch64 上无可用值，neon_* extra 值是 arm32 专属 flags）。
- 消费者测试必须断言 `pffft_simd_size()==4` / `pffft_simd_arch()=="NEON"`，
  把"静默降级"变成"显式失败"（本 PR test_pffft.c 断言 2/3 即此收口）。
- double 路径同 guard（pf_neon_double.h:42），同一注入覆盖。

## 降级方案（fallback）

- patch `cmake/target_optimizations.cmake` 在 aarch64 分支也提供 `GCC_EXTRA_VALUES`
  （仿 apple_m1 定义 extra 值）再 `-DTARGET_C_EXTRA=<val>`——缺点：改上游构建脚本，升级需重做。
- 次级兜底：显式 `-DPFFFT_SIMD_DISABLE=1` 接受标量路径，但**必须在 PR 正文声明性能退化**
  ——不声明即静默降级，属未完成适配。

## 红线（禁止做法）

1. **禁止**只看"构建成功+数值测试全过"就认定 SIMD 适配完成——标量路径数值完全正确，
   唯一性能差异；无断言的适配会把 NEON 优化库发布成标量库。
2. **禁止**把上游 `--test-simd` 自检入口（`validate_pffft_simd_ex`）纳入集成并据其失败判库有缺陷——
   该入口上游既未注册 ctest 也从不在 CI 运行，其 VALIGNED 探针循环是 SSE 16 字节视角假设
   （NEON float 的 VALIGNED 是 4 字节，float 数组内不存在 4 字节不对齐指针），
   在 NEON float 路径确定性必报 `!VALIGNED() should have found at least 4 occurences`——
   工装缺陷非库缺陷；库正确性由 9 项 ctest（含 FFTPACK 140dB 动态范围对照）覆盖。

## 适用范围与查重边界

- 直接适配：marton78/pffft（或 fork）一切版本（激活链代码自 2013 起稳定）。
- 间接适配：内嵌 pffft.c 单源的 DSP 库（rnnoise 生态/卷积混响/SDR/语音增强）——内嵌形态
  沿用上游默认编译参数，aarch64 同样中招。
- 通用模式（跨库价值）：①README 选项超前于 CMake 实现；②SIMD 宏激活依赖"extra 选项分支"
  而该分支仅覆盖部分架构；③SIMD 降级不失败只静默——在一切"多 SIMD 后端竞争定义 + 宏守卫分发"
  的库（pffft/kissfft/celt 等）上复现。
- 不覆盖：显式 `PFFFT_SIMD_DISABLE=1` 的主动降级；x86 SSE/AVX 路径问题。
- 知识图谱查重：E100（libjpeg-turbo jsimd 符号链接期问题——链接期 vs 本条编译期激活链）、
  E506（libpng arm_init.c 源选择——文件选择 vs 本条宏注入），零语义重叠。

## 实证

- 本地 conan create 三轮全绿（OHOS aarch64，commit b5e7cdb7c9）：ctest 9/9 +
  test_package 11/11 断言（simd_size=4/NEON、频谱误差 3.8e-06、往返误差 4.8e-07、
  Parseval 能量比 0.999999964）。
- 对照实验编译日志（本机 OHOS SDK clang）：默认 vs 注入的 pragma 行见"错误特征"节。
- CI 构建号与终态见关联 issue 证据表（PR #14559）。
