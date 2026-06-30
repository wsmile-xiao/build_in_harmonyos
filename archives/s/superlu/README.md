# SuperLU

SuperLU 是一个用于求解大型稀疏线性方程组的通用库。它使用带有部分 pivoting 的高斯消元法（GEPP）。

## 功能特性

- 支持 single precision (s), double precision (d), complex (c), double complex (z) 四种精度
- 支持多种稀疏矩阵格式（Harwell-Boeing, Matrix Market, Triple 等）
- 提供列预排序以减少填充元
- 支持迭代细化以提高解的精度

## 版本信息

- 当前版本: 5.3.0
- 发布日期: 2020-10-17

## 依赖

- CBLAS（内部实现或外部 BLAS 库）
- C 编译器（支持 ANSI C）

## 构建系统

- CMake（推荐）
- 传统 Makefile（需要手动编辑 make.inc）

## 使用说明

SuperLU 提供静态库 `libsuperlu.a`，可通过 CMake 或 pkg-config 集成到项目中。

```bash
# 使用 pkg-config
pkg-config --cflags superlu
pkg-config --libs superlu

# 使用 CMake
find_package(SuperLU REQUIRED)
target_link_libraries(your_target SuperLU::superlu)
```

## 测试

SuperLU 包含完整的测试套件，测试单精度/双精度/复数/双复数四种精度的求解器。

## 许可证

BSD 2-Clause License

## 相关资源

- 官方网站: http://crd-legacy.lbl.gov/~xiaoye/SuperLU/
- GitHub: https://github.com/xiaoyeli/superlu