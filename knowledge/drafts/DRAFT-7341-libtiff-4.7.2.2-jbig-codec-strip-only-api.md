# DRAFT-7341 — libtiff JBIG 编解码仅 strip 级 API：scanline 探针必挂、整图须单条 strip

> 状态：草稿（来自 libtiff 4.7.2.2 真机适配，task_id=7341）

## 问题

功能往返探针在真机第二轮暴露（同一写法在本地 Linux 同样复现，属消费方 API 约束
而非平台差异）：

- 写 JBIG：`TIFFWriteScanline` → `ISO JBIG scanline encoding is not implemented`
- 读 JBIG：`TIFFReadScanline` → `ISO JBIG scanline decoding is not implemented`
- JPEG 写侧在 COMPRESSION 之前设 `TIFFTAG_JPEGCOLORMODE` → `Unknown pseudo-tag 65538`

## 根因

1. libtiff 的 JBIG codec（tif_jbig.c）只注册 strip 级入口：encodestrip/decodestrip；
   encoderow 为 NULL → TIFFWriteScanline 落到 _TIFFNoRowEncode 兜底（tif_compress.c）；
   decoderow 保留 TIFFDefaultDirectory 的 _TIFFNoRowDecode 桩。
2. JBIG 编码器还要求整图**恰好一条 strip**（JBIGSetupEncode 校验 rowsperstrip==height）。
3. JPEGCOLORMODE 是 JPEG codec 自己注册的**伪标签**：写侧须在 COMPRESSION（挂载
   codec）之后设置；读侧须先触发目录读取（首个 TIFFGetField）再设置——错误消息是
   `"Unknown %stag"`（tif_dir.c）拼接的，字面不出现标签号，按完整字符串 grep 会漏。

## 方案

- JBIG 读写都用 strip API：写侧 `TIFFTAG_ROWSPERSTRIP=height`（单条 strip）+
  `TIFFWriteEncodedStrip(t, 0, buf, rowbytes*h)`；读侧整条 `TIFFReadEncodedStrip`。
- JPEGCOLORMODE 时序：写侧放在 COMPRESSION 之后；读侧放在目录读取之后。

实现见 `archives/l/libtiff/4.7.2.2/test_package/test.c`（write_jbig1 / verify_jbig1 /
write_rgb8 / verify_rgb8）。

## 验证

- 第二轮（scanline 写法）：74/77——JBIG 编解码双挂 + JPEGCOLORMODE 时序挂；
- 第三轮（strip 写法 + 时序修正）：`conan test` 83/83 断言全绿（含 7 后端矩阵
  DEFLATE/ZSTD/LZMA/JPEG/WEBP/LERC/JBIG 往返），exit 0。

## 适用边界

- 仅 JBIG codec 有此约束；DEFLATE/ZSTD/LZMA/WEBP/LERC 的 scanline 路径正常。
- JPEGCOLORMODE 时序约束仅影响 JPEG 消费者；与平台无关（Linux 同规则）。
- 不影响任何既有消费方——约束来自 libtiff 自身 codec 注册结构。

## 查重差异

- DRAFT-13503-libamrnb-amr-codec-test-properties：AMR codec 的构建期测试属性
  （waf 测试配置维度），与本条"消费期 API 注册结构"不同维度。
- 既有 E 系列条目均为平台/musl/toolchain 错误码，无 libtiff codec 消费 API 条目。
- 与本 MR 的 hmdfs 软链条目（DRAFT-7341-libtiff-4.7.2.2-hmdfs-nosymlink-versioned-sharedlib）
  同包不同题：一条平台适配、一条消费 API。
