# cm256cc

**GF(256) Cauchy MDS 块擦除码快速 C++ 库**（来自 f4exb，SDRangel 生态组件）

cm256cc 是catid/cm256 的 C++ 重写：给定原始数据块，生成恢复块，用于在丢包/擦除场景下还原原始数据。支持 GF(256) Cauchy MDS 编码/解码，x86 上使用 SSE2/SSSE3/SSE4/AVX 路径，ARM64 上强制使用 NEON（经内嵌 sse2neon 映射）。

## 用法

```cpp
#include <cm256cc/cm256.h>

CM256 cm256;
CM256::cm256_encoder_params params;
params.BlockBytes = 64;      // 每块字节数
params.OriginalCount = 10;   // 原始块数 < 256
params.RecoveryCount = 4;    // 恢复块数 < 256
cm256.cm256_encode(params, blocks, recoveryBlocks);
cm256.cm256_decode(params, blocks);   // 用恢复块还原丢失的原始块
```

## 上游

- 主页: https://github.com/f4exb/cm256cc
- 许可证: GPL-3.0-only（仓库 LICENSE；内嵌 cm256/sse2neon 上游部分保留其 BSD 声明）
- 构建: CMake（仅 SHARED 库；`BUILD_TOOLS=ON` 时附带 cm256_test/cm256_tx/cm256_rx 工具）
- 内嵌依赖: sse2neon.h（ARM64 NEON 支持所需，随官方源码提供）
