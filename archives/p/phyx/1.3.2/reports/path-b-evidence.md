# phyx 1.3.2 路径 B 三臂链接实证

> 日期：2026-10-11
> 环境：HarmonyOS PC aarch64，clang/LLD 15.0.4，GNU Make 4.4.1
> 对象：同一份 phyx `pxseqgen` 目标文件，仅替换最终链接库清单

## 实验设计

三臂实验固定编译器、目标文件、依赖版本和搜索目录，只改变 `CPP_LIBS`：

```text
A  -llapack -lblas -lpthread -lm -lnlopt -larmadillo
B  -llapack -lblas -lpthread -lm -lnlopt -larmadillo -lFortranRuntime -lFortranDecimal
C  -larmadillo -lm -lpthread -lnlopt
```

其中 A 对应上游手写 Makefile 的 reference BLAS/LAPACK 链接方式；B 是机械追加
Flang 运行时的常见“能链接”修复；C 对应修复后由 Autoconf 探测结果生成的单一
Armadillo 提供者链接线。

## 可核验结果

### A：原始链接线失败

退出码为 2。LLD 从 `liblapack.a` 拉入 Fortran 对象后报告：

```text
undefined symbol: _FortranACharacterCompareScalar1
undefined symbol: _FortranAioBeginExternalFormattedOutput
undefined symbol: _FortranAioOutputAscii
undefined symbol: _FortranAStopStatement
```

这证明错误来自 reference LAPACK 的 Flang 运行时边界，不是 Armadillo API 或 C++
源码编译失败。

### B：追加 FortranRuntime 后出现双数学提供者

退出码为 0，但制品同时满足以下两个事实：

```text
llvm-nm --defined-only pxseqgen
0000000000117468 T dgemm_
0000000000289fb4 T dgesv_
0000000000120d54 T dgetrf_

llvm-readelf -d pxseqgen
NEEDED Shared library: [libarmadillo.so]

llvm-readelf -d libarmadillo.so
NEEDED Shared library: [libopenblas.so.0]
```

因此 reference BLAS/LAPACK 已静态进入可执行文件，而 Armadillo 仍把 OpenBLAS 带入
动态闭包。“链接成功”没有恢复数学后端唯一性。

### C：消费 Autoconf 提供者结论

退出码为 0；`pxseqgen` 只直接依赖 `libarmadillo.so`、C++ 运行库和 libc；禁止的
reference BLAS/LAPACK/FortranRuntime 动态依赖为零，代表性 BLAS/LAPACK 已定义符号
为零，`pxseqgen -V` 实际执行退出码为 0。

## 证据完整性

原始命令、完整链接输出、工具版本、退出码和 ELF/符号表结果保存在仓库外：

```text
.task-results/phyx-1.3.2/logs/three-arm-link-evidence.log
SHA256: 5a20094e3977b9726db529253af8f11453e6dfc859ce833f15da5bf9e5a5c5c5
```

提交中只保留本脱敏摘要与哈希，不包含 Conan 缓存路径、个人绝对路径或原始运行日志。
