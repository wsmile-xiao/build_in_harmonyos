# lapacke64 3.12.1 — HarmonyOS PC 适配笔记

## 定位

lapacke64 = Reference-LAPACK **3.12.1** 的 LAPACKE C 接口 **ILP64（64 位整数）**
变体（Debian sid 同名口径：`-fdefault-integer-8` 构建的 libblas64/liblapack64/
liblapacke64）。与仓内既有包的关系：

- `lapack/3.12.1`：同一 tarball 的 **ILP32** 构建，只产 liblapack.a+libblas.a、
  无 C 头文件——其 conanfile 里的 `BUILD_CBLAS`/`BUILD_LAPACKE` 是 3.12.1
  **不存在**的开关（no-op），这正是它没产出 LAPACKE 的根因。整数 ABI 与
  lapacke64 不兼容，不能复用（requires 会把 ILP32 符号混进链接）。
- `liblapacke/0.3.30`：OpenBLAS 路线的 LAPACKE（**LP64**），非同源。

因此本配方**自含**：同一官方 tarball，`BUILD_INDEX64=ON` 一并产出
libblas64 + liblapack64 + liblapacke64（`LAPACKE` 符号在 liblapacke64 内），
`tool_requires flang-ohos/20.1.0` 编 Fortran，无运行期 conan 依赖。

## 源码

- https://github.com/Reference-LAPACK/lapack/archive/refs/tags/v3.12.1.tar.gz
- SHA256 `2ca6407a001a474d4d4d35f3a61550156050c48016d949f0da0529c0aa052422`
  （与 `archives/l/lapack/3.12.1` conandata 同源同哈希）
- license BSD-3-Clause（包内复制 LICENSE）

## 构建要点（CMake）

准确开关（tarball 逐行核实，勿照抄 lapack/3.12.1 的 no-op 开关）：

| 开关 | 值 | 作用 |
|------|----|------|
| `BUILD_INDEX64` | ON | 库名 blas64/lapack64/lapacke64；C 侧加 `-DLAPACK_ILP64 -DHAVE_LAPACK_CONFIG_H -DWeirdNEC`；`FORTRAN_ILP=TRUE` |
| `BUILD_INDEX64_EXT_API` | OFF | `_64` 后缀双 API 支持列表仅 Intel\|GNU，flang 不在列；只要单 API ILP64 |
| `LAPACKE` | ON | 构建 LAPACKE C 接口（正确开关名；`BUILD_LAPACKE` 不存在） |
| `BUILD_TESTING` | OFF | 关闭 TESTING/ 与 LAPACKE/example 子目录（演示另行手动编译执行） |
| `CBLAS` | OFF（默认） | 未启用：cblas64 为可选扩展，核心交付是 blas64/lapack64/lapacke64 |

ILP64 生效链：

- C：`-DLAPACK_ILP64` → `lapacke_config.h` 的 `lapack_int`/`lapack_logical`
  = `int64_t`（`-DWeirdNEC` 只影响 cblas.h 的 `CBLAS_INT`，本包未启 CBLAS）。
- Fortran：`CMAKE/CheckLAPACKCompilerFlags.cmake` 对非 Intel/XL/NAG/NVHPC
  编译器兜底 `-fdefault-integer-8`（flang 20 支持）。**配置期自检**：recipe
  在 configure 后读 `CMakeFiles/*/flags.make` 断言该标志确实出现在 Fortran
  flags——否则 Fortran 静默 ILP32 与 C 侧 int64 ABI 错位，宁可构建失败。

flang 编译链（复用 lapack/3.12.1 先例）：

- `CMAKE_Fortran_COMPILER` = flang-ohos 包内 flang；FLAGS 注入 SDK clang15
  `--sysroot` + `-resource-dir`（flang-ohos 是精简运行集，自带目录不完整）。
- `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`：flang 精简运行集缺
  crt/builtins 链接件，不能链接可执行文件。此模式下：
  - 编译器检测（lapack 3.12.1 已验证）；
  - `LAPACKE/include` 无条件执行的 `FortranCInterface_VERIFY()` 不做链接，
    实测通过，`lapacke_mangling.h` 正常生成并安装。
- `libFortranRuntime.a`/`libFortranDecimal.a` 随包复制进 `lib/`（lapack64
  归档内引用 `_FortranA*` 符号，消费方链接需带上），package_info.libs 一并
  声明，消费方 `-llapacke64 -llapack64 -lblas64 -lFortranRuntime
  -lFortranDecimal -lm` 即可。

安装产物（package() 核验）：

- `lib/`：`liblapacke64.a`、`liblapack64.a`、`libblas64.a`（+ flang 运行时
  归档）；shared 选项另产 `.so` 并经 binary-sign-tool 自签（XPM 要求）。
- `include/`：`lapacke.h`、`lapacke_mangling.h`（install 期生成）、`lapack.h`、
  `lapacke_config.h`、`lapacke_utils.h`。
- `lib/pkgconfig/`：blas64.pc / lapack64.pc / lapacke64.pc。

## 消费方须知

必须以 ILP64 宏口径包含头文件（recipe 的 `cpp_info.defines` 已自动传播）：

```c
// 编译时需 -DLAPACK_ILP64 -DHAVE_LAPACK_CONFIG_H
#include <lapacke.h>
lapack_int n = 2;          /* int64_t */
```

否则 `lapack_int` 退回 int32_t，与库内 int64 ABI 错位（调用看似能编过，
运行期数据损坏）。

## 上游测试

| 入口 | 状态 | 说明 |
|------|------|------|
| `test_package`（C 消费者） | **CI 门禁（L1）** | 8 项断言：sizeof(lapack_int)==8 锁 ILP64、LAPACKE_ilaver 版本、dgesv col/row、dpotrf、dgels、dgeev 残差、dpotrf 负例 |
| `LAPACKE/example` 4 演示 | **build() 内真实执行** | DGESV/DGELS × col/row-major，设备 CC 链接本构建静态产物就地跑（stdout 进 conan create 日志） |
| `TESTING/` 全套（EIG/LIN/MATGEN + lapack_testing.py） | **不入 CI，理由** | 参考 BLAS 后端全量 Fortran 测试真机需小时级（liblapacke 0.3.30 同套 lapack-test 实测 2-3h，COMPLEX16 LIN 单族即数十分钟），CI 45min 门禁不可容纳；ILP64 数值正确性由 test_package 断言 + example 演示覆盖核心路径（LU/Cholesky/QR/特征值）。如需全量：`-DBUILD_TESTING=ON` + ctest，可执行链接需 flang overlay（见 knowledge/drafts/DRAFT-ohos-flang-driver-link-overlay） |

已声明的偏差（test_package/MANIFEST.yml）：

- example 演示链接器用设备 CC（上游 Makefile 以 `$(FC)` 链接）——flang 精简
  运行集缺目标级 crt 无法链接可执行文件；被编译对象/头文件/被链库均为上游
  原件，仅链接器一处偏差。
- 上游 v3.12.1 tag 的 `INSTALL/ilaver.f` 与 CMake 版本号仍为 **3.12.0**
  （tag 未提升，tarball 逐行核实），故 LAPACKE_ilaver 断言 3.12.0——
  恰可锁定"用的是该 tarball 内置 Fortran 代码"。

## 已知限制 / 风险

- `shared=True` 分支实现了 .so 产出+自签+LD_LIBRARY_PATH 运行，但 **CI 只验
  默认静态**（profile 无 shared 覆盖）；shared 路径留待有需求时补验。
- flang 编 Fortran 全量 BLAS+LAPACK（~1500 文件）在 CI 默认 3600s 预算内
  （同体量 lapack/3.12.1 已通过），但设备负载高时接近上限，无
  build_timeouts 覆盖。
- `CMAKE_SYSTEM_NAME=HarmonyOS` 下 CMake 报 unknown platform warning 为已知
  现象，不阻塞。
