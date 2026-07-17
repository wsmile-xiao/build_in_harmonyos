# bedtools

bedtools 是一套用于基因组算术（genome arithmetic）的命令行工具集，支持对基因组区间进行 intersect、merge、sort、coverage、closest、subtract、flank 等操作，广泛用于生物信息学 BED/VCF/GFF/GFF2 数据分析。

- 上游仓库：https://github.com/arq5x/bedtools2
- 文档：https://bedtools.readthedocs.io/
- 许可证：MIT

## HarmonyOS PC 适配

- 构建系统：Makefile（内置 htslib 静态库）
- 编译器：clang/clang++（libc++）
- 依赖：zlib（经 Conan 提供）
- 已知限制：内置 htslib 关闭了 bzip2/lzma 后端，故 bzip2 压缩输入与 CRAM 格式不支持；BED/VCF/GFF/gzip 等核心格式全部正常
