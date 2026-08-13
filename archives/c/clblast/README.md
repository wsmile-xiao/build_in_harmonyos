# CLBlast

## 软件描述
CLBlast 是一个现代、轻量、高性能、可调优的 OpenCL BLAS 库（GitHub: CNugteren/CLBlast）。
提供 Level-1/2/3 BLAS 例程以及扩展例程（xhad/xomatcopy/xim2col/batched 等）的 OpenCL
加速实现，支持 16/32/64 位浮点与混合精度。

## 主要功能
- **Level-1 BLAS**: xswap/xscal/xcopy/xaxpy/xdot/xnrm2/xasum/xamax 等 10 个例程
- **Level-2 BLAS**: xgemv/xger/xsyr/xher/xsymv 等 24 个例程
- **Level-3 BLAS**: xgemm/xsymm/xsyrk/xherk/xtrmm/xtrsm 等 9 个例程
- **扩展例程**: xhad/xomatcopy/xconvgemm/batched GEMM 等 8 个例程
- **C API**（clblast_c.h）与 **C++ API**（clblast.h）

## 平台依赖
- 需要 OpenCL 头文件（opencl-headers）与 libOpenCL.so（opencl-icd-loader）
- 运行期需要 OpenCL 设备（GPU/CPU 驱动）

## 构建信息
- 构建系统: CMake
- 适配版本: 1.7.0（archives/c/clblast/1.7.0/）
- 平台: HarmonyOS PC (aarch64, os=OHOS)
