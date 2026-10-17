# DRAFT: 图像编解码 lossless roundtrip 探针图案设计：alpha=0 与 q=100 两坑

- **严重度**: 2
- **类别**: test, codec, methodology
- **软件**: libwebp 1.6.0.1（webmproject/libwebp，鸿蒙 PC 适配）
- **阶段**: test_package（R34）
- **状态**: UNMATCHED 草稿，待人工/AI 审核晋升

## 症状

libwebp 1.6.0.1 真机 conan-verify 首轮 G2 失败，探针 9/11：
- VP8L 逐字节断言 FAIL：首错位 (14,5) RGB want=163/194/225 got=156/187/218
  （三通道均匀 -7，但 R-G=-31、B-G=+31 差值关系保持，alpha 通道精确）；
- VP8 q=100 逐字节断言 FAIL：首错位 (0,0) G want=31 got=32（+1）。

初判真机 aarch64 NEON 无损路径 bug。**Windows 本机 PIL（独立 libwebp 构建）
逐字节复现同一错位**后锁定为探针图案设计错误，非库缺陷。

## 根因

1. **alpha cleanup**：测试图案 `(x*7+y*13+ch*31)&0xff` 的 alpha 通道在
   `x*7+y*13 ≡ 163 (mod 256)` 处为 0。VP8L 编码器对 alpha=0 透明像素不承诺
   RGB 保真——默认 WebPConfig.exact=0 下做 alpha cleanup，把透明像素 RGB
   改写成左邻预测值以利压缩（实测解码值 156/187/218 恰为左邻 (13,5) 的 RGB）。
   透明像素不可见，此改写合法且是文档明示行为（exact=1 才逐字节保留）。
2. **VP8 q=100 有损**：WebPEncodeRGBA(quality=100) 走 VP8 有损编码极限档，
   高频图案实测 RGB 偏差可达 134。近无损断言只对平滑渐变成立。

## 修正方案

```c
/* alpha 取 128..255 段避 0（防 alpha cleanup 改写透明像素 RGB） */
static unsigned char px_hf(unsigned x, unsigned y, int ch) {
    if (ch == 3) return (unsigned char)(((x * 7 + y * 13) & 0x7f) | 0x80);
    return (unsigned char)((x * 7 + y * 13 + ch * 31) & 0xff);
}
/* 逐字节无损断言只用 VP8L 专属 API；q=100 近无损断言用平滑渐变 + 容差 8（实测 ≤2） */
```

修正后真机探针 11/11 ALL GREEN；双向交叉验证（本机 PIL 编码参照流 → 真机解码、
真机编码流 → 本机解码）均逐字节精确。

## 验证

- libwebp 1.6.0.1 OHOS aarch64 test_package：11/11 断言通过
  （conan-verify G0-G4/L2/L4/L5 全绿，2026-09-27 华为 PC，Conan 2.29.1）
- 双平台复现：Windows 本机 PIL 12.2.0 与真机 libwebp 1.6.0.1 首轮错位逐字节一致

## 关键词

alpha cleanup, transparent pixel, VP8L, q100 lossy, round-trip, test pattern, libwebp, R34
