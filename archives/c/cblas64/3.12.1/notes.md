# cblas64 3.12.1 适配笔记（HarmonyOS PC / os=OHOS arch=armv8）

## 软件定位

CBLAS64 是 BLAS 的 64 位整数索引 C 接口（函数名 `cblas_*_64`，整数参数 int64_t），
即 cblas.h 的 `CBLAS_API64` 模式，等价上游 CMake `BUILD_INDEX64=ON` 时的 CBLAS
组件（库实名 libcblas64）。源码同为 Reference-LAPACK v3.12.1 官方 tarball（与
cblas/lapack 包同源同 SHA-256）。

## 链接语义与 ILP64 BLAS

- cblas64 包装层把调用转发给 ILP64（8 字节整数）BLAS 符号。上游 BUILD_INDEX64
  构建语义即 BLAS64 与 CBLAS64 一体产出（BLASLIB=blas64、CBLASLIB=cblas64）。
- ohpcd 暂无 ILP64 BLAS 发布（openblas 为 LP64）。本包按上游语义在包内以
  `flang -fdefault-integer-8` 构建 BLAS/SRC 参考 BLAS 的 64 位整数变体
  （libblas64.a，155 个导出符号），与 libcblas64.a 成对提供。实测 flang 该选项
  生效（探针程序 `storage_size(1)=64`）。
- 消费方链接：`-lcblas64 -lblas64 -lFortranRuntime -lFortranDecimal`（libblas64.a
  的 xerbla.f 引用 Fortran I/O；运行时静态库随包提供，同 lapack 包先例）。

## 上游 INDEX64 + CBLAS 组合的三处缺陷（补丁修复）

探索期在设备上原生复现并逐一修复，全部补丁不含平台条件编译：

1. **F77 符号 mangling 断裂**（patches/0001）：cblas_f77.h 的
   `F77_GLOBAL_SUFFIX` 无条件经 `API_SUFFIX` 给 Fortran 符号加 `_64` 后缀
   （C 端期望 `srotg_64_`），而 Fortran 侧 `-fdefault-integer-8` 恒产出无后缀
   符号（`srotg_`，gfortran/flang 均无符号后缀选项；带后缀的 ILP64 符号是
   OpenBLAS INTERFACE64 等实现的私有惯例）——上游同一次构建的 blas64 与
   cblas64 必然链接失败（`undefined symbol: srotg_64_`）。修复：宏加 `#ifndef`
   门，配方以 `-D'F77_GLOBAL_SUFFIX(a,b)=F77_GLOBAL(a,b)'` 恒等直通；cblas.h 的
   公开 API 改名（`cblas_*_64`）不受影响。对 32 位构建为 no-op。
2. **测试 C 辅助文件未做 API 改名**（patches/0003）：testing/*.c 的调用点是字面
   `cblas_sasum(...)`，而 64 位库导出 `cblas_sasum_64`（上游 CMake 同样未覆盖该
   组合，`cblas_test.h` 无 API_SUFFIX 适配）→ 必然 `undefined symbol`。补丁仅
   改函数名解析（`cblas_xxx(` → `cblas_xxx_64(`，20 个文件），不改测试逻辑与
   期望值。
3. **c_xerbla.c 栈缓冲越界读写**（patches/0002）：`F77_xerbla` 的
   `char rout[14]`（14 元素）装不下 `"cblas_" + 7 字符`（LAPACK 3.12 新增例程 ZGEMMTR 的
   XERBLA SRNAME 为 7 字符，zgemmtr.f:275），且复制循环 `i<7` 对 6 字符名
   （ZHER2K/ZSYR2K）越界读 `srname[6]` 并覆盖 `rout[12]` 的 NUL 终止符——SRNAME
   回环校验（strcmp）依赖栈布局运气。实测：32 位 OpenBLAS 路径靠栈上恰好为零
   通过；参考 BLAS 路径（本包）必失败（输出 `SRNAME = <cblas_zher2k垃圾>
   INSTEAD OF ...`）。修复：数组扩至 15 元素、复制循环以 Fortran 传入的
   `srname_len` 界定上界、循环后显式 `rout[13]='\0'`。

## 构建方案

- 上游 make 路径：`generate()` 写顶层 `make.inc`（BLAS/SRC 与 CBLAS 两级
  Makefile 都 include 它），`build()` 依次 `make -C BLAS/SRC`（libblas64.a）、
  `make -C CBLAS`（libcblas64.a）、`make -C CBLAS/testing`（12 驱动）、
  `make run`（上游测试）。绕开 CMake 的原因同 cblas 包（FortranCInterface）。
- 64 位 C 端宏：`-DWeirdNEC -DCBLAS_API64 -DLAPACK_ILP64 -DHAVE_LAPACK_CONFIG_H`
  （与上游 CMake BUILD_INDEX64 的 CFLAGS 一致，`-DCBLAS_API64` 对应上游
  `src/CMakeLists.txt` 的 `_64_cobj` 目标定义）。
- 产物：libblas64.a（155 导出，无后缀 Fortran 符号）、libcblas64.a（153 个
  `cblas_*_64` 导出）。库与测试产物全部落 build_folder。

## 上游测试

- 套件同 cblas 包（12 驱动），全量以 64 位模式编译运行。
- 统计口径同 cblas 包（测试程序验证行；取数 conanfile.py `build()` 正则计数）。
- 结果：TOTAL = 340 PASS + 0 FAIL（分布与 cblas 包一致）。
- 测试代码修改仅 patches/0002（越界 bug 修复，不改断言）与 patches/0003（API
  名适配，不改断言）；12 个驱动的测试逻辑、输入数据文件与期望值均未改动。
