# libminc

MINC 医学影像文件格式库：MINC1（netCDF 底层）与 MINC2（HDF5 底层）卷 I/O，
附 volume_io 几何/变换支持。产出 `libminc2.so`（头文件 minc2.h/minc.h/volume_io/）。

MINC2 格式底层用 HDF5 存储，MINC1 格式底层用 netCDF（经典格式），两者都静态
使用 zlib 做体数据压缩。

- 上游：https://github.com/BIC-MNI/libminc
- 许可证：BSD-3-Clause
- 鸿蒙 PC 适配版本：见各版本目录
