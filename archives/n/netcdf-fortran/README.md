# netcdf-fortran

netCDF 的 Fortran 接口库：在 netcdf-c 之上提供 F77 / F90 / F2003 的 API，产出 `libnetcdff.so`。

Fortran 程序通过 `use netcdf` 使用它读写 netCDF 文件；netCDF-4 格式底层仍由
netcdf-c → HDF5 完成，故运行期需要 netcdf-c 及其传递依赖（hdf5、curl、zstd、libxml2、libaec）。

- 上游：https://github.com/Unidata/netcdf-fortran
- 许可证：BSD-3-Clause
- 鸿蒙 PC 适配版本：见各版本目录

## OHOS 适配要点

- 设备与 NDK 无 Fortran 编译器，用仓库 `flang-ohos/20.1.0` 作 `tool_requires`。
- `.mod` 文件是编译器私有的二进制接口，**消费方必须用同一 `flang-ohos/20.1.0` 编译**。
- 消费方运行期需把 `libnetcdff.so` 与 netcdf-c 的传递依赖放进 `LD_LIBRARY_PATH`。
