# Kaldi

Kaldi 是 WFST（加权有限状态转换器）路线的开源语音识别工具包，提供特征提取（MFCC/PLP/FBANK）、
GMM/DNN 声学模型训练、以及基于 WFST 的解码器（含 online2 流式识别）。

- 官网：https://kaldi-asr.org/
- 仓库：https://github.com/kaldi-asr/kaldi

## OHOS 适配

本包提供 kaldi 的 C++ 静态库与头文件（`lib/libkaldi-*.a`，`include/<subdir>/*.h`）。

> 上游静态库文件名为 `kaldi-*.a`（无 `lib` 前缀）；为让 Conan 消费方能用
> `-lkaldi-<lib>` 链接，打包时统一重命名为 `libkaldi-*.a`。

- 依赖制品仓中已适配的 `openfst/1.8.4`（`--fst-root`，静态）与 `openblas/0.3.34`
  （`--mathlib=OPENBLAS`，提供 BLAS + LAPACK），不使用上游 `tools/` 自带的下载编译流程。
- OpenFst 1.8.4 与 kaldi g20231112 之间的 API 差异（`<fst/types.h>` 移除、`FST_FLAGS_*`、
  `ArcMapFst`/`ArcMap`、`FstPrinter::Print`、`CompactFst::WriteFst`、`StateIteratorData::base` 等）
  由 `patches/0002` 修复；OpenBLAS 自带 LAPACK >= 3.10 头文件与 kaldi CLAPACK 原型冲突由
  `patches/0003` 修复。
- 仅发布静态库；`src/*bin/` 命令行工具（每个都静态链入整套 kaldi、运行时需模型数据）不在本包内。

## 使用

```python
self.requires("kaldi/g20231112")
```

```cpp
#include "base/kaldi-common.h"
#include "matrix/kaldi-matrix.h"
```

## 上游测试

上游入口为 `make -C src test`（123 个测试程序），已在 `conan create` 的 `build()` 中作为门禁执行。

## 版本

`g20231112` 对应上游 master 分支快照 `e8ed6107cb8880fb2b9a2b7dea2f5889962b614b`（2023-11-10）。
