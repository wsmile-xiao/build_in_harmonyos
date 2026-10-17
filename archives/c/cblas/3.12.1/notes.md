# cblas 3.12.1 适配笔记（HarmonyOS PC / os=OHOS arch=armv8）

## 软件定位

CBLAS 是 BLAS 的标准 C 接口绑定。netlib 自 LAPACK 3.x 起将 CBLAS 随 LAPACK 发行
（`lapack-3.12.1` tarball 的 `CBLAS/` 子树）；`netlib.org/blas/cblas.tgz` 是不含
3.12.1 的历史独立包，故本包源码取 Reference-LAPACK v3.12.1 官方 tarball（与仓库
lapack/3.12.1 同源同 SHA-256），只构建其中 CBLAS 组件。

## 构建方案

- 上游 make 路径（`CBLAS/Makefile` include 顶层 `make.inc`）。
  配方在 `generate()` 写入 `make.inc`（字面路径，无环境变量依赖），`build()` 依次
  `make -C CBLAS`（libcblas.a）、`make -C CBLAS/testing`（12 个 blat 驱动）、
  `make -C CBLAS/testing run`（上游测试）。
- 不走 CMake：顶层 CMake 构建 CBLAS 需 `FortranCInterface_VERIFY` 混合链接验证，
  flang-ohos 精简运行集无法链接验证目标（lapack 包先例：BUILD_CBLAS=ON 实际未产
  CBLAS）。make 路径无此要求，探索实测全程设备原生通过。
- CBLAS/src 含约 30 个 Fortran 桥接子例程（`sdotsub.f` 等，被 C 包装调用），由
  GNU make 内置 `.f.o` 规则消费 `$(FC) $(FFLAGS)` 编译。
- flang 实测可用的完整参数形态（探索验证）：
  `flang --target=aarch64-linux-ohos --sysroot=<SDK>/sysroot -resource-dir=<SDK llvm>/lib/clang/15.0.4`，
  链接加 `-L<SDK llvm>/lib/aarch64-linux-ohos -lFortranRuntime -lFortranDecimal -lm`；
  flang 运行期需 `LD_LIBRARY_PATH` 指向 SDK llvm/lib（libxml2 给 lld）与 flang 包
  lib（libLLVM/libMLIR）。

## 依赖与链接形态

- `requires openblas/0.3.34`：提供 LP64 Fortran BLAS 符号（ddot_/dgemm_/...）。
  上游测试驱动以 `libopenblas.a` 静态链接（BLASLIB 变量），驱动运行零环境依赖。
- libcblas.a 自身导出 153 个 `cblas_` 符号；未定义符号仅 BLAS 符号与库内全局
  （CBLAS_CallFromC/RowMajorStrg，cblas_globals.o 提供）。`.f` 桥接成员是纯计算
  包装，无 FortranRuntime 运行时符号引用，消费方无需链接 Fortran 运行时。

## 上游测试

- 套件：`CBLAS/testing`，12 个驱动 = level1/2/3 × s/d/c/z 四精度。
- 运行方式：`make run`（blat1 自包含；blat2/3 读源码树内 `*in2`/`*in3` 数据文件）。
- 统计口径：统计单位 = 测试程序验证行（blat1 为 subprogram 结果 10/驱动；
  blat2/3 为 column-major/row-major 计算测试与 error-exits 检查行）。
  取数：conanfile.py `build()` 内对 12 个 `*test*.out` 的正则计数
  （PASS=`----- PASS -----`/`PASSED THE`，FAIL=`FAIL` 不分大小写）。
- 结果：TOTAL = 340 PASS + 0 FAIL（stest1..ztest3 依次 10/10/10/10/48/48/51/51/21/21/30/30）。
- 8 个 blat2/3 输出均含唯一 `END OF TESTS` 行，驱动全部跑完。

## 已核对的上游行为

- `cblas_xerbla` 的错误处理在库内（`cblas_xerbla.c`/`xerbla.c`），测试驱动通过
  `c_xerbla.c` 的同名拦截器接管；静态库成员按需提取，无符号冲突。
- 测试驱动主程序为 Fortran（`c_*blat1/2/3.f`），flang 编译 + 手动 SDK 链接路径
  实测可运行（FortranRuntime 静态链接进驱动）。
