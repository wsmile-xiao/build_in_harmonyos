# md5deep 4.4 — HarmonyOS PC 适配笔记

## 软件概述
md5deep 是 hashdeep 工具家族的一部分，用于递归计算并审计文件的
MD5 / SHA-1 / SHA-256 / Tiger / Whirlpool 哈希。构建产出 6 个可执行文件
（hashdeep、md5deep、sha1deep、sha256deep、whirlpooldeep、tigerdeep），
它们是同一份二进制，运行时按 `argv[0]` 分派到对应算法/接口。自带全部哈希
算法实现，无第三方运行时依赖（仅 libc + pthread，OHOS 上 pthread 属 musl）。

## 源码来源
- 上游仓库：https://github.com/jessek/hashdeep
- 4.4 的 GitHub release 资产 `md5deep-4.4.zip` 是 **Windows 二进制包**（含 .exe），
  不含源码，无法用于构建。
- 可构建源码取自官方 git tag 快照：
  `https://github.com/jessek/hashdeep/archive/refs/tags/v4.4.tar.gz`
  （strip_root 后顶层目录为 `hashdeep-4.4/`）。

## 关键适配点

### 1. 预生成 autotools 构建系统（prebuilt.tar.gz）
git 快照只含 `configure.ac` / `Makefile.am`，无 `configure` / `Makefile.in`，
需 autoreconf 引导。构建容器与 CI worker 均无 autoconf/automake/m4，无法现场
`bootstrap.sh`。因此在本机用 autoconf 2.71 + automake 1.16 生成以下文件并随配方
打包为 `prebuilt.tar.gz`，`build()` 中解压覆盖到源码树：
- `configure`、`config.h.in`、`aclocal.m4`
- `Makefile.in`、`src/Makefile.in`、`man/Makefile.in`、
  `tests/Makefile.in`、`tests/testfiles/Makefile.in`
- automake 辅助脚本 `compile`、`test-driver`

### 2. config.guess / config.sub 适配（E007）
快照自带的 `config.guess`/`config.sub` 停留在 2003 版，连 `aarch64-linux` 都无法
识别，已随 prebuilt.tar.gz 换成现代版本（automake 1.16，config.guess 2021-06-03 /
config.sub 2021-08-14）。但真实 OHOS worker 的 `uname -s` 返回 **HarmonyOS**，现代
config.guess 仍不识别 → `configure: error: cannot guess build type`。

本构建为本机构建（conan 判定 host==build，不传 `--host`，`cross_compiling=no`），
且 configure.ac 仅区分 `*linux*` 与 mingw，故 `build()` 对 OHOS：
- 将 `config.guess` 直接固定输出规范 OHOS 三元组 `aarch64-unknown-linux-ohos`
  （本配方 arch 固定 aarch64）；
- 给 `config.sub` 增加 `ohos*`（OS 列表）与 `linux-ohos*`（kernel-os 列表）识别。

configure 随即 `checking build/host system type... aarch64-unknown-linux-ohos`，
命中 configure.ac 的 `*-*-*linux*-*` 分支（定义 `__LINUX__`）。

> ⚠️ 本机 Docker 容器 `uname -s` 返回 Linux（config.guess 本可自识别为
> `-gnu`），无法复现 worker 的 HarmonyOS 场景；因 profile 本身是 os=OHOS，上述
> OHOS 分支在本机同样生效，本机构建即走 `-ohos` 三元组全流程验证通过。

### 3. OHOS shell 适配
- OHOS 无 `/bin/sh`，`build()` 将 `configure`、`config.sub` 及 automake 辅助脚本的
  shebang 重写为 `/data/service/hnp/bin/bash`，并向 configure 传 `SHELL=` 指向 bash。
  （config.guess 对 OHOS 被整体替换为 bash 脚本，自带正确 shebang。）
- 去除 `configure` 中 `umask 077 && mktemp/mkdir`（HMDFS 在 0700 目录下会阻止
  文件创建，否则 configure 的 config.status 临时文件创建失败）。

### 4. pthread
非 mingw 分支下 configure 的 `AX_PTHREAD` 宏自动探测 `-pthread` 并定义
`HAVE_PTHREAD`。clang + musl 下 `-pthread` 编译/链接均可用（pthread 符号在
musl libc 内），threadpool 正常链接，无需额外处理。

## 验证
- 构建：`conan create`（profile ohos-aarch64，clang 15 / libc++ / c++17）编译 6 个
  二进制均成功。
- test_package：对已知内容文件 `"hello\n"` 运行 md5deep/sha1deep/sha256deep/hashdeep，
  校验输出摘要等于参考值（MD5 `b1946ac9...`、SHA-1 `f572d396...`、
  SHA-256 `5891b5b5...`），并校验 `md5deep -v` 报告 4.4（`-v` 输出裸版本号；
  `-V` 输出的是版权声明，不含版本）。

## 补丁
- `0001-clang-cxx17-portability.patch`（portability）：clang++ `-std=c++17` 下的
  可移植性修复，改动 6 个上游源文件（src/dig.cpp、display.cpp、files.cpp、
  hash.cpp、hashlist.cpp、xml.h）：
  1. 在字符串字面量与 `PRI*` 宏之间补空格（否则触发 C++11
     reserved-user-defined-literal 错误，如 `"%"PRId64`）；
  2. mmap 结果由 `base>0`（指针与整型的有序比较，clang 报错）改为与
     `MAP_FAILED` 比较。

除该补丁外，autotools 构建系统经 prebuilt.tar.gz 提供，shebang / umask 077
适配在 `build()` 中对 configure 与 config.guess 处理，均不改动上游源文件。

## 依赖
无第三方依赖（libc + pthread）。
