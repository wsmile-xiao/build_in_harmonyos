# PBSIM — PacBio 测序模拟器

`PBSIM` 模拟 PacBio 平台的测序读长，支持两种数据类型：

- **CLR**（Continuous Long Read）：长读长、高错误率。
- **CCS**（Circular Consensus Sequencing）：较短读长、低错误率。

它根据参考序列（FASTA）与读长/精度/深度等参数生成 FASTQ（以及 MAF）输出，
并按用户提供的质量码表（sample-profile）或内置模型加入测序错误。

## 主要功能

- 依据参考序列模拟 CLR / CCS 读长，输出 FASTQ。
- 可配置读长均值/标准差/最小/最大、精度均值/标准差、测序深度、差异比例、随机种子等。
- 支持 `--sample-fastq`、`--model_qc`、`--prefix` 等选项。

## OHOS 适配要点

- **autotools 构建**：发布包不含预生成 `configure`，配方先 `autoreconf -i`，
  再 `./configure CC=<ohos clang> CXX=<ohos clang++>` 并 `make`。
- **零三方依赖、零补丁**：C++ 源码，仅需 libc/libc++ 与 `-lm`。
- 版本坐标为 Debian 上游快照 `1.0.3+git20180330.e014b1d`，以 dfsg orig tarball sha256 固定。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/pbsim` | PacBio 读长模拟器 |

## 参考资料

- 上游仓库：<https://github.com/pfaucon/PBSIM-PacBio-Simulator>
- 许可证：GPL-2.0-or-later
