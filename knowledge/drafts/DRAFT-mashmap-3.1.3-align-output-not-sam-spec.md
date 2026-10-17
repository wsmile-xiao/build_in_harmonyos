# DRAFT — 上游「SAM 输出」不符合 SAM 规范，断言须按实际形状写

> Status: **Draft**（待主编 promote） | severity: `3` | category: `testing` | Updated: 2026-10-02
> 源文件：`knowledge/drafts/DRAFT-mashmap-3.1.3-align-output-not-sam-spec.kv`
> 来源：mashmap 3.1.3 适配（`feat/mashmap-3.1.3`）

---

**关键词**：SAM, SAM spec, @HD, @SQ, @PG, CIGAR, mashmap-align, id:f, kc:f, 上游输出缺陷, 消费者断言

## 现象（error_signature）

```text
CheckError: the SAM output has no @SQ reference header: []
```

编译通过、运行通过、输出文件也有内容，只有按 SAM 规范解析的断言失败。

## 根因（root_cause）

mashmap-align 的定位是「把 mashmap 的比对结果转成 SAM」，但它的写出代码**没有实现 SAM 头**，
而且把 edlib 的 CIGAR 追加在最后一个 tab 分隔列的尾部。v3.1.3 实测一行 14 列：

```text
chr1  600000  0  600000  +  chr1  600000  2624  599697  7  600000  16  id:f:0.976558  kc:f:1.0353 0.0271378 1M5I1M1M9I...
```

| 列 | 含义 |
|----|------|
| 1–5 | query name / length / start / end / strand |
| 6–9 | target name / length / start / end |
| 10–12 | 保留位 / 比对块长 / mapq |
| 13 | `id:f:<float>` |
| 14 | `kc:f:<float> <float> <CIGAR>` —— CIGAR 是这一列里空格分隔的**第三个** token |

没有 `@HD` / `@SQ` / `@PG`，CIGAR 也不在 SAM 规定的第 6 列。
根因是上游从未对齐 SAM 规范，也没有针对该输出的回归测试，
它只被自己的下游脚本按固定列位置读。

## 影响面（affected_scope）

所有「上游工具产出自称 X 格式但实际不 conform」的适配。症状很有迷惑性：
编译通过、运行通过、文件有内容，只有按规范解析的断言会失败 ——
很容易被误修成「适配侧解析器写错了」，从而放过真实的上游缺陷。

## 推荐方案（rec_approach）

1. **按上游实际输出形状写断言**。先探形状再写断言：

   ```bash
   awk -F'\t' '{print NF}' <output> | sort -u    # 列数是否稳定（本例恒为 14）
   ```

   然后逐列做语义断言：本例校验名称/长度与 `.fai` 一致、链方向为 `+/-`、
   坐标不越界、第 13 列匹配 `id:f:<float>`、CIGAR 用 `rsplit(' ', 1)` 从末列取出并校验正则，
   最后交叉验证 **CIGAR 的参考跨度与记录坐标跨度一致**（实测差 1，上游的 off-by-one）。
2. **不要把断言改成「符合 SAM 规范」**——那会让测试恒红或被迫放宽断言，掩盖上游缺陷。
3. **把缺陷写进 `notes.md` 的「注意事项」与 PR 正文「补充说明」**，
   明确告知下游消费者应按上游实际格式解析。
4. 该缺陷属上游代码缺陷，**不在适配范围内修**（红线：不改上游语义）。

## 禁忌（forbid）

```python
assert any(line.startswith("@SQ") for line in header)   # ❌ 恒红
cigar = fields[5]                                       # ❌ SAM 规范列位，不是 CIGAR
```

后果：W3/CI 恒红，且根因被错误归因为适配侧解析逻辑，进入无谓调参螺旋（R43）。

## 关联

- `similar_to:` `DRAFT-xmill-0.8-upstream-cli-defects-invisible-to-build`
- `principles:` P001, P003
