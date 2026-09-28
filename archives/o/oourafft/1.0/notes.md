# oourafft 1.0 OHOS 适配记录

## 任务

- 平台任务 `contrib-9172`，`oourafft 1.0`，`taskBranch=feat/oourafft-1.0`。
- 路径 A（普通积分赛）。

## 源码

- 上游：<https://github.com/petewarden/OouraFFT>，tag `v1.0`。
- `sources.url = https://codeload.github.com/petewarden/OouraFFT/tar.gz/refs/tags/v1.0`
- `sha256 = 5f4dabc2ae21e1f537425d58a49cdca1c49ea11db0d6271e2a4b27e9697548eb`
  - 与 Debian `oourafft_1.0.orig.tar.gz`（`deb.debian.org`，package `oourafft` 1.0-3）
    **逐字节一致**，故使用官方 codeload。

## 构建

上游无构建系统（无 Makefile / CMake / configure），只有 C 源文件。配方：

```
clang -O2 -fPIC -c <src>.c -o <src>.o
llvm-ar rcs lib<name>.a <src>.o
```

对应 6 个库：`fft2d_fftsg`(fftsg.c)、`fft2d_fftsg2d`(fftsg2d.c)、
`fft2d_fftsg3d`(fftsg3d.c)、`fft2d_fft4f2d`(fft4f2d.c)、
`fft2d_shrtdct`(shrtdct.c)、`fft2d_alloc`(alloc.c)。

### 符号冲突与安装子集

`fft4f2d.c` 定义了与 `fftsg.c` 同名的私有 helper（`makewt`、`makect`、
`bitrv2`、`cftf`、`cftb`、`rftf`、`rftb`），且其 `cdft2d`/`rdft2d` 与
`fftsg2d.c` 的函数签名不同（6 参 vs 7 参）。二者不能出现在同一个链接里
（实测 `multiple definition`）。因此只安装 **`fft2d_fftsg` +
`fft2d_fftsg2d` + `fft2d_alloc`**，与 Debian `libfft2d-dev` 的
`install(TARGETS ...)` 集合一致。其余 4 个仍会编译，作为编译覆盖证据。

## 上游测试

- `sample1/testxg.c`：1-D 正反变换误差检查，覆盖
  `cdft`、`rdft`、`ddct`、`ddst`、`dfct`、`dfst` 共 **6 项**。
- 运行方式（非交互）：`echo 64 | ./testxg`。
- 期望输出：6 行 `xxx err= <数值>`，数值 ~1e-16。配方断言 6 项均 `< 1e-9`。
- `sample1/testxg_h.c` 对应 `_h`（无工作区）变体，本配方不编译；`sample2/pi_fft.c`
  是基准程序（算 pi），不是测试。

## 消费者测试

`test_package/test_oourafft.c`：7 项断言（libm 可见性、`cdft`/`rdft` 正反变换、
`alloc_1d_double`/`free_1d_double`、`alloc_2d_double`/`free_2d_double`、2-D `cdft2d` 正反变换）。

## 结果

- 真机 `conan create` 退出码 0（见 PR 正文）。
- 上游 6/6、消费者 7/7。
