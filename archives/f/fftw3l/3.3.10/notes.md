# fftw3l 3.3.10 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出 libfftw3l.so 等 2 个库，供链接与 dlopen。

## 关键适配

- **补丁 `fftw-0001-fix-swapped-soversion-version.patch`：修正上游写反的 SOVERSION/VERSION。**

  上游 CMakeLists 第 359 行写的是
  `set_target_properties (${subtarget} PROPERTIES SOVERSION 3.6.9 VERSION 3)` ——
  两个属性反了。CMake 里 `VERSION` 决定实体文件名（`lib.so.<VERSION>`）、
  `SOVERSION` 决定 soname 后缀（`lib.so.<SOVERSION>`），所以这么写会产出
  实体 `libfftw3.so.3`、soname `libfftw3.so.3.6.9`，与 autotools 构建
  （soname `libfftw3.so.3`、实体 `libfftw3.so.3.6.10`）**正好颠倒**。

  后果是下游会把完整版本号记进 DT_NEEDED，而 pyfftw 这类消费方按
  `libfftw3.so.3` 找。补丁改成 `SOVERSION 3 VERSION 3.6.10`，
  与 autotools 的 `CURRENT:REVISION:AGE = 9:10:6` 对齐。

  ⚠️ 这是**凡改用上游 CMake 构建 FFTW 的包都会中招**的坑，
  且本包构建装包时完全不暴露 —— 要到下游链接才发现。
  实证：制品仓里 fftw3f/3.3.9 完全没有 SONAME、fftw3f/3.3.9.1 的 SONAME 是
  无版本的 `libfftw3f.so`，都缺 `.so.3` 软链。

- **`ENABLE_THREADS=ON` 且 `WITH_COMBINED_THREADS=OFF`。**
  读 CMakeLists 335-346 行：只有 COMBINED 为 OFF 时才
  `add_library(${fftw3_lib}_threads)` 单出一个 `.so`；打开则把线程源码
  折进主库。pyfftw 是按 `-l<lib>_threads` 探测多线程支持的，折进去就探测不到。

- **不开 OpenMP。** 上游 Linux wheel 的伴生库是 `_omp` 版，但设备实测：
  SDK 里虽有 libomp.so、`-fopenmp` 也能编能跑（20 线程），产物的 RUNPATH
  却被烤成 `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/.../llvm/lib`
  —— 带 SDK 版本号的绝对路径，而 libomp.so 全设备只有 SDK 里有，换机器就炸。
  pyfftw 的 setup.py 自带逃生口：定义 `PYFFTW_USE_PTHREADS` 即优先走 pthreads。

## 状态

built（真机 conan create + test_package 通过）
