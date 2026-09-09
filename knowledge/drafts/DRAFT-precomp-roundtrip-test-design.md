# DRAFT: 压缩再压缩工具的 test_package 设计：round-trip 字节一致 + 压缩增益断言

- **严重度**: 2
- **类别**: test, compression, methodology
- **软件**: precomp 0.4.7（schnaader/precomp-cpp）
- **阶段**: test_package（R34）
- **状态**: UNMATCHED 草稿，待人工/AI 审核晋升

## 设计要点

预压缩器（precomp / reflate / srep 类"压缩再压缩"工具）的消费者测试
黄金断言面是三层：

1. **round-trip 字节一致**（核心正确性）：
   `precomp -o out.pcf in.gz` → `precomp -r -o restored.gz out.pcf`
   → `sha256(restored.gz) == sha256(in.gz)`。这是无损语义的机器可判
   断证明。
2. **流检出计数**：stdout 出现 `Recompressed streams: 1/1`，证明工具
   真的识别并解出了内层压缩流（而非原样拷贝）。
3. **压缩增益**（核心价值主张）：`len(gzip(pcf, 9)) < len(gzip(orig, 9))`
   ——pcf 的载荷解压后可被更强压缩器压得更小。

## 输入构造（关键）

```python
random.seed(...)  # 可复现
words = ["the", "quick", "brown", ...]          # 词表
content = " ".join(random.choice(words)
                   for _ in range(20000)).encode()  # ~115KiB 词级随机
with gzip.open(src, "wb", compresslevel=1) as f:    # 弱压缩
    f.write(content)
```

- 完全随机字节：无流可解，precomp rc=2（error class）；
- 高重复/极小文件：pcf 元数据（头 + 重压缩参数）开销吞掉增益；
- gzip level 1 + 词级随机文本：deflate 流可被 preflate 精确解码，
  且解出载荷对 gzip -9 仍有大量冗余 → 增益断言稳定成立
  （实测 16184 < 23129，约 30% 提升）。

## 验证
precomp 0.4.7 OHOS aarch64 test_package：5/5 断言通过
（HMBS_TEST_PACKAGE_RESULT: total=5 passed=5 failed=0）。

## 关键词
precomp, round-trip, sha256, pcf, compression gain, gzip level 1, R34
