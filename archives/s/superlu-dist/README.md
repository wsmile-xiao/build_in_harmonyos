# SuperLU_DIST

SuperLU_DIST 是 SuperLU 的**分布式内存（MPI）**版本：按进程网格划分矩阵，
使用 ParMETIS 做填充约减排序，求解大型稀疏非对称线性方程组。

- 上游：<https://github.com/xiaoyeli/superlu_dist>
- 许可证：BSD-3-Clause
- 构建系统：CMake
- 适配的版本：见各版本子目录（当前 `9.0.0`）

## 与 `superlu` 的区别

| 包 | 并行模型 | 适用场景 |
|---|---|---|
| `superlu` | 串行（单进程） | 中小规模、单机 |
| **`superlu-dist`** | **MPI 分布式** | 大规模、多进程；Trilinos/Amesos2 的 `SuperLUDist` TPL 上游 |

两者是**不同的包**，不可互相替代（Trilinos 侧分别对应
`FindTPLSuperLUDist.cmake` 与 `FindTPLSuperLU.cmake`）。

## 依赖

- `open-mpi/5.0.10` —— MPI 实现（须与 parmetis 一致）
- `parmetis/4.0.3` —— 并行排序（自带 METIS）
- `openblas/0.3.33` —— BLAS/LAPACK

## 使用

```python
self.requires("superlu-dist/9.0.0")
```

```cmake
find_package(superlu-dist REQUIRED)
target_link_libraries(app PRIVATE superlu-dist::superlu-dist)
```

公开头 `superlu_defs.h` 直接包含 `<mpi.h>`，本包已把 MPI 头目录与
OpenMP 链接标志转发给下游，消费者无需额外配置。

各版本的适配细节（含踩坑与验证数据）见对应版本目录下的 `notes.md`。
