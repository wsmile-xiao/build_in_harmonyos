# DRAFT-cqrlib-1.1.4-libtool-makefile-direct-compile

> Contributor: 2301_76770579 | Status: Draft | Updated: 2026-09-09
> Source: cqrlib 1.1.4 HarmonyOS PC 适配（无构建系统小库，从零写配方）

## 现象

cqrlib 1.1.4（yayahjb/CQRlib，四元数/旋转 C 库）没有 CMake/autotools，只有一份
2009 年起的手写 Makefile，且：

1. **硬依赖 libtool**（`COMPILE_COMMAND = $(LIBTOOL) --mode=compile ...`，无
   libtool 环境直接不可用）；
2. **安装目录默认 `$HOME`**（`INSTALLDIR = $(HOME)`），install 目标还会在装完后
   现场编译 4 个 dynamic/static 测试并 diff——沙箱/打包流程全不接受；
3. `make tests` 的判据是运行 `CQRlibTest`/`CPPQRTest` 后 `diff -b -c` 对比
   `*_orig.lst`，但 **GitHub tarball 里两个 `*_orig.lst` 都是 0 字节占位文件**
   → diff 判据形式上存在、实际不可用。

## 根因

- 该库是"单 .c + 单 .h"级别的微型库，上游从未引入标准构建系统；Makefile 面向
  作者本机（Mac,libtool 在 `$HOME/bin`）而非可复现打包。
- 期望输出文件在上游仓库本来就是空占位（作者本地跑完才生成真实 lst 自用），
  因此 **真正的测试判据其实是程序自检返回值**：`CQRlibTest.c` main 返回
  `errorcount`（每处数值不符递增），`exit 0` 即全过。

## 解决方案（配方侧，不动上游源）

1. **绕过 libtool Makefile，配方内直接编译**：`cc -O2 -fPIC -c cqrlib.c` →
   `ar rcs libCQRlib.a`（或 `-shared`），编译器从 conan conf
   `tools.build:compiler_executables` 取，不裸用 `$CC`。
2. **测试改走 exit 自检**：build() 内编译上游 `CQRlibTest.c`（链静态库 +`-lm`）
   与 `CPPQRTest.cpp`（**按上游 Makefile 语义不链库**——它测的是 cqrlib.h 里
   `#ifdef __cplusplus` 的 header-only C++ 模板），直接运行，非零即失败；
   body/MANIFEST 如实写明"diff 判据因上游 .lst 空占位不可用，以程序自检为准"。
3. 打包只取 `cqrlib.h` + `libCQRlib.{a,so}`，`cpp_info.libs=["CQRlib"]`、
   `system_libs=["m"]`（库名大小写敏感，沿用上游）。

## 禁止策略

- 不得声称跑了 `make tests` 的 diff 判据（.lst 空占位，diff 必然失败或无意义）。
- 不得给 CPPQRTest 链 libCQRlib——上游设计就是验证纯头文件模板路径。
- 不得在上游 Makefile 上打补丁硬改 INSTALLDIR/libtool 路径硬跑——直接编译更稳。

## 适用范围

任何"单/少源文件 + 手写 libtool/plain Makefile + 无标准构建系统"的小 C 库
（尤其 2000s 学术代码：crystallography/数值/工具类）迁 OHOS 均可复用此模式：
配方内直接编译 + 上游自检测试 exit 判据 + 诚实标注上游判据不可用原因。
