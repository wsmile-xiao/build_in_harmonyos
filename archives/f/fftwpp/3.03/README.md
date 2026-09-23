# fftwpp 3.03（FFTW++）

FFTW++ 是 FFTW3 的高层 C++ 头文件封装（University of Alberta, John C. Bowman 等），
提供 1D/2D/3D 复数-复数、实数-复数、复数-实数 FFT 与隐式去卷积，
处理内存对齐、计划、wisdom 与并行（OpenMP/MPI）的技术细节。

- 上游：https://github.com/dealias/fftwpp（版本 3.03，tag 无 v 前缀）
- 许可：GPL-3.0-or-later / LGPL-3.0-or-later
- 分类：math / 信号处理

## 包结构
- **package_type**: header-library（不编译，纯拷贝）
- `include/fftwpp/*.h` — 10 个公共头（fftw++.h、parallel.h、convolve.h 等）
- `src/fftwpp/*.cc` — 4 个伴随编译单元（fftw++.cc、parallel.cc、Array.cc、Complex.cc）

## OHOS 适配
- 上游 CMakeLists 只驱动 tests/examples 编译（无 install 规则），配方直接
  copy 头文件与伴随 .cc 进包，遵循上游示例用法（`g++ app.cc fftw++.cc -lfftw3`）
- **单线程模式**：包 `defines` 注入 `FFTWPP_SINGLE_THREAD`（上游 README 官方开关），
  与仓内 fftw/3.3.10 串行版对齐，同时避开 OHOS OpenMP RUNPATH 坑
- **消费者必读**：在构造任何 fft1d/fft2d 前设置
  `fftw::effort = FFTW_ESTIMATE;` —— fftw/3.3.10-OHOS 的
  WISDOM_ONLY→forget→MEASURE 计时路径会死锁，fftwpp 默认恰好走该链
  （详见 notes.md 二分定位证据链）

## 依赖
- fftw/3.3.10（仓内 conan 包，serial 版）
- 编译工具: clang, cmake

## 消费者示例
```cpp
#include <fftwpp/fftw++.h>
using namespace fftwpp; using namespace parallel; using namespace utils;

int main() {
    fftw::effort = FFTW_ESTIMATE;   // OHOS 适配要点
    fftw::maxthreads = get_max_threads();
    size_t n = 4;
    Complex *f = ComplexAlign(n);
    fft1d Forward(n, -1);
    Forward.fft(f);
    deleteAlign(f);
}
```
编译时把 `<pkg>/src/fftwpp/fftw++.cc` 与 `parallel.cc` 加入目标源文件，链接 fftw。

## 功能验证
```bash
conan create . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64> --build=missing
# test_package: 3/3 断言通过（解析谱 + 反变换还原）
```

## 参考
- 源码: https://github.com/dealias/fftwpp/archive/refs/tags/3.03.tar.gz
- 文档: http://fftwpp.sourceforge.net
