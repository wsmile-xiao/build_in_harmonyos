# pnetcdf

Parallel NetCDF - 并行 I/O 库，用于 NetCDF 格式文件的并行读写。

## 简介

PnetCDF (Parallel NetCDF) 是一个高性能并行 I/O 库，基于 NetCDF 格式，专为 MPI 并行计算设计。它允许多个 MPI 进程同时读写同一个 NetCDF 文件，大大提高了大规模科学计算应用的 I/O 性能。

## 特性

- 支持 MPI 并行 I/O
- 与标准 NetCDF 格式兼容
- 支持阻塞和非阻塞 I/O 操作
- 提供 C、Fortran 和 C++ API
- 支持大数据集（大于 2GB）

## 编译版本

### 1.14.1 (built)
- 编译日期: 2026-06-11
- 状态: built
- 依赖: MPICH 4.0.3
- 特点: 禁用 C++ 和 Fortran 绑定，仅保留 C API

## 依赖

- **MPICH 4.0.3** (必需) - MPI 运行时库
- clang 15.0.4 (编译器)

## 使用示例

### 编译程序
```bash
mpicc program.c -I$HOME/usr/local/include -L$HOME/usr/local/lib -lpnetcdf
```

### 运行程序
```bash
mpiexec -np 4 ./program
```

### 简单示例
```c
#include <pnetcdf.h>
#include <mpi.h>

int main(int argc, char** argv) {
    int rank, nprocs;
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &nprocs);

    printf("Process %d: PnetCDF version %s\n",
           rank, ncmpi_inq_libvers());

    MPI_Finalize();
    return 0;
}
```

## 工具程序

- `ncmpidump` - NetCDF 文件内容转储
- `ncmpigen` - 从文本描述生成 NetCDF 文件
- `ncmpidiff` - 比较 NetCDF 文件差异
- `pnetcdf_version` - 显示版本信息
- `pnetcdf-config` - 编译配置助手

## 平台适配

### HMDFS 环境适配
在 HMDFS 文件系统环境下，configure 脚本需要在不受限制的目录执行，例如 ~/tmp。

### MPI 依赖
pnetCDF 必须与 MPI 库一起使用。推荐使用 MPICH 4.0.3 或 OpenMPI 4.x。

## 参考资料

- 官方网站: https://parallel-netcdf.github.io/
- 用户手册: https://parallel-netcdf.github.io/wiki/
- GitHub: https://github.com/Parallel-NetCDF/PnetCDF