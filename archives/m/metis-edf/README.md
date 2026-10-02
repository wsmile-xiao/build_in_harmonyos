# metis-edf — METIS 4.0.1 的 Code_Aster/EDF 变体

`metis-edf` 是 EDF 为 **Code_Aster** 维护的 METIS 4.0.1 分支：把源码里所有 `int`
计数器加宽为 `long`（支持超大规模问题），并新增 Code_Aster 专用的排序驱动
`onmetis`（输入 `fort.81`，输出 `fort.85`）。库本身提供图的串行划分、网格划分和
稀疏矩阵填充约减排序。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/libmetis.a` | METIS 4.0.1 库（`METIS_PartGraphRecursive`、`METIS_PartGraphKway`、`METIS_NodeND` 等） |
| `include/metis.h` 等 6 个头 | 公共 API（`metis.h` 会包含 `defs.h`/`struct.h`/`macros.h`/`rename.h`/`proto.h`） |
| `bin/onmetis` | Code_Aster 排序驱动：`onmetis fort.81`（生成 `fort.85`、`fort.81.iperm`） |
| `bin/pmetis` | 递归二分划分：`pmetis <GraphFile> <Nparts>` |
| `bin/kmetis` | k 路划分：`kmetis <GraphFile> <Nparts>` |

## 用法

```sh
# 库
cc app.c -I <prefix>/include -L <prefix>/lib -lmetis -lm

# 命令行
pmetis graph.file 4      # 生成 graph.file.part.4
kmetis graph.file 4
onmetis fort.81          # Code_Aster 格式
onmetis --version        # metis-edf-4.1
```

## OHOS 适配要点

- 上游 `Makefile` → `CONFIG/configure` 只识别 SunOS/OSF1/IRIX64/Linux/Cygwin，并硬编码
  gcc/g77/gfortran，因此**绕过 configure**，用 OHOS clang 直接编译 `Lib/*.c` 与
  `Programs/*.c`。
- `onmetis` 链接三支 Fortran 例程（`lect00.f`/`lect11.f`/`ecri11.f`）。OHOS 无 Fortran
  编译器，制品仓亦无 gfortran/flang，故按 **ISO C 等价移植**为 `port_fortran_io.c`
  （原 `.f` 文件保留在树里）。三支例程只负责 `fort.81`/`fort.85` 的定长格式读写。
- 编译需要 `-fcommon`，并需把隐式函数声明降级为警告（`proto.h` 里 `GKfree` 的声明被上游
  注释掉了）。
- 上游测试为 `Test/Makefile` 的 `fort.85` 与 `vers_check` 两个 target，`build()` 内实跑。
  随包的 `Test/*.ref` 与任何现代 libc 构建都不同（METIS 4.x 排序依赖 libc 的
  `rand()`/`drand48()` 流），故做结构校验而非字节比对。

## 参考资料

- 上游：<http://glaros.dtc.umn.edu/gkhome/metis/metis/overview>
- 源码 tarball：Ubuntu multiverse `metis-edf_4.1-2.orig.tar.gz`
- 许可证：METIS（University of Minnesota，非自由）
