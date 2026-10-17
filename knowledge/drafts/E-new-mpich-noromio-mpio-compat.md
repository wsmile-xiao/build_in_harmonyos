# mpich（--disable-romio）缺 MPI-IO 声明时给消费库补 stdio 兼容头

> Draft: DRAFT-MPICH-NOROMIO-MPIO-COMPAT
> Stem: `E-new-mpich-noromio-mpio-compat` — pairs with the same-stem `.kv`
> 来源：combblas 2.0.0 适配（PR #9161，2026-09-09）

## 基本信息

- **ID**: DRAFT-MPICH-NOROMIO-MPIO-COMPAT
- **严重度**: 3
- **类别**: mpi, mpich, romio, portability, conan-recipe, cmake
- **触发工具**: clang|mpich|mpi.h|cmake|conan
- **阶段**: compile|link

## 错误特征

```
use of undeclared identifier 'MPI_MODE_CREATE'|use of undeclared identifier 'MPI_MODE_WRONLY'|
use of undeclared identifier 'MPI_File_open'|use of undeclared identifier 'MPI_File_close'|
use of undeclared identifier 'MPI_File_read_at'|MPI_File_write|MPI_File_set_view|
typedef redefinition with different types .*MPI_File|member access into incomplete type 'struct ADIOI_FileD'
```

## 可复现问题

ohpcd 发布的 mpich/4.0.3 配方 `--disable-romio`（ROMIO = MPI-IO 实现被禁用）：
- `mpi.h` 里 `MPI_MODE_CREATE/WRONLY/RDONLY` 宏缺失（仅剩 NOCHECK/NOSTORE/NOPUT/NOPRECEDE/NOSUCCEED）
- `MPI_File_open/close/read_at/write/write_all/set_view` 函数声明缺失
- `MPI_File` 类型**有** typedef（`typedef struct ADIOI_FileD *MPI_File`）但 `struct ADIOI_FileD` 未定义（不完整类型）

消费 MPI-IO 的库（combblas 的 SpParHelper.cpp/FullyDistSpVec.cpp/SpParMat.cpp 用它读
Matrix Market 文件、DebugPrintKeys 写临时文件）直接编译报 `undeclared identifier`。

## 根因分析

MPI-IO 是 MPI-2 的可选实现，由 ROMIO 提供。ohpcd 的 mpich 配方为裁剪体积/避免 OHOS
构建问题用了 `--disable-romio`，导致 mpi.h 里 ROMIO 相关声明整体缺失——但 `MPI_File`
类型仍保留 typedef（ROMIO 类型定义在 mpi.h 里，函数实现才在 ROMIO 库）。这造成
"类型有、函数无"的中间态：编译期缺声明，且无法用链接 libromio 解决（库也没编）。

## 推荐方案

**方法**: stdio-mpio-compat-header

**说明**: >
  在消费库的公共主头（如 CombBLAS.h）patch 一个 stdio 实现的 MPI-IO 兼容头：
  (1) **补全不完整类型**：`struct ADIOI_FileD { FILE * f; };`（mpi.h 只 typedef
      了指针，补结构体定义即可，不重复 typedef——重复会报 "typedef redefinition
      with different types"）；
  (2) **stdio 实现函数**：MPI_File_open → fopen（CREATE 时 "wb+" 否则 "rb"）、
      MPI_File_close → fclose、MPI_File_set_view → fseek(SEEK_SET)、
      MPI_File_write/write_all → fwrite、MPI_File_read_at → fseek+fread；
  (3) **MPI_Status 兼容**：mpich 的 MPI_Status 是 `{count_lo, count_hi_and_cancelled,
      MPI_SOURCE, MPI_TAG, MPI_ERROR}`（无 count 字段）——read_at 里写 `st->count_lo`；
      MPI_Get_count 已在 mpi_proto.h 声明，**不要重复定义**；
  (4) **单进程语义**：此替代等价于单进程场景（每 rank 独立 fopen/fseek），多进程
      并行 I/O 语义不保真——适配时明确标注适用范围。
  插入位置：主头 `#include <mpi.h>` 之后（保证 MPI_File 类型已可用）。

**验证/命令**:
```
conan create archives/c/combblas/2.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 预期：configure 无 MPI_File/MPI_MODE 未声明错误，EXIT=0，test_package 输出 combblas OK
```

## 关键词

mpich, romio, MPI-IO, MPI_File, MPI_MODE_CREATE, ADIOI_FileD, mpi.h, disable-romio,
mpio compat, stdio, fopen, fseek, MPI_Status, count_lo, combblas, OHOS, clang
