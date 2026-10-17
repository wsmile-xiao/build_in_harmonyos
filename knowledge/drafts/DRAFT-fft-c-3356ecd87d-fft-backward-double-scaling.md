# DRAFT-fft-c-3356ecd87d-fft-backward-double-scaling

- **来源**: fft-c 3356ecd87d R01 适配（HarmonyOS PC aarch64）
- **分类**: math / FFT / FFTPACK / API 缩放语义 / runtime / testing
- **状态**: 本地草稿（挂路径 B 知识库扩展 PR，与 fft-c 归档同 PR 交付）

## 问题 / 错误签名

```
fft_forward(FFT_SCALED_OUTPUT) + fft_backward(FFT_SCALED_OUTPUT) 往返结果 = n × 原信号
impulse 往返: y[0] = n（应为 1）；双频信号往返 maxerr ≈ n × 幅值
```

## 根因

`fft_backward` 调用的 FFTPACK `rfftb` 是**非归一**逆变换：`rfftb(rfftf(x)) == n*x`。
上游 fft-c 又在 `scale_output == FFT_SCALED_OUTPUT` 分支对 rfftb 结果乘 n，
与 `fft_forward` 的除 n 叠加成双重缩放（前向 ÷n，反向 ×n ⇒ 往返 ×n）。

## 修复方案

删除 `fft_backward` 中 SCALED 分支的 `input[i] *= n`：反向不做任何缩放，
`rfftb(rfftf(x)/n) == x`，往返还原。

```c
void fft_backward(FFTTransformer *t, FFT_PRECISION* input){
    __fft_real_backward(t->n, input, t->wsave, t->ifac);
    /* 不再乘 n：rfftb 本身是非归一逆（rfftb(rfftf(x))==n*x），
       前向已除 n，反向再缩放会双重缩放 */
}
```

## 验证

- 修复前：SCALED impulse 往返 y[0]=1024（n×1）❌
- 修复后：双频信号（10·sin2Hz + 5·cos15Hz, n=1024）往返 maxerr=7.1e-15 ✅
- 附带确认（未修复时若按 `out[2k],out[2k+1]` 取 bin 会连读错谱线，见排布草稿）

## 适用边界 / 反例

- 适用：任何 FFTPACK 封装（rfftf/rfftb 非归一约定）做"缩放前向 + 反向还原"的场景；
  fft-c、类似单文件封装。
- 反例/边界：非 SCALED（UNSCALED）模式往返本应得 n×x（FFTPACK 约定，非 bug）；
  使用方若手工做 1/n 归一，不适用本修复。**教训**：判断"缩放 bug"前必须先确认
  底层 rfftb 的归一约定（实测 rfftb(rfftf(x))==n*x 而不是 x）。

## 查重差异

- index.tsv / E*.kv / 草稿均无 FFTPACK/fft_backward/往返条目（E469 header-only
  server port-binding、E533 hmdfs autotools 为关键词误命中；cmsis-dsp NE10
  cfft-radix5 草稿为 NEON 数值错误，领域相邻、问题与方案均不同）。
- 新增差异：FFTPACK 封装库 API 缩放语义 + 往返一致性数值断言法（可迁移到其他
  rfftb 系库）。