# lfanew 0-20230825 适配笔记

## 编译环境
- 构建系统: autotools（上游自带生成好的 configure + Makefile.in，无需 autoreconf）
- 编译日期: 2026-09-26
- 编译器: OHOS SDK clang 15（/data/service/hnp/bin/clang → aarch64-unknown-linux-ohos-clang），llvm-ar
- 构建机: x86_64 runner，交叉目标 aarch64-linux-ohos；qemu-aarch64（binfmt）用于运行静态产物
- 状态: published（conan-verify G1–G4 通过，W3 conan create 通过）

## 源码
- 上游: https://gitlab.com/tkchia/lfanew ，tag `20230825` = commit 9f82806bc936a2df7ba28d2e428bb119a969a5c4
- conandata URL: `https://gitlab.com/tkchia/lfanew/-/archive/20230825/lfanew-20230825.tar.gz`
  sha256 `ae3353378b892d37e5840429afe0908e61a2054efa619b0bd01d945440fb7423`（两次下载一致）
- 任务给出的 Debian `lfanew_0~20230825+dfsg.orig.tar.xz` 是下游重打包（R39/PF7 禁用），
  与上游 tag 逐文件 diff：仅少了 `3rd-party/`（Takeda 的 MS-DOS player 7z 包，只用于上游测试/默认目标），其余完全一致。
- 版本号 `0-20230825` 沿用任务指定（对应 Debian `0~20230825`，上游 tag `20230825`）。

## 编译步骤

手工探索（out-of-tree）：

```bash
../lfanew-0-20230825.work/configure --host=aarch64-unknown-linux-musl --prefix=/usr \
  CC=/data/service/hnp/bin/clang AR=$NDK/llvm-ar RANLIB=$NDK/llvm-ranlib CFLAGS="-O2 -fPIC"
make install DESTDIR=$PWD/stage      # 只装 bin/lfanew、lib/libfanew.a、include/{lfanew,nexgen}
```

配方（conanfile.py）：
- `generate()`：OHOS 下 `--host=aarch64-unknown-linux-musl`；构建机为 OHOS（`settings_build.os`）时再加 `--build=aarch64-unknown-linux-musl`；`extra_ldflags=-static`；
  `CC` 取 profile 的 `tools.build:compiler_executables`（R33），`AR` 为编译器同目录 `llvm-ar`，`RANLIB="llvm-ar s"`。
- `build()`：先把随包 `configure` 的 `umask 077` 改为 `umask 022`（E129，HMDFS），再 `make lfanew a/libfanew.a -j1`；**不跑默认目标**——默认目标还会用 MinGW 交叉编译器 + 7z + upx
  构建 `3rd-party.build/msdos_i486.pe`（上游测试用的 DOS 模拟器），不属于包内容。
- `package()`：`make install DESTDIR=<package_folder>` + `LICENSE`。
- 产物：`bin/lfanew`（静态 AArch64 ELF）、`lib/libfanew.a`、`include/lfanew/{_config.h,_version.h,dirent.h,io.h}`、`include/nexgen/{mzendian.h,mzhdr.h}`。
  既有库又有 CLI → `package_type=static-library` + `bindirs=["bin"]`，软件级 `commands.json` 已声明（R38）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Invalid configuration 'aarch64-linux-ohos': system 'ohos' not recognized`；`aarch64-unknown-linux-ohos` 也报 `machine 'aarch64-unknown-linux' not recognized` | 源码自带 2016 年 config.sub，不认 ohos（E122 针对新版脚本，不适用） | configure.ac 无 `AC_RUN_IFELSE`/`AC_TRY_RUN` 运行期探测，不改 config.sub，直接 `--host=aarch64-unknown-linux-musl`（OHOS libc 即 musl）；知识草稿 E721 回退方案 |
| 2 | `a/direntdup.c:32:37: error: use of undeclared identifier 'NAME_MAX'` | glibc `<dirent.h>` 间接带出 `NAME_MAX`，OHOS musl `<dirent.h>` 不包含 `<limits.h>` | `patches/0001-a-direntdup.c.patch` 补一行 `#include <limits.h>`（无平台宏）；知识草稿 E721。引擎原误配 E493 |
| 3 | x86 runner 上无法运行动态 OHOS 产物（无 `/lib/ld-musl-aarch64.so.1`，E544） | 交叉构建机 | `lfanew` 只依赖 libc，按 E544 以 `-static` 链接交付；test_package 消费者也静态链接，经 qemu-aarch64 实跑的就是交付产物本身 |
| 4 | conan-verify G0 提示 E490（autotools 脚本执行位） | 预防性提示 | 上游 tarball 中 configure/config.* 均为 0755，本地 conan create 通过，未加额外处理 |
| 5 | CI（HarmonyOS 原生构建机，`uname -s = HarmonyOS`）首轮红：`config.guess: unable to guess system type` → `configure: error: cannot guess build type` | 2016 版 config.guess 无 HarmonyOS 分支（E007）；本地 x86 runner 上 config.guess 能认出宿主，W3 未暴露 | `settings_build.os == "OHOS"` 时补 `--build=aarch64-unknown-linux-musl`（与 host 相同，configure 仍按原生构建，`cross compiling... no`）；本地复验 39/39 |
| 6 | CI 第 2 轮红：`./config.status: line 610: ./confXXXXXX/subs1.awk: Permission denied` → `could not setup config files machinery` | configure 以 `umask 077` 建 config.status 临时目录，HMDFS 给新目录置 setgid，属主也无法写入（E129）；本地 ext4 不复现 | `build()` 中 `replace_in_file(configure, "umask 077", "umask 022")`（仓内 1129 个配方同手法）；本地复验 39/39 |

## 源码修改

- `patches/0001-a-direntdup.c.patch`（portability，+1/-0）：`a/direntdup.c` 在 `#include <stddef.h>` 前补 `#include <limits.h>`。
  由 `refresh-patch --auto` 生成；对 glibc/MinGW 同样正确，可回馈上游。

## 依赖版本

无第三方依赖（仅 libc）。W0：`requirements()` 为空，无需 `conan download` 探测。

## 上游测试清点（R51）

框架：GNU autotest（`tests/testsuite.at` 入口，需 autom4te 生成 `tests/testsuite`，源码包未附带生成物，本机无 autoconf）。
`grep -c AT_SETUP tests/*.at` → 8 个用例：

| 文件 | 用例 | 依赖 | 本次结果 |
|------|------|------|----------|
| metacheck.at | dos2unix / nasm / MS-DOS 程序运行器 / Windows 程序运行器（4） | dos2unix、nasm、emu2/86sim/msdos、MinGW + wine | 未运行：纯测试环境自检，工具在 OHOS/CI 上不存在 |
| lfanew.at | 默认模式；`-U`/`-S` 模式（2） | nasm 汇编 MZ、DOS 运行器执行、MinGW 编译 PE、wine 执行 | 未运行：同上；同等 CLI 语义由 test_package [2][3][4] 覆盖 |
| dirent.h.at | scandir（1） | 主机 C 编译器；平台自带 scandir 时 `AT_SKIP_IF` | 手工复现：OHOS clang `-static` 编译链接 `libfanew.a`，qemu-aarch64 运行 rc=0（上游在此平台会 skip，这里仍实际执行） |
| io.h.at | _binmode（1） | 主机 C 编译器（上游只编译） | 手工复现：编译 + qemu-aarch64 运行 rc=0 |

上游 N=8，可执行 N′=2，通过 2/2；其余 6 个不可运行的具体原因见上表（x86 DOS/Windows 工具链与模拟器，非 OHOS 生态）。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify lfanew 0-20230825
# G1/G0/G2/G3/G4 PASS；conan create 日志 reports/conan-create.log
# test package: RUN: "/usr/bin/qemu-aarch64" "./test_lfanew" "<pkg>/bin/lfanew" "<workdir>" "/usr/bin/qemu-aarch64"
# lfanew consumer test: 39/39 checks passed   (exit 0)
```

鸿蒙特有测试（rule12）：`test_package/test_lfanew.c`，5 个用例、39 项断言，完整消费者流程——
Conan 以 OHOS profile 消费本包（CMakeDeps `lfanew::lfanew` → `libfanew.a` + 头文件）→ 编译消费者 →
运行消费者，由它构造 MZ 文件、驱动**包内** `bin/lfanew` 的三种模式与两条拒绝路径、再用包的头文件解析产物，
最后经 `<lfanew/dirent.h>` 调 `scandir()`（configure 检出 OHOS libc 自带实现）扫描工作目录，并用本包 `libfanew.a` 的 `_direntdup()`（补丁 0001 改动的代码）复制每个条目。
本地证据：x86 runner 经 qemu-aarch64 实跑，被执行的 `lfanew` 就是交付的静态 ELF（非重链副本），退出码 0。
CI 上同一 test_package 在 `conan create` 必跑路径中执行：AArch64 runner 直接运行，x86 runner 需 qemu-aarch64（否则报错而非跳过）；以 CI 日志出现 `39/39 checks passed` 为准。

## 注意事项

- `lfanew` 与消费者探针均静态链接（libc-only，E544 先例 whichman 等）；test_package 在既非 AArch64 又无 qemu-aarch64 的机器上会失败而不是跳过。
- 上游默认 `make`（all）目标需要 7z/MinGW/upx，配方刻意只构建 install 所需目标。
---

**编译结束**: 2026-09-26 12:28
**最终状态**: published
