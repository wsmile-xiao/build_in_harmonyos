# GlobalArrays (GA)

Partitioned Global Address Space (PGAS) library for distributed arrays，
由 PNNL 维护（https://github.com/GlobalArrays/ga），许可证 BSD-3-Clause。

## HarmonyOS PC 适配说明（5.9.2）

- 构建系统：Autotools（configure + make）。
- 设备端无 MPI 运行时与 Fortran 编译器，故：
  - `--with-mpi=no --with-sockets`：关闭 MPI 消息层，使用 ARMCI SOCKETS（TCP）网络；
  - `--disable-shared --enable-static`：纯静态产物，规避 libtool relink 破坏 ELF 签名；
  - `--disable-openmp`：避免 OpenMP 运行时依赖；
  - `config.guess` 无法识别 HarmonyOS，configure 显式 `--build/--host=aarch64-unknown-linux-ohos`。
- 测试：`global/testing/unit-tests/` 依赖 MPI 多进程，OHOS no-MPI 构建不运行上游测试；
  使用 test_package consumer 测试（创建/读写/查询/负向断言）。
