# PT-SCOTCH

PT-SCOTCH 是 SCOTCH 的**并行（MPI）**版本：在分布式内存下完成图/网格划分与
稀疏矩阵排序。它是 TriBITS `FindTPLScotch.cmake` 在 `TPL_ENABLE_MPI` 时要求
的对象（该分支强制 `ptscotch.h` + `ptscotch ptscotcherr scotch scotcherr`）。

- 上游：<https://gitlab.inria.fr/scotch/scotch>
- 许可证：CeCILL-C
- 构建系统：CMake
- 适配版本：见各版本子目录（当前 `7.0.12`）

## 与 `scotch` 的区别

| 包 | 并行模型 | 产物 | 备注 |
|---|---|---|---|
| `scotch/7.0.12` | 串行 | `scotch.h`、`libscotch.a` | 他人归档，本包**不修改**它 |
| **`ptscotch/7.0.12`** | **MPI 并行** | `ptscotch.h`、`libptscotch.a` + 串行层 | 本包（`BUILD_PTSCOTCH=ON`） |

两者出自**同一上游源码树**：同一份 tarball 用 `-DBUILD_PTSCOTCH=ON/False` 分别
产出并行/串行层。之所以拆成两个包而不是给 `scotch` 加选项：`archives/s/scotch`
属他人归档，按贡献规范不越权修改；仓内已有 `superlu`（串行）/`superlu-dist`
（MPI）这一「同名拆分」先例。

## 依赖

- `mpich/5.0.1.2` —— MPI 运行时（与仓内 `trilinos` 同选）
- `bzip2/1.0.8`、`xz/5.6.2`、`zlib/1.3.1` —— 可选的压缩后端

## 使用

```python
self.requires("ptscotch/7.0.12")
```

```cmake
find_package(ptscotch REQUIRED)
target_link_libraries(app PRIVATE ptscotch::ptscotch)
```

公开头 `ptscotch.h` 依赖 `<mpi.h>`，本包已把 MPI 依赖（含头目录与库）通过
接口传递给消费者，无需额外配置。

各版本的适配细节（含踩坑与验证数据）见对应版本目录下的 `notes.md`。
