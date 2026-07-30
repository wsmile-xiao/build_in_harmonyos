# dsdp 5.8 编译笔记（HarmonyOS PC · 手写 Makefile 处理）

## 定位

DSDP：半定规划（SDP）的对偶尺度内点法求解器。cvxopt 的 `dsdp` 模块用它。

上游是 2005 年前后的老项目（Argonne National Laboratory），此后基本停更，
构建系统很旧且**不完整**——本配方大部分工作是绕开它自身的缺陷。

## 上游构建系统的三个问题

### ① 工具全是裸名

`make.include` 里：

```make
CC       = gcc
ARCH     = ar cr
RANLIB   = ranlib
```

OHOS 上**没有 gcc**；且 conan 的 `self.run` 走 `/bin/sh`，最小 PATH 下裸 `ar`/`ranlib` 也未必
找得到（见 SKILL「自定义 build 里调工具：别假设在 PATH」）。故全部命令行覆盖成全路径：

```
make dsdplibrary DSDPROOT=<src> CC=<hnp>/clang ARCH="<hnp>/llvm-ar cr" RANLIB=<hnp>/llvm-ranlib
```

### ② `oshared` 目标不可用，且会烤死 soname

上游产共享库的目标是：

```make
oshared:
	${AR} x ${DSDPLIB}
	${SH_LD} ${DSDPLIBSO} *.o -o ${DSDPLIBSO}
```

两个毛病：

1. **`SH_LD` 在 `make.include` 里是注释掉的**（`#SH_LD = ${CC} -shared -W1,-soname,`，
   注意还把 `-Wl` 误写成了 `-W1`），所以这个目标根本跑不起来
2. 即使补上，它传的是 `-Wl,-soname,${DSDPLIBSO}`——`DSDPLIBSO` 是**全路径**，
   soname 会被烤成绝对路径，下游 `DT_NEEDED` 随之烤死路径。
   本仓的 `expat/2.8.2` 与 `poppler/25.12.0` 都栽在这类问题上

**故 make 只用来产静态库 `lib/libdsdp.a`，共享库自己链**：

```
clang -shared -o lib/libdsdp.so.5.8 \
      -Wl,--whole-archive lib/libdsdp.a -Wl,--no-whole-archive \
      -Wl,-soname,libdsdp.so.5 <openblas> -lm
```

`--whole-archive` 保证静态库里的目标文件全部导出（否则未被引用的符号会被丢弃）；
soname 给**纯名字**；链上 openblas 以解析 BLAS/LAPACK 符号。

### ③ `install` 目标名不副实

```make
install:
	make dsdplibrary
	make example
	make test
	make dmatlab
```

它并不安装任何东西（还会去建 MATLAB 接口）。故 `package()` 里自己拷头文件与库、
自己建版本软链 `libdsdp.so → .so.5 → .so.5.8`。

## 依赖

- `openblas/0.3.34`（提供 BLAS + LAPACK）

`make.include` 里默认的 `LAPACKBLAS = -llapack -lblas -lg2c -lm` 用不上——
`-lg2c` 是 g77 时代的产物，早已不存在；本配方在自己链共享库时直接指定 openblas。

## 验证

test_package 直接 `#include <dsdp5.h>` 并链接 libdsdp，**真解一个半定规划**：

```
max  y     s.t.  diag(1, 3) - y·I  ⪰ 0
```

约束即 `y ≤ 1`，故最优解 `y* = 1`（已知解析解）。经
`DSDPCreate` → `CreateSDPCone` → `SetBlockSize` → `SetADenseVecMat` → `SetDualObjective`
→ `Setup` → `Solve` 全流程，校验求得的 `y` 与解析解一致（容差 1e-4）。
该路径会走到内点迭代与稠密矩阵运算，后者用 BLAS/LAPACK。

共 8 条断言。

## 已知限制

- 上游已多年未更新，无上游测试套件可跑
- 仅建库，不建 examples / MATLAB 接口

## 状态

built（真机 `conan create -pr:h ohos-native -pr:b ohos-native` + test_package 全绿）
