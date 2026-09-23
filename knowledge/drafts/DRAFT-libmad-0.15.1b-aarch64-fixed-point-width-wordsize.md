# DRAFT-libmad-0.15.1b-aarch64-fixed-point-width-wordsize：aarch64 定点位宽修正

> Contributor: pc6-5 (OH executor) | Status: Draft | Updated: 2026-09-07
> Source: libmad 0.15.1b HarmonyOS PC 适配（task libmad-0.15.1b-r01-pc6-5-20260906T152808Z）
> 本文件与 `DRAFT-libmad-0.15.1b-aarch64-fixed-point-width-wordsize.kv` 配对，stem 相同，
> 字段（主题 / error_signature / root_cause / solution / validation / 适用边界）相互对应。

## 现象

libmad 0.15.1b 在 OHOS PC aarch64（armv8 / clang-15）上构建成功、API 可调用，
但实际 MPEG 帧解码输出不可用（噪声/位宽错误）。定位到 mad.h 中两个关键宏：

```text
# define FPM_INTEL        # 32 位定点乘法/精度路径（x86 时代默认）
# define SIZEOF_LONG 4    # 与 aarch64 的 64 位 long 不符
```

## 根因（error_signature / root_cause）

- mad.h 由 configure 生成，其 FPM_INTEL 定点宏假设 32 位 long（x86/32 位时代），
  在 64 位 aarch64 上定点乘法中间量与精度路径错误，解码输出噪声。
- configure 的生成逻辑未按目标 ABI 纠正 SIZEOF_LONG（旧版本无 AC_SIZEOF_LONG 修正）。

## 方案（solution / rec_approach）

在生成 mad.h 之后、编译之前替换两个宏（Conan recipe 中 `replace_in_file` 完成）：

```python
replace_in_file(self, mad_h, "# define FPM_INTEL", "# define FPM_DEFAULT")
replace_in_file(self, mad_h, "# define SIZEOF_LONG 4", "# define SIZEOF_LONG 8")
```

- `FPM_DEFAULT`：ISO C 标准运算 + 64 位中间量，aarch64 上定点精度正确。
- `SIZEOF_LONG 8`：与 aarch64 ABI 一致。

## 验证（validation）

- 修复后 test_ohos 完整解码一帧 MPEG-1 Layer II（128kbps/44.1kHz stereo）：
  `synth_frames=1 total_samples=1152`，全绿通过。
- `mad_header_decode` 报告 `layer=II bitrate=128000 samplerate=44100`，与帧头一致。

## 适用边界（boundary / affected_scope）

- 在生成/安装头中硬编码 32 位 long 定点宏（FPM_INTEL 或等价）的 DSP、音频解码、
  定点数学库，移植到 64 位 aarch64（OHOS armv8 / 其它 ARM64）。
- 若库用 configure `AC_SIZEOF_LONG` 已正确生成宏，则无需此补丁。

## 查重差异

- **exact_duplicate**: false — FPM_INTEL/FPM_DEFAULT/SIZEOF_LONG 定点位宽全库 0 命中。
- **causal_duplicate**: false — 无同根因既有条目。
- **trigger_overlap**: false — E117（cmake config 模板）仅字面含 SIZEOF_LONG，主题为
  CONFIGURE_FILE 模板缺失，非定点位宽；DRAFT-gcem（libm long double 参考值域）是
  数学库边界行为，非处理器字长宏。
- **solution_overlap**: false — 无同类"生成头字长宏修正"方案。
- **combination_novelty**: true — 与 C3（GCC flag 剔除）组合覆盖旧 DSP 库 OHOS 适配。
- **boundary_novelty**: true — 边界为 32 位 long 定点宏在 64 位目标上的字长错配。
- **test_migration_novelty**: true — 无既有测试迁移入口。

关系：`similar_to= E117, DRAFT-gcem-1.16.0-ohos-libm-long-double-boundary`；
`caused_by= none`；`prerequisite_of= none`；`conflicts_with= none`。