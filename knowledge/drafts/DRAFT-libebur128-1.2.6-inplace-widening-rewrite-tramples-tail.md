# DRAFT: 原地"窄→宽"类型改写踩掉未读样本（test_package 数据层陷阱）

- **库/版本**: libebur128/1.2.6（泛化到一切多精度输入接口的 DSP/音频库测试）
- **阶段**: testing（test_package 真机运行）
- **severity**: 2 ｜ **类别**: testing, portability, dsp, c, test-package
- **证据**: 真机 shadow CI job `libebur128-1.2.6-20260929`，r3（run `…-095945-3257`）11 断言仅 sample_peak 失败 → 修复后 r4（run `…-100235-5663`）11/11 全过

## 现象

test_package 在真机运行时单条数值断言失败（其余 10 条通过）：

```
ok - float 1 kHz sine -> gated global loudness in (-30, 0) LUFS
FAIL - sample_peak tracks 0.8 amplitude input
...
ERROR: ConanException: Error 1 while executing
```

本机 OHOS clang 交叉编译、链接全部通过——**编译层无任何征兆**。

## 根因

测试代码为"复用"float 正弦生成器，写了这样的模式：

```c
double *buf = malloc(4800 * 2 * sizeof(double));
fill_sine((float *)buf, 4800, 0.8);            /* 以 float 写入前 4N 字节 */
for (i = 0; i < 9600; ++i)
    buf[i] = (double)((float *)buf)[i];        /* 原地拓宽 —— BUG */
```

第 i 次迭代：读取偏移 `4i`，写入偏移 `8i`。当 `i > 2` 后，写入区间 `[8i, 8i+8)` 落在**尚未读取**的 float 数据 `[4i+4, 4N)` 内——后面的源样本被 double 位模式踩坏，峰值失真。

这不是库的问题，是**测试自身的数据通路 bug**；而且"11 断言只挂 1 条"的失败形态极易诱导人去怀疑库的 sample_peak 实现（若真去 patch 库就完全修反了）。

## 方案

1. **首选：按目标精度直接生成**（rec_auto_fix 不适用，需人工改测试源码）

   ```c
   for (i = 0; i < 4800 * 2; ++i)
       buf[i] = 0.8 * sin(2.0 * 3.141592653589793 * 1000.0 * (double)(i / 2) / SR);
   ```

2. **备选：第二缓冲中转**——读 `src[i]`（float*）写 `dst[i]`（double*），两缓冲不重叠。适用于窄类型生成器已存在、改动面大时。

3. 修复后本机用 Python 复算期望值（`max=0.800000000` ∈ 容差 `(0.799, 0.801)`）再上真机，避免浪费设备窗口。

## 禁止

- ❌ 放宽数值容差让测试变绿（掩盖数据通路 bug，同时废掉数值断言对库的约束力）
- ❌ 误判为库缺陷去 patch 上游（r3 形态：10/11 过、1 数值断言挂——先审测试数据通路）

## 泛化提示

音频/DSP 库普遍提供 `short/float/double` 三套输入接口（ebur128、libsndfile、opus、speexdsp…），消费者测试常为三种精度各写一份数据。**任何"向同一块 malloc 内存用不同宽度指针读写"的写法都踩同一颗雷**：写入偏移超前于读取偏移时必自踩。规则一句话：**窄转宽永不原地**。

## 关联

- similar_to: `DRAFT-rcheevos-12.2.1-float-to-unsigned-arch-ub`（同为浮点数据层架构/精度陷阱，但那条是库语义 UB，本条是测试代码内存别名 bug）
- 来源：`feat/libebur128-1.2.6-codex` @ `382036e771`，迭代记录见 `archives/l/libebur128/1.2.6/notes.md`
