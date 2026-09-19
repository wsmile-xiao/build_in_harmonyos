# dietlibc

## 简介

dietlibc 是一个轻量级、体积优化的 C 标准库（libc）实现，专注静态链接，可作为 glibc/musl 之外的替代方案。由 Felix von Leitner（fefe）开发，许可证 GPL-2.0-or-later。

## OHOS 适配

### 适配要点
- 上游构建系统为**自定义 Makefile**（非 autotools/cmake），通过 `ARCH`/`CC`/`AR` 交叉编译。
- **aarch64 完整支持**：`aarch64/` 目录含 37 个汇编文件（start.S、clone.S、setjmp.S 等），syscall 编号为 Linux aarch64 ABI。
- 交叉编译仅构建核心静态库目标（`dietlibc.a`/`libm.a`/`libpthread.a`/`librpc.a`/`libcompat.a`/`libcrypt.a`/`liblatin1.a` 及 `start*.o`/`dyn_start.o`/`dyn_stop.o`），跳过 diet/elftrunc/dnsd（这些需宿主机 diet 包装器二次交叉）。
- 打包用 Conan `copy` 手动完成，不用 `make install`（HarmonyOS 无 GNU install 命令，见知识库 E098）。

### 补丁（patches/）
1. `0001-makefile-ar-and-integrated-as.patch`：Makefile 增加 `AR` 变量（HarmonyOS 只有 llvm-ar，无 GNU ar，见 E012）；去掉 `-fno-integrated-as`（HarmonyOS 无 GNU gas，改用 clang 集成汇编器）。
2. `0002-aarch64-type-function-percent.patch`：aarch64 汇编 `.type name, #function` 改 `%function`（clang 集成汇编器兼容，与上游 arm 架构写法一致）。

### 已知风险（真机验证点）
- clang 集成汇编器对 dietlibc aarch64 汇编（`.macro`/`:got:`/`svc` 等）的完整兼容性需真机确认。
- dietlibc 使用 Linux syscall ABI，与 HarmonyOS 内核 syscall 编号的兼容性需真机运行确认。
- 静态链接时 `--rtlib=compiler-rt`（替代上游 Makefile 的 `-lgcc`）的 resource 路径需真机确认。

## 依赖

### 编译依赖
- 无外部库依赖（libc 本体自包含）。仅需 clang + llvm-ar + make。

### 运行依赖
- 无运行依赖（静态库，消费者自行静态链接）。

## 参考

- 官网: https://www.fefe.de/dietlibc/
- 源码: https://deb.debian.org/debian/pool/main/d/dietlibc/dietlibc_0.34~cvs20160606.orig.tar.xz
- Debian 源码页: https://sources.debian.org/src/dietlibc/
