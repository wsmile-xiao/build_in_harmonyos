# lapack64 3.12.1 适配笔记（HarmonyOS PC / os=OHOS arch=armv8）

## 软件定位

lapack64 是 LAPACK 的 64 位整数索引（ILP64）变体：上游 CMake `BUILD_INDEX64=ON`
语义下的 LAPACK 组件（CMakeLists 中 `LAPACKLIB=lapack64`），库实名 liblapack64.a。
源码同为 Reference-LAPACK v3.12.1 官方 tarball（与 lapack/cblas64 包同源同
SHA-256）。与 cblas64 包（cblas_*_64 C 接口 + libblas64.a）同属 INDEX64 家族，
知识参考 knowledge/drafts/E547-draft-CD3B.md。

## 构建语义与依赖

- Fortran 侧 `flang -fdefault-integer-8`（实测 default integer 变 8 字节，探针
  storage_size(1)=64 见 cblas64 notes），导出**无后缀** Fortran 符号（dgemm_ 等，
  ILP64 语义）——gfortran/flang 均无符号后缀选项，带后缀 ILP64 符号是 OpenBLAS
  INTERFACE64 等实现的私有惯例（cblas64 notes 已论证）。同一次链接内与 32 位
  liblapack/libblas 不可共存（符号同名），消费方需整链一致 ILP64。
- ILP64 BLAS：ohpcd 无独立 ILP64 BLAS 包，BLAS64 由 cblas64/3.12.1 包成对提供
  （libblas64.a + Fortran 静态运行时）。本包 `requires cblas64/3.12.1`，消费方
  经 cpp_info 传递拿到完整 ILP64 链（lapack64+cblas64+blas64+运行时），与上游
  BUILD_INDEX64 一体产出 blas64+lapack64 的语义一致。
- tool_requires flang-ohos/20.1.0（同 lapack/cblas64/openblas 先例）；链接其
  FortranRuntime/FortranDecimal 静态库（LDFLAGS 由 make.inc 注入）。
- 构建走上游 make 路径（SRC/Makefile include 顶层 make.inc）；绕开 CMake 的
  原因同 lapack/cblas64 包（FortranCInterface 链接验证不可用，flang 精简运行集
  无法完成）。
- TIMER=NONE：second_NONE/dsecnd_NONE 计时桩返回 0，不依赖 etime 等平台扩展；
  LAPACK 算法本体不用计时值，仅测试驱动打印。INSTALL 探针对象仅取
  dlamch.o/second_NONE.o/dsecnd_NONE.o 三个（SRC/Makefile 显式引用）；
  dlamch.o 显式 `-O0`（FFLAGS_NOOPT）防优化改变机器常数探测的舍入/下溢行为。

## 上游测试（R51 三步法）

- **清点**：上游 LAPACK testing = 14 个驱动（另有 4 个 xdmd* 驱动不在默认全量）× 74 次驱动运行（消耗 47 个输入文件；上游 testing/*.in 清单共 67 个）：
  xlintst{s,d,c,z}（LIN 4）+ xlintstds/xlintstzc（混合精度 proto 2）+
  xlintstrf{s,d,c,z}（RFP LIN 4）+ xeigtst{s,d,c,z}（EIG 4）；输入 testing/*.in。
- **实际运行**：真机（os=OHOS armv8）上游 make 全路径构建 BLAS64+LAPACK64+
  MATGEN+全部驱动（make.inc 同配方语义：-fdefault-integer-8、TIMER=NONE），
  binary-sign-tool 签名后经官方 lapack_testing.py -n -r 全量运行。
  证据：reports/lapack64-upstream-testing-log.md（原件在任务目录，哈希见报告头）。
- **结果与计数口径**：官方 runner 汇总表（SUMMARY nb test run / numerical error
  / other error）为准：N=测试运行数，N′=通过数（=N−数值错误−其他错误）。
  **N = 5,151,370，数值错误 0、其他错误 0（通过率 5151370/5151370，100%）**；
  覆盖 14 驱动 × 74 次运行（消耗 47 个不同输入文件；上游 .in 清单共 67 个，glm/nep 等跨精度共用、bak/bal/dmd 等 20 个不在默认全量内）。
  dlamch 探针（-O0）真机运行正常（IEEE 双精度机器常数（Epsilon=1.11e-16、Precision=2.22e-16））。

## 轮间产物基线说明

liblapack64.a 为 ar 静态库，成员元数据内嵌构建目录随机名/时间戳，每轮验证
（私有 CONAN_HOME 随机命名）字节级不同属预期。conan-verify L5 提示同源码
重验出现基线差异时删除 reports/baseline.json 重立基线（语义等同首轮），
本任务按该口径执行一次并在此记录原因（reports/ 本身在 .gitignore 中，
基线为轮间工件非交付物）。

## 消费者测试

test_package/test.c 以 int64 整数参数直调 dgemm_/dgesv_（列主序，手算值逐项
校验），链接 liblapack64+libblas64+Fortran 运行时全链（L1e 反向验证均真实依赖）。

## 与 32 位 lapack 包的差异

| 项 | lapack 3.12.1 | lapack64 3.12.1 |
| --- | --- | --- |
| 整数宽度 | LP64（default 4 字节） | ILP64（-fdefault-integer-8，8 字节） |
| 产物 | liblapack.a + libblas.a | liblapack64.a（BLAS64 由 cblas64 依赖提供） |
| 依赖 | 无 requires | requires cblas64/3.12.1 |
| 上游测试 | 未运行（R51 前归档） | 真机全量运行（见上） |
