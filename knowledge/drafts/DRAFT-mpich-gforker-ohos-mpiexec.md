# mpich（gforker 进程管理器）在 OHOS 上的 mpiexec 可用性确认

> Draft: DRAFT-MPICH-GFORKER-OHOS-MPIEXEC
> Stem: `DRAFT-mpich-gforker-ohos-mpiexec` — pairs with the same-stem `.kv`
> 来源：combblas 2.0.0 前置评估（PR #9161，2026-09-09）

## 基本信息

- **ID**: DRAFT-MPICH-GFORKER-OHOS-MPIEXEC
- **严重度**: 2
- **类别**: mpi, mpich, process-manager, ohos, portability
- **触发工具**: mpich|mpiexec|mpirun|conan|clang
- **阶段**: runtime|testing

## 错误特征

```
Error in system call mpiexec: No such file or directory|
mpiexec could not exec <binary>|
attempting to use an MPI routine .* before initializing or after finalizing MPICH|
invalid mpiexec argument -V（mpich 的 mpiexec 用法与 OpenMPI 不同）
```

## 可复现问题

在 OHOS 上适配依赖 MPI 的库（combblas）前，需确认 ohpcd 的 mpich 包能否
`mpiexec` 启动进程——这决定上游测试能否实测（还是 rule 1.2 声明）。直接
`mpiexec -V` 会报 `invalid mpiexec argument -V`（mpich 的 mpiexec 语法不同），
容易误判为不可用。

## 根因分析

ohpcd 的 mpich/4.0.3 配方配置：
- `--with-pm=gforker`（进程管理器是 **gforker**，非默认 Hydra）——gforker 通过
  fork/exec 启动子进程，不依赖 Hydra 的 pmi_proxy/hydra_pmi_proxy 组件
- `--with-pmi=simple`（简化 PMI 接口）
- `--disable-romio`（无 MPI-IO，见 E-new-mpich-noromio-mpio-compat）

gforker 是 mpich 最轻量的进程管理器：`mpiexec -n N` 即 fork N 个子进程执行目标，
无需额外 daemon——因此 OHOS（无 Hydra 二进制、进程管理受限）下依然可运行。

> **【2026-09-11 更正】多进程实际完全可用，先前"size=0"的记载有误。**
>
> 实测（正确探针）：`mpiexec -n 1` → `rank=0 size=1`；`-n 2` → `rank=0,1 size=2`；
> `-n 4` → `rank=0..3 size=4`（均 RC=0）。`MPI_Comm_size` 返回值正确。
>
> 原记载的 "MPI_Comm_size 返回 size=0 → 多进程语义受限" **并非环境限制，而是探针
> 自身的缺陷**：
>
> ```c
> // ❌ 原探针：格式串里没有 %d，输出恒为 size=0，与实际值无关
> printf("mpi OK rank=0 size=0\n", rank, size);
> //   warning: data argument not used by format string [-Wformat-extra-args]
>
> // ✅ 正确写法
> printf("rank=%d size=%d\n", rank, size);
> ```
>
> 编译器其实已给出 `-Wformat-extra-args` 警告——**探针类工具务必留意编译告警**，
> 否则会把"测量工具坏了"误读成"被测系统受限"。

## 推荐方案

**方法**: gforker-multiprocess-verification

**说明**: >
  (1) 确认包内二进制：mpich 包 `bin/` 含 mpiexec/mpichversion/parkill/mpicc，
      `cpp_info.bindirs=["bin"]`；
  (2) 版本验证用 `mpiexec -usize 1 <cmd>` 或直接 `mpichversion`（不要用 OpenMPI
      风格的 `-V`，mpich 会报 invalid argument 误导判断）；
  (3) 最小 MPI 探针（MPI_Init/Comm_rank/Comm_size/Finalize）编译链接 libmpi.so；
      ⚠️ **printf 必须带 `%d`**——写成 `printf("size=0\n", size)` 会因缺格式符而
      恒输出 0，是最隐蔽的误判来源（本轮即因此误报 size=0）。正确写法
      `printf("rank=%d size=%d\n", rank, size);`，实测 `-n 1/2/4` 分别得
      `size=1/2/4`（均 RC=0）；
  (4) 结论映射：单进程与多进程**均可运行** → 上游测试不因进程数受限；若某用例
      失败，应从用例自身（数据/算法/运行时）排查，**不要先归因于"多进程语义受限"**。

**验证/命令**:
```
conan download "mpich/4.0.3" -r=ohpcd
# 最小探针编译：clang -I<mpich>/include <probe>.c <mpich>/lib/libmpi.so -o probe
LD_LIBRARY_PATH=<mpich>/lib mpiexec -n 1 ./probe   # 预期 rank=0 size=1, RC=0
LD_LIBRARY_PATH=<mpich>/lib mpiexec -n 2 ./probe   # 预期 rank=0/1 size=2, RC=0
LD_LIBRARY_PATH=<mpich>/lib mpiexec -n 4 ./probe   # 预期 rank=0..3 size=4, RC=0
```

## 关键词

mpich, gforker, mpiexec, mpirun, pmi=simple, hydra, MPI_Comm_size, size=1,
multi-process, printf-format-bug, -Wformat-extra-args, false-negative,
OHOS, process-manager, combblas, clang
