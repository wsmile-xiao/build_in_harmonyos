# runlim

`runlim` 运行给定命令并对其**及其全部子进程**进行资源采样与限制：通过 `/proc` 文件系统周期采样 CPU 时间、墙钟时间与常驻内存（RSS），超限时杀掉整个进程树；运行结束输出统计（time/real/space/samples）。它是 SAT/CP 竞赛与基准测试社区事实上的资源限制器。

上游 [fmv.jku.at/runlim](https://fmv.jku.at/runlim/)（作者 Armin Biere，JKU；BSD-4-Clause）。

## 功能概述

- `runlim [option ...] program [arg ...]`
  - `-t/--time-limit=<秒>`：CPU 时间限制（同时设置 RLIMIT_CPU 与 RLIMIT_AS）
  - `-r/--real-time-limit=<秒>`：墙钟时间限制（多线程程序适用）
  - `-s/--space-limit=<MB>`：常驻内存限制（采样击杀；配合 `-t` 时同时设置 RLIMIT_AS）
  - `-o/--output-file=<文件>`：日志输出文件（默认 stderr）
  - `-k/--kill`：把子进程收到的信号传播给 runlim 自身
  - `-h/--help`、`--version`
- 退出码（runlim 自身状态，**子进程退出码被忽略**）：0=ok、1=exec 失败、2=out of time、3=out of memory、4=子进程 SIGSEGV、5=SIGBUS、6=fork 失败、7=内部错误、11=其他信号

## 依赖关系

- 编译依赖：无（单文件 C + POSIX，仅链接系统 libc）
- 运行依赖：无（需 Linux/OHOS 风格 `/proc`）

## OHOS 适配要点

- 官方 tarball 为 `configure.sh` + `makefile.in` 的极简 POSIX 构建；`configure.sh` 将 `$CC/$CFLAGS` 代入 makefile 后单次调用编译器产出 `bin/runlim`
- 补丁 0001（RLIMIT_AS 单位修复）：`space_limit`（MB）被原样当字节传给 `setrlimit(RLIMIT_AS)`，导致 `-t`/`-t -s` 触发 setrlimit 后子进程 `execvp` 恒失败（ENOMEM）；改为按字节换算。设备实测：修复前 `runlim -t 1 ...` → "execvp failed" rc=1；修复后 → "out of time" rc=2。上游单位缺陷，无平台宏
- `/proc/<pid>/stat` 字段布局与标准 Linux 一致（实测 OHOS 内核 1.12：field 23=vsize 字节、field 24=rss 页），runlim 的采样解析无需适配
- 上游无测试套件；`test_package/test_runlim.sh` 补 31 条消费侧功能断言（真实执行已安装二进制），清点证据见 [1.10/test_package/MANIFEST.yml](1.10/test_package/MANIFEST.yml)

## 参考资料

- 上游主页：<https://fmv.jku.at/runlim/>
- 上游说明：<https://fmv.jku.at/runlim/README>
- 发行包：<https://fmv.jku.at/runlim/runlim-1.10.tar.gz>

## 版本

- `1.10` — 适配 HarmonyOS PC（aarch64-linux-ohos / armv8）；1 个 RLIMIT_AS 单位修复补丁；见 [1.10/notes.md](1.10/notes.md)

## 产物

| 路径 | 说明 |
|------|------|
| `bin/runlim` | 主程序（arm64 ELF） |
