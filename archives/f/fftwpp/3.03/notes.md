# fftwpp 3.03 适配笔记

## 库简介

FFTW++（dealias/fftwpp）是 FFTW3 的 C++ 头文件封装：1D/2D/3D 复数/实数 FFT、
隐式去卷积、可选 MPI 转置。3.03 上游 tag 即 `3.03`（无 v 前缀，仓库实测
`git ls-remote --tags` 枚举：3.00/3.01/3.02/3.03/2.xx/SISCarchive）。

上游无 install 规则的 CMakeLists（只编 tests/examples），README 明示用法：
```
g++ example0.cc ../fftw++.cc -lfftw3
```
即"头文件 + 伴随 .cc + fftw3"三件套。

## 包结构（本配方）

| 路径 | 内容 |
|------|------|
| include/fftwpp/ | fftw++.h parallel.h align.h seconds.h statistics.h utils.h Complex.h Array.h convolve.h cmult-sse2.h |
| src/fftwpp/ | fftw++.cc parallel.cc Array.cc Complex.cc（伴随编译单元） |
| licenses/ | LICENSE（GPL-3.0+）、LICENSE.LESSER（LGPL-3.0+） |

消费者接线（test_package 即此用法）：
1. `#include <fftwpp/fftw++.h>`
2. 编 `<pkg>/src/fftwpp/fftw++.cc` + `parallel.cc` 进自己 target
3. 链接 `fftw::fftw`（-lfftw3）
4. 包 `defines` 注入 `FFTWPP_SINGLE_THREAD`（无需手动 -D）

## 关键适配决策（含证据）

### 1. 单线程模式（FFTWPP_SINGLE_THREAD）
- fftw/3.3.10（OHOS 串行版）无 fftw3_threads/fftw3_omp（nm -D 实测 0 个
  thread 符号）；fftwpp 多线程路径需要 fftw_init_threads + omp
- OHOS 上 OpenMP 的 RUNPATH 坑（fftw 3.3.10.2 notes 已记录：libomp.so
  只在 SDK 内，产物 RUNPATH 会烤成 SDK 绝对路径）
- 上游 README 官方支持：`-DFFTWPP_SINGLE_THREAD` 禁用多线程
- parallel.h：SINGLE_THREAD 下不 include omp.h，get_max_threads() 返回 1

### 2. fftw::effort = FFTW_ESTIMATE（消费者侧必设，test.cpp 已示范）
**实测发现的 fftw/3.3.10-OHOS 死锁**（二分定位的完整证据链）：
- 纯 C 复现程序：import("")→export→forget→MEASURE 计划 → **挂死**
  （fftw_forget_wisdom 之后再用 FFTW_MEASURE 计时计划即挂）
- ESTIMATE 全链路正常（forget→ESTIMATE plan→execute 全过，2 秒内）
- fftwpp 默认 fftw::effort=FFTW_MEASURE，且 fftw::planner 默认函数
  Planner() 强制走 WISDOM_ONLY→失败→forget→re-plan 链 → 必踩死锁
- 此症与 fftw/3.3.10.1 配方 notes 记录的"OHOS 计时源回退"问题同源
  （该版已改 CMake 构建修复；3.3.10 autotools 版仍带此症）
- **避让**：消费者在构造 fft1d 前设 `fftw::effort = FFTW_ESTIMATE;`
  实测完整前向+归一化反向变换全绿（X1=(-2,2) 解析解吻合，还原 err=0）

### 3. CMakeDeps 不导出 srcdirs
- conan 2.29.1（OHOS 适配版）：cpp_info.srcdirs=["src"] 不生成
  `fftwpp_SRC_DIRS` CMake 变量，`fftwpp_PACKAGE_FOLDER` 也只有
  `_RELEASE` 后缀版
- 正确做法：test conanfile 用 `self.dependencies["fftwpp"].package_folder`
  定位，经 `cmake.configure(variables={"FFTWPP_SRC_DIR": ...})` 传给 CMake

### 4. 伴随 .cc 的引号 include
- fftw++.cc 里 `#include "fftw++.h"` 引号包含，默认相对 .cc 自身目录找，
  而头在 include/fftwpp/ 下 → CMake 给 target 加
  `target_include_directories(... "${FFTWPP_PKG_ROOT}/include/fftwpp")`

### 5. 运行时库路径（musl loader）
- C++ 消费者 NEEDED libc++_shared.so；conanrun 只注入 fftw 的 libdir
- test() 显式拼 LD_LIBRARY_PATH：依赖 libdirs + SDK libc++ 目录 +
  /system/lib64，bash -c 包装执行（fftw 3.3.10.2 同款经验）

## 验证

- 本地 conan create（-pr:h/-pr:b=ohos-aarch64，--build=missing）：全绿
- test_package 真机运行 3/3 断言：
  1. FFTWPP_SINGLE_THREAD 生效（maxthreads==1）
  2. 1D 前向 FFT 解析谱正确（f[i]=i → X0=6, X1=-2+2i, X2=-2, X3=-2-2i）
  3. fftNormalized 反变换还原（max err = 0.000e+00）

## 上游测试用例说明

上游 tests/ 目录为 FFTW++ 自身的精度/性能测试程序（tests.py 驱动，含
hybrid 卷积 26 组 + transpose + timing），依赖构建产物与运行环境；
上游 CMakeLists 的 TESTS 选项默认编 22 个测试二进制。本适配按本仓
惯例以 test_package 数值断言（对齐上游 example0.cc 行为）验证。
