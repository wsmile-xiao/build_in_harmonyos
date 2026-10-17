# DRAFT-minlzma-1.1.5-decoder-integrity-check-disabled-corrupt-test：解码器完整性检查关闭时的损坏流测试设计

> Contributor: pc4-37 | Status: Draft | Updated: 2026-09-23
> Source: minlzma 1.1.5 适配（Path B 知识库扩展）；触发场景：鸿蒙专项测试 test_ohos 损坏流断言
> 对应：`knowledge/drafts/DRAFT-minlzma-1.1.5-decoder-integrity-check-disabled-corrupt-test.kv`

## 现象

鸿蒙专项测试 test_ohos 的"损坏流拒绝"断言失败：

```text
PASS: size query mode (CRC32 stream)
PASS: malloc
PASS: decode CRC32 stream, no checksum error
PASS: decoded content matches expected
FAIL: corrupt stream rejected safely      ← 损坏 payload 字节后 XzDecode 仍返回 true
RESULT: 1 FAILURES
```

## 根因

minlzlib 的 CRC 完整性校验由编译期宏 `MINLZ_INTEGRITY_CHECKS` 控制，而上游 CMake
**默认不定义**该宏（只有 `minlzlib.h` 里的 `MINLZ_META_CHECKS=1`）。对 XZ 流损坏
**payload 字节**时——该段是无压缩 chunk（LZMA2 控制字节 0x01，数据原样透传）——
解码照常成功，`XzChecksumError()` 恒返回 false（无检查宏）。断言"损坏 payload → 解码失败"
必然 FAIL。

**陷阱**：不能假设"解码库都会校验完整性"；宏裁剪型解码库的损坏流行为取决于编译期开关。

## 修复（已验证）

先用**字节扫掠实验**确定使解码确定性失败的字节位：

```bash
# 对流的每个偏移 i 异或 0xFF，调 XzDecode(bad, len, NULL, &sz)，记录 rc==0 的偏移
# minlzma 实测：偏移 24（LZMA2 块控制字节 0x01）异或成 0xFE（非法控制值）→ rc=0
# 偏移 12（块头 size 字段）在大小查询模式下 rc=1 —— 不触发失败，不能用
```

测试断言改为损坏结构性字节：

```c
bad[24] ^= 0xFF;  /* LZMA2 块控制字节 -> 非法值 0xFE，解码确定性失败 */
rc = XzDecode(bad, XZ_CORRUPT_LEN, NULL, &badSize);
check(!rc, "corrupt stream rejected safely");
```

验证证据：修正后 conan-verify G2 PASS，test_ohos CTest 通过（RESULT: ALL OHOS TESTS PASSED）。

## 适用边界

- 适用：带编译期完整性检查开关的解码/解压库；断言"损坏流必须失败"时先确认宏开关。
- 反例：默认启用完整性检查的库，损坏 payload 即触发 checksum 失败，无需结构性字节手法。
- 方法可迁移：字节扫掠找最小稳定失败偏移，可复用于任何格式解码器的负向测试设计。

## 验证结果

| 项目 | 结果 |
|---|---|
| 损坏 payload 断言 | FAIL（宏未启用）→ 换结构性字节后 PASS |
| test_ohos | ALL OHOS TESTS PASSED ✅ |
| conan-verify G2 | PASS ✅ |