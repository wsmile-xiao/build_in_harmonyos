# openblas 0.3.34 编译笔记（HarmonyOS PC · Makefile · 含 LAPACK）

## 定位
- 优化 BLAS + 完整 LAPACK。numpy/scipy 等科学计算依赖。产 libopenblas.so.0（含 LAPACK 符号）。

## 关键适配（含 Fortran → 用 flang-ohos）
- LAPACK 是 Fortran，设备/NDK 无 Fortran 编译器 → **tool_requires flang-ohos/20.1.0**（设备原生 LLVM Flang）。
  build() 里 FC=<flang-ohos>/bin/flang，FEXTRALIB 喂 <flang-ohos>/lib/libFortran{Runtime,Decimal}.a。
- **两处源码补丁**（portability）：
  1. exports/Makefile FLANGNEW so 分支：原 $(FC) 当链接器 → flang 塞 host 依赖失败；改 $(CC) 链 + 追加 $(FEXTRALIB)。
  2. blas_server.c：openblas_setaffinity/getaffinity 加 !defined(__OHOS__)（OHOS musl libc.so 不导出 pthread_setaffinity_np）。
- **构建 env**：LD_LIBRARY_PATH = <SDK llvm/lib>:<flang 包 lib>（前者给 lld 正确 libxml2.so.16——HiShell 污染会搞坏 lld；后者给 flang 运行期 libLLVM/libMLIR/libclang-cpp）。CC/AR/RANLIB 用设备 hnp 路径。
- 目标 `shared`（不用默认 all，避免可选 tests 用 flang 当链接器失败）；TARGET=ARMV8。
- package() 里 binary-sign-tool 自签 .so。

## 状态
built（真机原生 conan create 通过：编译+签名+打包；dgemm=[19,43,22,50]、dgesv 解=[1,2] info=0 全对；numpy 2.5.1 链本库验证通过）。
