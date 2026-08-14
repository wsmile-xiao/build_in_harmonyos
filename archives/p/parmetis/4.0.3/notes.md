# ParMETIS 4.0.3 适配笔记

## 基本信息

- **上游仓库**：https://github.com/KarypisLab/ParMETIS
- **下载源**：https://karypis.github.io/glaros/files/sw/parmetis/parmetis-4.0.3.tar.gz
- **构建系统**：CMake 2.8+（顶层有 Makefile 包装器，本配方直接用 CMake）
- **许可证**：University of Minnesota（研究/教育免费，商业需授权）

## 依赖关系

```
parmetis/4.0.3
├── open-mpi/5.0.10  (外部 conan 依赖)
├── metis/           (源码内 bundle)
└── metis/GKlib/     (源码内 bundle)
```

## 适配要点

### 1. MPI 链接策略（6 轮迭代）

**最终方案**：显式传入 MPI 路径 + `CMAKE_EXE_LINKER_FLAGS`

上游 CMakeLists.txt 中 FindMPI 被注释掉，设计意图是用 `cc=mpicc`。但 open-mpi 的 mpicc-wrapper 需要 `OPAL_PREFIX` 环境变量才能找到 MPI 安装位置——open-mpi recipe 只在 `runenv_info` 中设置此变量，build 环境（buildenv）中不存在。尝试通过 `os.environ` 和注入 `conanbuild.sh` 传递，均失败（Conan 的 `self.run()` 环境传递机制导致）。

最终放弃 mpicc，改用 clang + 显式 cache 变量：
- `MPI_INCLUDE_PATH` → 上游 CMakeLists.txt 已支持 `include_directories(${MPI_INCLUDE_PATH})`
- `MPI_LIBRARIES=mpi` → 生成 `-lmpi`
- `CMAKE_EXE_LINKER_FLAGS=-L<mpi_lib>` → **关键修复**：`MPI_LINK_FLAGS` 通过 `set_target_properties(LINK_FLAGS)` 设在静态库上，CMake 不会将此传播到可执行文件

### 2. 产物缺失补装

ParMETIS CMake 通过 `add_subdirectory(metis/libmetis)` 直接进入 libmetis，跳过了 `metis/CMakeLists.txt`，导致 metis.h 和 libmetis.a 编译了但不安装。在 `package()` 中手动 `copy()` 补装。

### 3. 上游测试缺失

ParMETIS 4.0.3 不发布测试套件（`add_subdirectory(test)` 被注释掉，代码未包含在 tarball 中）。
test_package 用自编测试，调用 `ParMETIS_V3_PartKway` 对 4 顶点环图分 2 区。

## 验证结果（鸿蒙 PC 实机）

- [x] conan create 编译通过
- [x] test_package 在 MPI singleton 模式下运行通过
- [x] 产物：libparmetis.a + libmetis.a + parmetis.h + metis.h + ptest/mtest/parmetis/pometis
