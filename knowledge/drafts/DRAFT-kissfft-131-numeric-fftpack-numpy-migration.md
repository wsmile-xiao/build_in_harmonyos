# DRAFT-kissfft-131-numeric-fftpack-numpy-migration：上游 Python2 测试脚本依赖 Numeric/FFTPACK 的 numpy 等价迁移

> Contributor: pc2-36 | Status: Draft | Updated: 2026-09-18
> Source: kissfft 131 HarmonyOS PC 适配（r02 返工，task kissfft-131-r02-rec-pc2-36-20260918T024500Z）
> 本文件与 `DRAFT-kissfft-131-numeric-fftpack-numpy-migration.kv` 配对，stem 完全相同，
> 字段（主题 / error_signature / root_cause / solution / validation / 适用边界）相互对应。

## 现象

kissfft 131 上游测试脚本 `test/compfft.py`、`test/fastfir.py` 在 OHOS Python3 环境直接运行失败：

```text
python3 compfft.py
  ModuleNotFoundError: No module named 'FFT'     # from FFT import * / import FFT
python3 fastfir.py
  ModuleNotFoundError: No module named 'Numeric' # from Numeric import *
```

上游 2019 年脚本依赖 Python2 时代专有模块 Numeric（数组/线性代数）与 FFT（FFTPACK 封装），
Python3 环境（且 pip 无对应分发：`pip3 download fftpack/numeric` → No matching distribution found）下不可用。

## 根因（error_signature / root_cause）

- 上游测试脚本为 Python2 编写，依赖 Python2 专有第三方模块 Numeric/FFTPACK；
- 既有 E269（port-python-script）明确其方案仅适用于「不依赖 Python 2 C 扩展或 Python 2 专有
  第三方包」的测试 runner，故 Numeric/FFTPACK 属 E269 边界之外，需要模块级迁移而非仅语法级
  py2→3 修复。

## 方案（solution / rec_approach）

以 numpy（OHOS 已安装 numpy 2.5.2 aarch64 wheel）做**语义等价**最小迁移：

1. `from Numeric import *` → `import numpy as np`；
2. FFTPACK 封装调用 → numpy.fft 等价：
   - `FFT.fftnd(x)` → `np.fft.fftn(np.asarray(x,dtype=complex))`
   - `FFT.real_fft(...)` → `np.fft.fft(...)`（复数基线）
   - `inverse_fft(fm)` → `np.fft.ifft(fm)`、`fft(h,nfft)` → `np.fft.fft(h,nfft)`
3. Numeric 数组/归约 → numpy：`array/reshape/size/conjugate/sum/convolve/vdot/concatenate`
   对应 `np.*`；
4. `popen2.Popen3` → `subprocess.Popen(stdin=PIPE, stdout=PIPE)`，二进制读写用 `wb/rb`
   （Python3 下 struct.pack 返回 bytes，`''.join` → `b''.join`）；
5. `dict.has_key` → `in`（与 E269 语法级修复一致）。

不改变测试语料与断言语义（SNR 对比阈值保留），只替换数值/进程包装层；库源码不动。

## 验证（validation）

```bash
python3 compfft.py -n 4   -u ./kf_float   # NFFT=[4],   SNR = 144.6/148.6 dB
python3 compfft.py -n 2,3 -u ./kf_float   # NFFT=[2,3], SNR = 144.5/146.1 dB
python3 compfft.py -n 3,4,4 -u ./kf_float # NFFT=[3,4,4], SNR = 143.0/142.5 dB
python3 fastfir.py -l 500 -n 128          # snr=135.5 dB
# 全部 exit 0；已纳入双口径台账 executed_passed_total（17/20 = 85.0%）
```

依赖：kf_float 工具（tools/fft_float，clang 构建）、fastconv/fastconvr 工具。

## 适用边界 / 反例

- 仅限纯数值模块（Numeric/FFTPACK 可被 numpy 语义等价替代）；
- 若脚本依赖 Python2 C 扩展（旧版 PIL、numpy<0 生态等）则 numpy 迁移不适用，须另寻替代；
- 若仅是 print/has_key 语法级问题（无专有模块），走既有 E269 即可，无需本迁移。

## 查重与关系

- 四范围查重：graph/index.tsv 零命中（grep Numeric/FFTPACK 无条目）；doc/ 零命中；
  graph/*.kv 零命中；drafts/ 仅 E2164-draft.md 的 "Numeric" 命中（版本解析容错的
  非数字字符串，与本候选无关）。
- 七轴：exact=false；causal=部分（与 E269 同为 py2 脚本移植）；trigger_overlap=部分
  （模块缺失 vs 语法报错）；solution_overlap=部分（numpy 模块迁移 vs print 语法修复）；
  combination_novelty=true；boundary_novelty=true；test_migration_novelty=true。
- similar_to: E269
- path: B（知识库扩展；模块级 numpy 迁移为新增差异，已由本轮真实日志验证）