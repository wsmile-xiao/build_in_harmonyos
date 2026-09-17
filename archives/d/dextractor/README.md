# dextractor

Decompression and compression commands for PacBio `.bax.h5`, `.fasta` and
`.quiva` files（Gene Myers，PacBio SMRT 测序数据工具集）。

## OHOS 适配

- 使用上游 Makefile（经 `0001-makefile-portable-toolchain-and-install.patch`
  可移植化：字面 `gcc` → `$(CC)`，`PATH_HDF5`/`DEST_DIR` 可被 make 命令行覆盖）。
- 依赖 `hdf5/1.14.6`（仅 `dextract` 链接；传递依赖 `libaec/1.1.7`、`zlib/1.3.1.1`）。
- `dextract` 主程序入口先调用 `H5Zfilter_avail(H5Z_FILTER_DEFLATE)`，在目标平台
  运行时同时验证 libhdf5.so 动态加载与 zlib deflate 滤镜可用性（test_package T4）。
- 本次为路径 A 基础适配，仅修改 Makefile（构建可移植化），未改任何源码文件。

## 构建产物

| 工具 | 用途 |
|------|------|
| `dextract` | 从 `.bax.h5`（HDF5）提取 subread 与 QV 数据 |
| `dexta` / `undexta` | `.fasta` ↔ 2-bit `.dexta` 互转 |
| `dexqv` / `undexqv` | `.quiva` ↔ Huffman 压缩 `.dexqv` 互转 |

## 验证

- macOS 开发宿主：4 个非 HDF5 工具编译 0 警告；fasta 往返字节级一致；
  quiva 往返 10 条无损流一致 + delTag 按上游 2-bit 设计重建；错误路径 rc=1。
- 上游测试：0（上游无测试套件，清点证据见 1.0/notes.md）。
- Conan 消费测试：4 组 / 15 断言（test_package/test.sh）。

上游：https://github.com/thegenemyers/DEXTRACTOR
