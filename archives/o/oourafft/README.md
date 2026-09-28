# oourafft

Ooura 的通用 FFT 包（General Purpose FFT），提供 1/2/3 维、长度为 2 的幂的
离散 Fourier / Cosine / Sine 变换。上游仓库 `petewarden/OouraFFT` 只是把
原作者 Takuya Ooura 的 C 源码（`fftsg.c`、`fftsg2d.c`、`fftsg3d.c`、
`fft4f2d.c`、`shrtdct.c`、`alloc.c`）与两个 sample 目录收在一起，**没有任何
构建系统**。

## 适配要点

- 配方直接用 OHOS clang 把各源文件编译为静态库：
  `fft2d_fftsg`、`fft2d_fftsg2d`、`fft2d_fftsg3d`、`fft2d_fft4f2d`、
  `fft2d_shrtdct`、`fft2d_alloc`。
- `fft4f2d.c` 自带一份与 `fftsg.c` 同名的私有 helper（`makewt`/`bitrv2`/
  `cftf` …）且其 `cdft2d` 与 `fftsg2d.c` 的签名不同，**不能与
  `fftsg`/`fftsg2d` 同时链接**；只安装 `fft2d_fftsg` + `fft2d_fftsg2d` +
  `fft2d_alloc`（与 Debian `libfft2d-dev` 的安装集合一致）。
- 上游公共 API 无头文件（只有 `alloc.h`），原型按源码注释约定自行声明。
- 无三方依赖，仅需 `libm`。

## 上游测试（构建时实跑）

`sample1/testxg.c` 是上游 1-D FFT 测试：对 `cdft/rdft/ddct/ddst/dfct/dfst`
各做一次正变换 + 逆变换并打印最大误差（6 项检查）。配方以
`echo 64 | ./testxg` 非交互运行，并断言 6 个误差全部小于 `1e-9`。

## 消费者测试

`test_package/test_oourafft.c` 共 7 项断言：libm 可见性、1-D `cdft`/`rdft`
正反变换、`alloc_*` 辅助函数、以及 2-D `cdft2d` 正反变换。
