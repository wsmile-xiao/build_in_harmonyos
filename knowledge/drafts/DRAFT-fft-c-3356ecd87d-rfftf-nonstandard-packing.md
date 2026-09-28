# DRAFT-fft-c-3356ecd87d-rfftf-nonstandard-packing

- **来源**: fft-c 3356ecd87d R01 适配（HarmonyOS PC aarch64）
- **分类**: math / FFT / FFTPACK / 输出排布 / API 契约
- **状态**: 本地草稿（挂路径 B 知识库扩展 PR，与 fft-c 归档同 PR 交付）

## 问题 / 错误签名

```
按 out[2k], out[2k+1] 取 bin k 谱线 → 15Hz 余弦读成 0（谱线错位）
实际排布: out[0]=R0(DC), out[N-1]=R_{N/2}(Nyquist),
          1<=k<=N/2-1: R_k=out[2k-1], I_k=out[2k]
```

## 根因

fft-c 的 `__fft_real_forward`（FFTPACK rfftf 移植）采用变体排布：DC 在开头、
Nyquist 实部在**末尾**、中间每 bin 实部在奇下标、虚部在偶下标（`out[2k-1]=R_k,
out[2k]=I_k`），与 netlib 标准排布（`[R0, R_{N/2}, R1,I1, R2,I2, …]`）不同；
上游头文件/文档未说明该排布，消费方按常见假设取谱线必然错位。

## 修复方案（消费方侧契约）

按实测排布取 bin：

```c
/* bin 0 (DC):      mag = fabs(out[0])
 * bin N/2 (Nyq):   mag = fabs(out[N-1])
 * 1<=k<=N/2-1:     re = out[2k-1]; im = out[2k]; mag = hypot(re, im) */
```

## 验证

- impulse 探针：`out[0..4]=1,1,0,1,-0`，`out[N-1]=1`（R_{N/2}）——
  排布 [R0, R1,I1, R2,I2, …, R_{N/2}] 完全吻合，两种常见假设均不符。
- 纯余弦 `5·cos(2π·15·i/N)`: `R15=out[29]=2560`（unscaled，即 5·N/2）✅；
  按错位假设读 `out[30],out[31]` = 0 ❌。
- 修正排布后 test_package 与鸿蒙专项测试 `MAG(bin15)=2.5`（scaled）断言通过。

## 适用边界 / 反例

- 适用：消费 fft-c / FFTPACK rfftf **变体排布**实现（Nyquist 在末尾）时必须按
  此契约取谱线。
- 反例/边界：netlib 标准排布（`[R0, R_{N/2}, R1,I1,…]`）的库**不适用**本排布公式；
  用 impulse 探针实测排布是最稳的定位手段（不要照抄库头注释或 README 示例的
  下标假设）。

## 查重差异

- index.tsv / E*.kv / 草稿均无 rfftf/rfft 排布条目；检索 "fftpack"/"backward"/
  "rfft" 仅有 E469（header-only server port-binding）、E533（hmdfs autotools）
  关键词误命中，cmsis-dsp NE10 cfft-radix5 草稿为 NEON 数值错误（领域相邻、
  问题与方案不同）。
- 新增差异：FFTPACK 变体排布契约 + impulse 探针定位法（可迁移到其他
  rfftf 系库/FFTPACK 移植）。