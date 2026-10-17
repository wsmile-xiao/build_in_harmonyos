# uchardet 0.0.7 packaging

Conan 体系打包（ARCHIVE-SPEC v3.0：手动 tar.gz 打包已废弃）。

发布路径：PR 合入 main → CI release 流水线 `conan create` + `conan upload`
发布到 CNB 制品仓（`ohpcd` remote），消费方通过 `conan install --requires=uchardet/0.0.7` 获取。

本地目录中的 `uchardet-0.0.7-ohos-aarch64.tar.gz`（gitignored）为本地
`conan create` 产物快照，仅用于 submit 自检与人工核对，不进入 PR。

- 变体：`shared=False`（默认，静态库 + CLI）、`shared=True`（libuchardet.so.0.0.7 + SONAME）
- 产物：lib/libuchardet.{a,so*}、include/uchardet/uchardet.h、bin/uchardet、lib/pkgconfig/uchardet.pc
