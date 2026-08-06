# fftw3f

FFTW 的**单精度（float）**构建，产出 `libfftw3f.so.3` 与 `libfftw3f_threads.so.3`。

FFTW 每次构建只出一种精度，所以三种精度是三个独立的包：
`fftw`（double）、`fftw3f`（float）、`fftw3l`（long double）。
pyfftw 这类消费方会同时链接三者。

- 上游：https://www.fftw.org/
- 许可证：GPL-2.0-or-later
- 鸿蒙 PC 适配版本：见各版本目录
