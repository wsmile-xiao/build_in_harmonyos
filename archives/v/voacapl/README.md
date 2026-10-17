# voacapl

VOACAP（Voice of America Coverage Analysis Program）高频（HF）无线电传播预测
程序的 Linux/Unix 移植版，纯 Fortran 源码，输出命令行工具。

- 上游：https://github.com/jawatson/voacapl
- 许可证：上游为 NTIA/ITS special + CC0-1.0 混合（部分工具 GPL-3+）
- 鸿蒙 PC 适配版本：见各版本目录

## OHOS 适配要点

- 设备与 NDK 无 Fortran 编译器，用仓库 `flang-ohos/20.1.0` 作 `tool_requires`。
- flang 编译需给 `--target=aarch64-unknown-linux-ohos`、`--sysroot=<sdk>/sysroot`、
  `-resource-dir=<sdk>/llvm/lib/clang/<ver>`、`-L<sdk>/llvm/lib/aarch64-linux-ohos`
  （libunwind.a / libc++_shared.so 只在该目录），否则链接与运行均失败。
- 运行期需把 flang 包 lib/（libLLVM/libMLIR/libclang-cpp）与 SDK
  `llvm/lib/aarch64-linux-ohos`（libc++_shared.so）放入 `LD_LIBRARY_PATH`。
- 上游使用 FORTRAN 66 的 Hollerith 编辑描述符与 gfortran 扩展过程 `unlink()`，
  需源码级替换（详见各版本 patches 与 notes）。
