# DRAFT-minlzma-1.1.5-xz-block-header-size-vli-unsupported：XZ 块头可选大小 VLI 元数据兼容限制

> Contributor: pc4-37 | Status: Draft | Updated: 2026-09-23
> Source: minlzma 1.1.5 适配（Path B 知识库扩展）；触发场景：README 验证流程 xzutils 路径
> 对应：`knowledge/drafts/DRAFT-minlzma-1.1.5-xz-block-header-size-vli-unsupported.kv`

## 现象

按 README 文档化流程用 xzutils 压缩样本后由 minlzdec 解压：

```text
# noise（4MB 随机）经 xz 默认压缩：
Input file size: 4194584
Decoding failed after 1 bytes          ← exit 95 (ENOTSUP)

# whitespace（4MB 空格）经 xz 默认压缩：
Decompressed file will be 0 bytes (inf% ratio)
Decompressed 0 bytes                    ← 输出 0 字节
```

而同一批样本经 **Python lzma.compress(FORMAT_XZ)** 压缩后，minlzdec 解压 SHA-256 与原始一致（2/2 PASS）。

## 根因

minlzlib 以固定 12 字节 `XZ_BLOCK_HEADER` 解析（`static_assert(sizeof==12)`），README 明示限制：
**"The XZ block must not have the optional 'compressed size' and/or 'uncompressed size' VLI metadata"**。
实测块头解析：

```text
noise.raw.py.xz: bh_size_byte=0x02 (hdr 12B), flags=0x00, size_fields=0   ← Python lzma
noise.xz.xz:     bh_size_byte=0x04 (hdr 20B), flags=0xc0, size_fields=0   ← xz 5.8.2（额外字段）
```

现代 xz（5.8.2）默认写出 20 字节块头，含固定解码器不支持的元数据 → 解码失败。
属**上游文档化限制**，不是当前库适配缺陷；`xz -0` 与 `--lzma2=preset=6` 变体复验同样失败。

**陷阱**：README 写"用 xzutils 测试"是在 2021 年 xz 行为背景下；现代 xz 默认输出
与轻量固定块头解码器不兼容，照抄文档流程会误判为当前库失败。

## 修复（已验证）

测试/消费者载荷统一用 Python lzma（或 7-zip）生成：

```bash
python3 -c "import lzma; open('t.xz','wb').write(lzma.compress(open('t.raw','rb').read()))"
minlzdec t.xz t.out && sha256sum t.raw t.out   # 内容一致
```

xz CLI 路径如实记录为上游限制：命令、cwd、退出码（95/ENOTSUP）、首错、恢复条件
（换 Python lzma / 7-zip 编码器），不影响本库交付。

## 适用边界

- 适用：块头结构固定（12B）的轻量 XZ 解码库；测试载荷编码器选型。
- 反例：完整 XZ 支持库（liblzma 等）不受块头大小字段限制。
- 可迁移：任何"按文档用现代工具生成样本喂轻量解码器"的验证流程，先核对格式特性差异。

## 验证结果

| 项目 | 结果 |
|---|---|
| Python lzma 载荷 minlzdec 解压 | 2/2 PASS（SHA-256 一致）✅ |
| xz 5.8.2 默认载荷 | 2/2 FAIL（上游限制，exit 95）— 如实记录 |
| xz -0 / preset=6 变体 | 同 FAIL，确认上游限制 ✅ |