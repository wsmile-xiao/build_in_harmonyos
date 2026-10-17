# netcdf

netCDF-C：科学数据的自描述、可移植存储格式的 C 实现，产出 `libnetcdf.so`。

netCDF-4 格式底层用 HDF5 存储，所以本包依赖 `hdf5`；远程访问（DAP/NCZARR）依赖 `curl`，
XML 解析依赖 `libxml2`，压缩依赖 `zlib`/`zstd`/`libaec`。

- 上游：https://www.unidata.ucar.edu/software/netcdf/
- 许可证：BSD-3-Clause
- 鸿蒙 PC 适配版本：见各版本目录
