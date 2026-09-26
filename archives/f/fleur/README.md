# fleur

Fleur 是一个纯 C 实现的 Bloom Filter 库，与 DCSO 的
[Go](https://github.com/DCSO/bloom) / [Python](https://github.com/DCSO/flor)
实现完全兼容（同一套文件头与位数组布局）。

- 上游: https://github.com/hashlookup/fleur（BSD-3-Clause）
- 版本: 0.3
- 提供: 静态库 libfleur.a（依赖 libfnv.a/libmyutils.a）与 CLI 工具 fleurcli
- API: fleur_initialize / fleur_add / fleur_check / fleur_bloom_filter_to_file /
  fleur_bloom_filter_from_file / fleur_join / fleur_fingerprint / fleur_destroy_filter
