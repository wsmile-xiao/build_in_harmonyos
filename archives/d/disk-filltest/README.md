# disk-filltest

disk-filltest 是一个用随机数据填充指定路径、随后回读并校验随机序列是否被正确落盘的
坏盘检测工具；写入与回读过程同时给出读写速度。上游实现是单个 ANSI C 文件
（`disk-filltest.c`，545 行），构建系统为最简 Makefile，官网
<https://panthema.net/2013/disk-filltest/>（源码仓库 <https://github.com/bingmann/disk-filltest>）。

## 功能概述

* 以 `random-########` 命名在当前目录（或 `-C` 指定目录）写入随机数据文件，直到磁盘写满或达到 `-f` 上限。
* 写完后回读，按同一伪随机序列（`-s` 种子）逐块校验，任何差异都会报 `Mismatch to random sequence` 并以非零码退出。
* `-r` 只校验已有数据；`-u` 校验通过后删除文件；`-U` 打开后立即 unlink，仅通过文件句柄写入与校验。
* `-S <MiB>` 控制单个文件大小，`-N` 跳过校验（用于擦盘），`-R <n>` 重复整个流程。

## OHOS 适配

* 上游代码零修改：OHOS clang 15 + musl 下使用上游默认 `CFLAGS`（`-O3 -W -Wall -ansi`）即可无警告编译。
* 无第三方依赖：仅包含 libc 与 POSIX 头文件（`errno/fcntl/getopt/inttypes/limits/stdio/stdlib/string/sys/time/time/unistd/sys/statvfs`）。
* 不使用 `make install`：上游 install 目标依赖 GNU `install` 与 `gzip`（生成 man 页），并把 `/usr/local` 前缀写进变量；配方改为直接把二进制、man 页与 `COPYING` 复制到 Conan 包目录，构建机与设备端行为一致。
* 已知平台限制：设备上 `install`/`gzip` 不在默认 PATH（仅 `/system/bin` 有），HMDFS 对 `chmod` 不生效；因此产物权限由复制时的源文件权限保留（上游编译产物本身可执行）。
* **使用安全**：该工具的语义就是“写满磁盘”。在多人共享的设备上验证时，所有测试都以 `-S 1 -f 1` 限定单文件 1 MiB、并在临时目录中运行后立即删除；绝不允许无限定地执行填充。

## 依赖关系

* 编译依赖：C 编译器（本适配使用 OHOS 原生 clang 15.0.4）、GNU make。
* 运行依赖：无（动态链接 musl libc）。

## 参考资料

* 项目主页：<https://panthema.net/2013/disk-filltest/>
* 源码仓库：<https://github.com/bingmann/disk-filltest>（tag `v0.8.2`）
* Debian 源包：`disk-filltest_0.8.2-1.1`（其 `.orig.tar.gz` 与 GitHub tag 归档哈希一致）
