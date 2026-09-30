# W0 report: libgomp 16.1.1

- Issue: 待补（本机前置适配，任务清单未提供明确 issue 编号）
- Date: 2026-09-24
- Dependency role: GNU OpenMP 运行时库，无独立上游，从 GCC 16 源码树构建 libgomp 子库。

## 上游信息

- 软件：libgomp（GNU Offloading and Multi Processing Runtime Library，GCC 的 OpenMP 运行时）。
- 上游：https://gcc.gnu.org/ ，源码位于 GCC 源码树 `libgomp/` 子目录。
- 许可证：GPL-3.0-or-later WITH GCC-exception-3.1（runtime 例外，链接不传染）。
- 版本映射：Conan 16.1.1 → 上游 GCC 16.1.0（GCC 官方 ftp 无 gcc-16.1.1.tar.xz，
  仅 16.1.0 / 16.2.0；16.1.1 为 releases/gcc-16 分支点，采用同系列官方 tarball 保证可复现）。
- 源码 tarball：gcc-16.1.0.tar.xz，sha256 `50efb4d94c3397aff3b0d61a5abd748b4dd31d9d3f2ab7be05b171d36a510f79`
  （本机复用 libobjc 适配已下载的 tarball，重新校验 sha256 一致，97.7 MB）。

## 依赖

- 运行时依赖：
  - pthread（musl libc 自带，`-pthread` 链接，见 E003）。
  - futex syscall（aarch64 上 config_path="linux posix"，有 ENOSYS 降级；不可用时回落 posix pthread mutex/cond）。
- 构建依赖：
  - clang（纯 C，无需 clang++ / 无需 gfortran；无 FC 时 configure 自动跳过 Fortran 模块，见 E109）。
  - GNU binutils（ar/ranlib/nm/objcopy/readelf/ld，OHOS 用 llvm-* 替代，见 E012）。
  - make、bash、/bin/sh（HMDFS 无执行位，见 E046/E087）。
- 与 libobjc 的差异：**不构建 GCC 前端**，因此不需要 GMP/MPFR/MPC（GCC 前端的 in-tree 依赖），
  也无需 all-gcc 生成的 gcc/runtime-info.h 与 libgcc。
- 可选依赖：Fortran 编译器（gfortran）——OHOS 无 gfortran，自动降级跳过 omp_lib 模块。
- 无额外 Conan 依赖。

## 依赖数量与结论

```text
依赖数量：0 个独立 Conan 依赖（pthread/libc 为系统 musl 自带）
已满足依赖：pthread、futex、libc 均由 OHOS musl 提供
缺失依赖：无
是否需要拆分依赖适配：否
阻塞点：无前置阻塞；真机 shadow CI 需排队
下一步：本机前置验证 -> 真机 shadow CI（单包排队）
```

## Source and build system

- 源码：GNU GCC 16.1.0 release archive（tar.xz，97.7 MB，选择性解压 libgomp/ 子目录）。
- 构建系统：libgomp 独立 autotools（libgomp/configure + make），native aarch64-linux-ohos（--host=aarch64-unknown-linux-musl）。
- 构建目标：libgomp.so / libgomp.a + omp.h（纯 C，无 Fortran 模块）。
- 上游测试：libgomp/testsuite（DejaGNU），需 DejaGNU 环境，OHOS 隔离 job 不现实，改为 test_package 消费者验证。

## Decision

真机 shadow CI 已通过（L0/L1/L4/L5 pass，L2 skip），libgomp/16.1.1 适配完成。
