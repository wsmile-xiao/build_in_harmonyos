# PaStiX

PaStiX（parallel sparse direct solver）是 Inria / LaBRI（Bordeaux）的并行稀疏直接求解器：supernodal 分解、SIMD 阻塞内核、动态调度，面向共享内存与异构节点。

- 官网与仓库: <https://gitlab.inria.fr/solverstack/pastix>
- 许可证: LGPL-3.0-only
- 构建系统: CMake（依赖 SCOTCH / BLAS-LAPACK / hwloc；本仓以 Conan 配方入库）

## 归档版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 6.4.0 | built | SMP 静态库组合面（openblas 0.3.34 + scotch 7.0.12 + hwloc 2.14.0，无 MPI/GPU）；含 0001 getopt 值 token 可移植性补丁 |

## OHOS 适配要点

- **getopt 可移植性**：OHOS libc 的 `getopt_long` 会置换非选项参数，上游 `get_options.c` 直读 `argv[optind]` 不推进 optind 的用法在 OHOS 上崩（多 `-i` 参数用例段错误）；补丁 0001 显式消费值 token。
- **Fortran 必需**：上游 `project()` 声明 Fortran 为必需语言，设备/NDK 无 Fortran 编译器，需 `tool_requires flang-ohos/20.1.0` 并给全 `--target/--sysroot/-resource-dir` 与链接期 `-L<SDK>/llvm/lib/aarch64-linux-ohos`。
- **morse Find 模块**：需关闭 `find_package_prefer_config` 恢复模块模式查找（SCOTCH 位宽探测依赖 FindSCOTCH）。
- **hwloc.pc shim**：FindHWLOC 只走 pkg-config，依赖包内 .pc 不可重定位，配方生成 shim。
- 详见 `6.4.0/notes.md` 与 `6.4.0/manifest.yaml`。
