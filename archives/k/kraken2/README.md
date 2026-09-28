# Kraken2

Kraken 2 taxonomic sequence classification system.

## 适配说明（2.1.3）

- 自研 Makefile 构建（src/Makefile），`make -C src` 产出 6 个命令行工具：
  estimate_capacity / build_db / classify / dump_table /
  lookup_accession_numbers / k2mask，无 install 规则，package() 手动拷贝。
- OpenMP：OHOS 无 OpenMP 运行时，`KRAKEN2_SKIP_FOPENMP=` 置空关闭
  `-fopenmp`，上游 src/omp_hack.cc 提供单线程兜底（多线程能力受限）。
- zlib：仅 k2mask 需要（gzstream.h gz* API），经 CPATH/LIBRARY_PATH 注入
  conan zlib/1.3.1 依赖。
- 上游无正式单元测试套件；test_package 以自造最小数据做端到端冒烟
  （build_db 构建索引 + classify 分类 3 条序列）。
