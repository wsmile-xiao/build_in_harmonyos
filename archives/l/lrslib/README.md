# lrslib

> 多面体顶点/面枚举工具集 —— 精确有理数算术的 reverse search 实现（C 库 + 命令行工具）

## 简介

lrslib 是 David Avis（McGill 大学）的 reverse search 实现，用于**凸多面体**的
H-表示（半空间不等式组）与 V-表示（顶点/射线）之间的精确转换、冗余约束剔除、
面/体积枚举，以及双人博弈 Nash 均衡求解。全部计算走**精确有理数算术**，
不引入浮点误差。

上游发布包同时装出：

* `liblrs.so` —— C 库。库里**同时**编入三套算术后端（64bit `lrslong`、
  128bit `lrslong+B128`、`gmp`），调用方通过编译宏经 `lrslib.h` 的 `suf()` 选出符号后缀。
* 命令行工具 `lrs`（H↔V 转换、面枚举、体积）与 `lrsnash`（Nash 均衡），
  以及 `lrs` 的 argv[0] 别名 `redund` / `minrep` / `fel`。

## OHOS 适配要点

1. **临时目录不能写死 `/tmp`**：平台沙箱里 `/tmp` 只读，而上游把
   `mkstemp()` 的模板写成字面量 `/tmp/lrs_restartXXXXXX`
   （`lrs` 的 64/128bit 溢出重启）与 `/tmp/lrs_stdinXXXXXX`（stdin 暂存）。
   本包补丁改为 `$TMPDIR` 优先、`/tmp` 兜底；运行时请让 `TMPDIR` 指向可写目录。
2. **可执行文件的 RUNPATH 是 `$ORIGIN/../lib`**：上游 install 布局把工具放 `bin/`、
   库放 `lib/`，却完全不给 RUNPATH，装完只能靠 `LD_LIBRARY_PATH`。本包补丁用
   `RUNPATHFLAGS ?= -Wl,-rpath,'$$ORIGIN/../lib'` 修好，因此
   **裸环境**（不 source conanrun）也能直接跑 `bin/lrs`。
3. **`--version` / `--help` 是本包补丁新增的**：上游把每个参数都当输入文件名。
   `lrs --version` 输出 `lrs (lrslib 7.3)`，`lrsnash --version` 输出 `lrsnash (lrslib 7.3)`。
   其余选项写在**输入文件里**（`begin` 行之前），不是命令行开关。
4. **只出共享库**：上游 makefile 只有 `all-shared` 目标，没有静态库目标，
   因此 `-o shared=False` 会抛 `ConanInvalidConfiguration`。
5. **消费方要自己选算术后端**：`-DMA -DGMP`（GMP）、`-DMA -DB128 -DLRSLONG`（128bit）
   或 `-DMA -DLRSLONG`（64bit）。不选任何一套时 `lrslib.h` 会挑内置 `lrsmp` 后端，
   而 `liblrs.so` 里并没有编入该后端，链接会失败。

## 排除与替代

* `mplrs` / `mplrsgmp`（MPI 并行版）：需要 `mpicc` 与 OpenMPI，平台工具链不含；
  上游 `default: lrs lrsgmp` 同样不含它们。
* `plrs` / `plrsgmp`（OpenMP 版）：需要 libomp，未纳入本包。
* 单精度算术后端变体（`lrs1`/`lrs2`/`lrsmp`/`lrsnash1`/`lrsnash2`）：上游 `make single`
  目标，未纳入；需要时可用 `lrslib.h` 的 `-DMA -DLRSLONG` / `-DMA -DB128 -DLRSLONG`
  直接消费 `liblrs.so`。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| gmp | 6.3.0 | ohpcd 制品仓；该版本**只提供 `libgmp.a`（静态）**，GMP 代码被静态并入 `liblrs.so` |

## 功能验证

```sh
# 1. 工具能跑（裸环境，不 source conanrun —— 这才证明 RUNPATH 正确）
env -u LD_LIBRARY_PATH <pkg>/bin/lrs --version        # lrs (lrslib 7.3)
env -u LD_LIBRARY_PATH <pkg>/bin/lrsnash --version    # lrsnash (lrslib 7.3)

# 2. 真实计算：上游 cube.ine 是 3-立方体，恰有 8 个顶点
TMPDIR=$(mktemp -d) env -u LD_LIBRARY_PATH <pkg>/bin/lrs cube.ine | grep Totals
# *Totals: vertices=8 rays=0 bases=8 integer_vertices=8  max_vertex_depth=3

# 3. 别名（argv[0] 分派）
env -u LD_LIBRARY_PATH <pkg>/bin/redund cube.ine | head -3
env -u LD_LIBRARY_PATH <pkg>/bin/minrep cube.ine | head -3
env -u LD_LIBRARY_PATH <pkg>/bin/fel cube.ine | head -3
```

## 参考

- [官方文档 / 下载页](https://cgm.cs.mcgill.ca/~avis/C/lrs.html)
- [源码归档](https://cgm.cs.mcgill.ca/~avis/C/lrslib/archive/)
- [lrslib 手册](https://cgm.cs.mcgill.ca/~avis/C/lrslib/USERGUIDE.html)
