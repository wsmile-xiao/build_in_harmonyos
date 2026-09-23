# primer3

PCR 引物设计与分析工具集（Primer3）。

## 简介

Primer3 是广泛使用的 PCR 引物/杂交探针设计工具，由 Whitehead Institute
for Biomedical Research 开发并开源。核心能力：

- **引物对自动设计**：给定 DNA 模板序列（Boulder IO 格式），按用户指定的
  引物长度、Tm、GC 含量、产物尺寸范围等约束挑选最优引物对
- **解链温度计算**（oligotm）：SantaLucia/Breslauer 等多种热力学模型
- **序列比对**（dpal/ntthal）：经典与热力学（nearest-neighbor）比对，
  用于二聚体/发夹结构评估
- **序列掩蔽**（primer3_masker，基于 kmer 列表的物种特异性掩蔽）
- **扩增子设计**（amplicon3_core）

主入口 `primer3_core` 以 Boulder IO（`SEQUENCE_TEMPLATE=...` 记录 + `=` 分隔）
方式在 stdin/文件上流式处理，是生物信息学流水线中的经典组件。

## 上游

- 官网: https://primer3.org
- 源码仓库: https://github.com/primer3-org/primer3
- 本归档版本: 2.6.1（上游 tag v2.6.1）

## 许可证

GPL-2.0（源码 LICENSE 文件；amplicon3 部分另有 GPL-3 许可文件，
整体以 GPL-2.0 分发）。

## 产物形态

| 类别 | 内容 |
|------|------|
| 静态库 (lib/) | libprimer3.a、libdpal.a、libthal.a、libthalpara.a、liboligotm.a、libamplicontm.a、libmasker.a |
| 可执行 (bin/) | primer3_core、ntdpal、ntthal、oligotm、amplicon3_core、long_seq_tm_test、primer3_masker |
| 头文件 (include/) | libprimer3.h、oligotm.h、dpal.h、thal.h、thal_parameters.h 等 11 个公共头 |

## OHOS PC (arm64) 适配说明

- **零补丁适配**：CC/CXX/AR/RANLIB 均为上游 Makefile 变量，命令行注入
  OHOS 工具链即可完成 aarch64 交叉编译
- **构建系统**：上游 tarball 顶层无 configure（非 autotools），Makefile
  位于 `src/` 子目录
- **验证**：上游回归测试 218/218 全过（perl 套件：p3test/a3test/oligotm/
  dpal/thal/masker/cmdline）；conan test_package 消费者测试（真实 API
  链接 + primer3_core Boulder IO 端到端）通过
- 详见 [2.6.1/notes.md](2.6.1/notes.md) 与
  [2.6.1/reports/test-report.md](2.6.1/reports/test-report.md)

## 消费示例

```bash
# 设计引物（Boulder IO）
printf 'SEQUENCE_ID=demo\nSEQUENCE_TEMPLATE=<模板序列>\nPRIMER_TASK=generic\nPRIMER_PRODUCT_SIZE_RANGE=75-150\n=\n' | primer3_core

# CMake 链接静态库（libprimer3.cc 为 C++11，需 C++ 链接器）
find_package(primer3 REQUIRED)
target_link_libraries(app PRIVATE primer3::primer3)
```
