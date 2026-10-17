# libf2c (netlib), packaged as libf2c2

`libf2c2` 是 **f2c 的 Fortran 运行时库**。f2c 把 Fortran 源码翻译成 C，
但把内在函数、字符串处理以及整套格式化/列表定向 I/O 运行时留在这个库里，
所以 f2c 的输出通常按 `-lf2c` 编译链接。本目录归档该运行时的适配配方。

包名沿用 Debian 对该运行时的命名（源码包与二进制包都叫 `libf2c2`，
与 SONAME `libf2c.so.2` 对应）。

## 功能概述

- Fortran 内在函数的 C 实现：类型转换（`i_nint`、`d_int`、`h_dnnt` …）、
  数学函数（`pow_dd`、`d_lg10`、`erf_`、`d_prod` …）、复数与位操作
- 字符运行时：`s_cmp`、`s_copy`、`s_cat`、`i_indx`、`h_len` 等，按 Fortran
  的空格补齐语义工作
- 完整 I/O 运行时：单位表、格式化（`s_wsfe`/`do_fio`/`e_wsfe`）、
  列表定向（`s_wsle`/`do_lio`/`e_wsle`、`s_rsle`/`e_rsle`）、内部读写、
  `f_open`/`f_clos`/`f_rew`/`f_inqu`、`-trapuv` 所需的 `_uninit_f2c`
- 程序启动例程：`main`（调用 `f_init` → `MAIN__` → `f_exit`）与
  `getarg_`/`iargc_`/`getenv_`/`system_`/`signal_`

## OHOS 适配

- 源码来自 netlib 官方 `https://netlib.org/f2c/libf2c.zip`（无版本号文件，
  版本号 `20240504` 为 Debian 打包该快照时使用的上游版本）。
- 上游自带 `makefile.u`，属性上是 in-source Makefile 工程，本适配直接驱动它，
  没有引入额外的构建系统。
- 两个可移植性补丁，均非平台宏、均不改变功能语义：
  1. `uninit.c` 的 `fpu_control.h`（glibc 专有）判据收窄到 glibc；
  2. `main.c` 的 `main`/`MAIN__` 改为 weak，使共享库不再带未定义符号
     （否则 lld 默认的 `--no-allow-shlib-undefined` 会拒绝任何链接方）。
- `arith.h` 由 `arithchk.c` 在构建时现场编译执行生成，因此构建机需与目标机
  同架构；本仓库的 `ohos-aarch64` profile 是 OHOS/aarch64 原生编译。
- 已知差异：Debian 的 `libf2c2` 二进制包还提供 `libf2c_i2.so.2`
  （`f2c -i2` 生成代码使用的 ABI）。本仓库没有 f2c 编译器包，生态中不存在
  产生 `-i2` 代码的来源，且两个 ABI 导出同名符号无法共用链接，故本配方
  只构建默认 ABI。

## 依赖关系

- 编译依赖：无
- 运行依赖：libc（数学函数在 HarmonyOS 上由 libc 提供；`cpp_info.system_libs`
  仍声明 `m` 以便静态链接场景）

## 参考资料

- 上游：<https://netlib.org/f2c/>（`libf2c.zip`、`makefile.u` 与 README）
- 许可：AT&T / Lucent / Bellcore 声明，见包内 `licenses/Notice`
- 各发行版打包（含其下游补丁，本适配未采用）：Debian `libf2c2` 20240504-1
