# heatshrink

面向嵌入式与实时系统的 LZSS 压缩/解压库（OHOS aarch64 适配归档）。

- 上游: https://github.com/atomicobject/heatshrink
- 许可证: ISC
- 版本: 0.4.1（首次适配）
- 构建: 上游顶层 Makefile，无外部依赖
- 产物: `libheatshrink_dynamic.a`（动态分配，默认）、`libheatshrink_static.a`
  （固定缓冲/嵌入式）、`heatshrink` CLI（见 `commands.json`）
- 消费者注意: 两个库导出同名 API 但结构体布局不同，必须二选一链接，
  对应 Conan components `heatshrink::dynamic` / `heatshrink::static`
  （各自带 `HEATSHRINK_DYNAMIC_ALLOC=1/0` define）

各版本详情见 `0.4.1/manifest.yaml`、`0.4.1/notes.md` 与 `0.4.1/reports/`。
