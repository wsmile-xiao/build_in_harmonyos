# htslib — OpenHarmony 编译档案

## 软件简介
HTSlib 是用于读写高通量测序数据格式的 C 库，支持 SAM、BAM、CRAM、VCF、BCF 等格式，并提供 `bgzip`、`htsfile`、`tabix` 等命令行工具。

## OHOS 适配要点
- 使用 Autotools 构建，Conan 配方产出静态 `libhts.a` 和命令行工具。
- 通过 `--host=aarch64-unknown-linux-ohos` 避免 configure 运行临时 conftest 二进制失败。
- 使用 `AutotoolsDeps`/`PkgConfigDeps` 注入 Conan 依赖 `zlib/1.3.1`、`xz/5.6.2`、`libdeflate/1.25`。
- 禁用当前未适配或非必要能力：bzip2、libcurl、plugins、ref-cache。
- 修复 HarmonyOS/HMDFS 下 `umask 077`、`/tmp`、`ln -sf` 相关问题。

## 依赖关系
- zlib/1.3.1
- xz/5.6.2
- libdeflate/1.25

## 交付命令
- bgzip
- htsfile
- tabix
- annot-tsv

## 参考资料
- [HTSlib 官网](https://www.htslib.org/)
- [HTSlib GitHub](https://github.com/samtools/htslib)
