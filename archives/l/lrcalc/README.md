# lrcalc

Littlewood-Richardson 系数计算器（Anders S. Buch，C 语言实现），提供 `liblrcalc` 库与
`lrcalc`、`schubmult` 两个命令行程序。

## 功能概述

- `lrcalc`：对称函数运算——单个 Littlewood-Richardson 系数（`coef`/`lrcoef`）、
  斜 Schur 函数展开（`skew`）、Schur 函数乘积（`mult`）、余积（`coprod`）；
  另支持 Grassmann 极小量子上同调环（`-q`）与融合环（`-f`）模式
- `schubmult`：Schubert 多项式乘积的结构常数
- `liblrcalc`：上述功能的 C 库（partition/vector/hashtab 等导出接口）

## HarmonyOS PC 适配要点

- 上游 `config.guess`/`config.sub`（2012）不识别 HarmonyOS/`ohos`：补丁 0001 为
  `config.guess` 增加 `HarmonyOS` 分支，补丁 0002 让 `config.sub` 接受 `linux-ohos*`
  三元组（native 构建时 configure 的 build type 推断依赖 config.guess）
- HMDFS 下 `umask 077` 临时目录不可写（setgid 语义，知识 E011/E129），
  `config.status` 会以 `subs1.awk: Permission denied` 中止：补丁 0003 放宽为 `umask 022`
- profile 注入的 harmonybrew bash 作为 SHELL 会破坏 libtool/config.status（E386 同族）：
  configure 显式使用 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh`；`make -j1` 规避 HMDFS jobserver FIFO 限制
- 上游测试 `make check`（`Makefile.am` 的 `testsuite` 入口，8 项检查）在适配后原样运行并通过

## 依赖关系

- 编译依赖：无（仅 OHOS SDK clang/libc）
- 运行依赖：libc；共享库由 Conan 依赖链管理

## 参考资源

- 官网（源码下载）：https://sites.math.rutgers.edu/~asbuch/lrcalc/
- 上游源码仓库：https://bitbucket.org/asbuch/lrcalc
