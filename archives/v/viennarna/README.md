# viennarna

> The ViennaRNA Package — 用于 RNA 二级结构预测与比较的 C 代码库（RNAlib）与独立程序集合

## 简介

ViennaRNA Package 提供预测与比较 RNA 二级结构的 C 代码库（RNAlib，`libRNA`）以及多个独立程序（`RNAfold`、`RNAcofold`、`RNAalifold`、`RNAeval` 等）。

主要功能：
- **最小自由能（MFE）结构预测**（Zuker & Stiegler 算法）
- **配分函数（partition function）**：碱基配对比率（McCaskill 算法）
- **次优结构生成**（Wuchty 算法）
- **结构比较**：间距度量、树编辑距离
- **序列设计（反向折叠）**

## OHOS 适配要点

### 编译建议

ViennaRNA 使用 GNU autotools。HarmonyOS PC (aarch64) 上构建需：

```bash
./configure \
  --host=aarch64-unknown-linux-gnu \
  --build=aarch64-unknown-linux-gnu \
  --without-python --without-perl --without-swig \
  --without-gsl --disable-mpfr --without-svm \
  --without-forester --without-kinfold --without-rnalocmin \
  --disable-lto --disable-openmp --disable-vectorize --disable-simd
```

要点：
- `config/config.sub` 需识别 `ohos` 基本 OS 类型与 `linux-ohos` kernel-OS 组合；`config/config.guess` 增加 HarmonyOS 探测（见 `patches/`）。
- `libRNA.a` 强制静态链接（upstream `LDFLAGS -static`），内含 bundled `dlib` C++ 对象，下游消费方需用 C++ 链接器链接并带 `libc++`。
- libsvm 支持会注入 `-lstdc++`，在 OHOS libc++ 工具链上无法解析，需 `--without-svm`（仅影响 RNAfold `-z` z-score，SWIG 接口已禁用，无重新生成要求）。
- Python/Perl/SWIG 脚本接口、GSL/MPFR 数值库均为可选/独立交付物，打包时禁用。

### 补丁说明

| 补丁/机制 | 说明 |
|------|------|
| `0003-Makefile.in-no-doc.patch` | 从顶层 SUBDIRS 移除 doc/doxygen 与 doc，避免参考手册构建（需 doxygen/sphinx/pdflatex，OHOS 均缺失）导致 `No rule to make target xml/*` |
| 配方内 content-anchored OHOS 识别（conanfile.py `_apply_ohos_gnu_config_patches`） | 对 config/config.sub 识别 `ohos` OS 与 `linux-ohos` 组合、对 config/config.guess 增加 HarmonyOS 探测；以稳定子串锚定、幂等、跨 config 脚本代际自适应，避免统一 diff 因源码 config 脚本漂移而中止整个构建 |

## 测试

- **上游测试**：`make check` 注册 19 项原生测试（10 个 C 库 check 单元测试 + 9 个 RNAfold/RNAcofold/RNAalifold 可执行程序 TAP 测试）。
- Python/Perl 接口测试（共 46+14 项）属于另行打包的脚本接口组件，不在本 C 库包范围内。

## 依赖

- `check/0.15.2`（仅用于 C 库单元测试的链接）
