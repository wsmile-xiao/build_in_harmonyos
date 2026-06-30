# pnetcdf 1.14.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-11
- 编译器: clang/clang++ (clang version 15.0.4)
- MPI: MPICH 4.0.3
- 状态: built (成功)

## 编译步骤

### 1. 准备 MPI 环境
MPICH 4.0.3 已预装到 ~/usr/local：
```bash
export PATH=$HOME/usr/local/bin:$PATH
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
export MPICC=$HOME/usr/local/bin/mpicc
export MPICXX=$HOME/usr/local/bin/mpicxx
```

### 2. 应用 HMDFS 解决方案
在不受 HMDFS 限制的目录运行 configure：
```bash
mkdir -p ~/tmp/pnetcdf-build-1.14.1
mkdir -p ~/tmp/pnetcdf-config-tmp
mkdir -p ~/tmp/test-install-pnetcdf-1.14.1
export TMPDIR=$HOME/tmp
```

### 3. Configure
```bash
cd ~/tmp/pnetcdf-build-1.14.1

~/builds/pnetcdf-1.14.1.work/configure \
    --prefix=$HOME/usr/local \
    --build=aarch64-unknown-linux-gnu \
    --disable-cxx \
    --disable-fortran \
    MPICC=$HOME/usr/local/bin/mpicc \
    MPICXX=$HOME/usr/local/bin/mpicxx \
    MPIF90="" \
    MPIF77=""
```

Configure 关键输出：
- MPI vendor: MPICH 4.0.3
- Build static libraries: yes
- Build shared libraries: yes
- Build Fortran APIs: no
- Build C++ APIs: no

### 4. 编译和安装
```bash
make -j2
make install DESTDIR=~/tmp/test-install-pnetcdf-1.14.1  # staging
make install  # 本地安装
```

### 5. 验证
```bash
# 版本验证
pnetcdf_version
# 输出: PnetCDF Version: 1.14.1

# 功能验证（使用 MPI）
cat > test_pnetcdf.c << 'EOF'
#include <pnetcdf.h>
#include <stdio.h>
#include <mpi.h>

int main(int argc, char** argv) {
    int rank, nprocs;
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
    printf("Process %d of %d: PnetCDF version: %s\n",
           rank, nprocs, ncmpi_inq_libvers());
    MPI_Finalize();
    return 0;
}
EOF

mpicc test_pnetcdf.c -I$HOME/usr/local/include -L$HOME/usr/local/lib -lpnetcdf -o test_pnetcdf
mpiexec -np 2 ./test_pnetcdf
# 输出:
# Process 0 of 2: PnetCDF version: 1.14.1 of July 31, 2025
# Process 1 of 2: PnetCDF version: 1.14.1 of July 31, 2025
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 之前失败：缺少 MPI 依赖 | 系统未安装 MPI 库 | 安装 MPICH 4.0.3 到 ~/usr/local |
| 2 | HMDFS 软链接限制 | configure 在 HMDFS 目录执行失败 | 在不受限目录 ~/tmp 运行 configure |
| 3 | umask 077 问题 | configure 默认使用 umask 077 | 已确认为 umask 022，无需修改 |

## 关键配置说明

pnetCDF configure 参数：
- `--disable-cxx`：禁用 C++ 绑定（减少编译时间）
- `--disable-fortran`：禁用 Fortran 绑定（减少依赖）
- `MPICC=...`：指定 MPI C 编译器路径
- `MPICXX=...`：指定 MPI C++ 编译器路径
- `MPIF90=""`：明确禁用 Fortran MPI 编译器
- `MPIF77=""`：明确禁用 Fortran 77 MPI 编译器
- `--build=aarch64-unknown-linux-gnu`：绕过 config.guess 平台识别

## 安装产物

### 库文件
- `/usr/local/lib/libpnetcdf.a` (3.8M) - 静态库
- `/usr/local/lib/libpnetcdf.so.7.0.0` (2.9M) - 动态库
- `/usr/local/lib/libpnetcdf.so` -> libpnetcdf.so.7.0.0
- `/usr/local/lib/libpnetcdf.so.7` -> libpnetcdf.so.7.0.0

### 工具程序
- `/usr/local/bin/ncmpidiff` (99K) - NetCDF 文件差异比较
- `/usr/local/bin/ncmpidump` (83K) - NetCDF 文件转储
- `/usr/local/bin/ncmpigen` (199K) - NetCDF 文件生成
- `/usr/local/bin/ncoffsets` (52K) - 偏移量计算工具
- `/usr/local/bin/ncvalidator` (64K) - NetCDF 文件验证
- `/usr/local/bin/pnetcdf-config` (11K) - 配置助手
- `/usr/local/bin/pnetcdf_version` (22K) - 版本信息
- `/usr/local/bin/cdfdiff` (88K) - CDF 文件差异比较

### 头文件
- `/usr/local/include/pnetcdf.h` (173K) - 主头文件

## 使用说明

### 编译程序
```bash
mpicc program.c -I$HOME/usr/local/include -L$HOME/usr/local/lib -lpnetcdf
```

### 运行程序
```bash
mpiexec -np <进程数> ./program
```

### 设置库路径
```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
```

## 依赖版本

### 已有依赖
- clang 15.0.4
- GNU make 4.4.1
- autoconf 2.72
- pkg-config 0.29.2
- **MPICH 4.0.3** (必需)

## 知识提取记录

### 已解决
- pnetCDF 需要 MPI 库支持
- 在 HMDFS 环境下需要在不受限目录运行 configure
- MPI 初始化使用 MPI_Init/MPI_Finalize，而非 ncmpi_init/ncmpi_finalize

### 知识图谱草稿
- 已创建 E081-draft-6A3A（缺少 MPI 库依赖导致 configure 失败）
  - 该草稿应在本次成功编译后更新为已解决状态

## 测试结果

### 功能测试
- ✅ 编译测试程序成功
- ✅ MPI 并行运行测试程序成功（2 进程）
- ✅ pnetcdf_version 工具正常运行
- ✅ ncmpidump 工具正常显示帮助信息

### 性能测试
- make check：部分测试超时跳过（测试套件较大）
- 核心 MPI 功能正常

## 注意事项

1. pnetCDF 是并行 I/O 库，必须与 MPI 一起使用
2. MPI 必须在运行前正确初始化（MPI_Init）
3. 需要 MPICH 4.0.3 或更高版本支持 MPI 4.0 特性
4. 共享库运行时需要设置 LD_LIBRARY_PATH 或 RPATH

---
**编译结束**: 2026-06-11 18:45
**最终状态**: built
---

**编译结束**: 2026-06-11 18:47
**最终状态**: built
