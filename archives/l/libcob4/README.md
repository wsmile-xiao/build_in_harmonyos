# libcob4

`libcob4` 是 [GnuCOBOL](https://www.gnu.org/software/gnucobol/) 的 **COBOL 运行时共享库** `libcob.so.4` 的独立 conan 包：任何由 `cobc` 编译出来的 COBOL 程序在运行期都链接它，它同时对外提供一套稳定的 **libcob C API**（`<libcob.h>`），供 C/C++ 程序直接调用 COBOL 运行时（初始化、字段读写、内存分配、异常与信号处理等）。

之所以有这样一个包：上游把「编译器 `cobc`」与「运行时库 `libcob`」放在同一份 autotools 源码树里交付（见 [../g/gnucobol](../../g/gnucobol/)），但两者许可证不同、消费方也不同 —— 编译器是 GPL，运行库是 LGPL。只想 **运行** COBOL 程序、或只想用 libcob C API 的下游，不应该被拖进一整个编译器。本包就是这条最小依赖路径。

上游 [GnuCOBOL](https://sourceforge.net/projects/gnucobol/)（作者 Keisuke Nishida / Roger While / Simon Sobisch 等，运行库部分 LGPL-3.0-or-later）。

## 包名从哪来

不是一个另外的上游项目 —— 名字直接取自库自己声明的 ABI：

```makefile
# libcob/Makefile.am
libcob_la_LDFLAGS = $(COB_FIX_LIBTOOL) -version-info 6:0:2 -no-undefined
```

libtool 的 `-version-info current:revision:age` 语义为

| 量 | 公式 | 本例（6:0:2） |
|----|------|---------------|
| SONAME | `libcob.so.(current-age)` | `libcob.so.4` |
| 真实文件名 | `libcob.so.(current-age).age.revision` | `libcob.so.4.2.0` |

所以 conan 包名 = `libcob4`，包内只交付这一条 ABI 链。

## 功能概述

- `lib/libcob.so.4.2.0` — 运行时库本体（含 `libcob.so.4` SONAME 链接与 `libcob.so` 链接名）
- `include/libcob.h` — 伞头文件，C API 入口
- `include/libcob/{common,version,cobgetopt}.h`、`include/libcob/{exception,exception-io,statement}.def` — 公共 API 头
- C API 覆盖：运行时初始化/收尾（`cob_init`/`cob_tidy`/`cob_is_initialized`）、内存（`cob_malloc`/`cob_free`）、`cob_field` 与字符串/整数互转、COBOL 固有函数、文件与屏幕 IO、异常与信号、临时文件命名（`cob_temp_name`）等

**不包含**：编译器 `cobc`、运行器 `cobcrun`、`cob-config`、copybook 与配置目录、`CBL_OC_DUMP.so` —— 这些是 [gnucobol](../../g/gnucobol/README.md) 的交付物。需要编译器请依赖 `gnucobol/3.2`。

## 依赖关系

- 编译依赖：`gmp/6.3.0`（GnuCOBOL 的任意精度算术，非可选）
- 运行依赖：无外部共享库（GMP 以静态 PIC 形式链入 libcob）

## OHOS 适配要点

- 源码、SHA256 与 **7 个 OHOS 可移植性补丁**与 `gnucobol/3.2` 逐字相同（含 `0004-libcob-call.c.patch`、`0005-libcob-common.c.patch`）
- 上游测试套件（`tests/testsuite`，1226 用例）经 `cobc` 驱动，所以本包仍走完整 `./configure && make && make check`，**只在 install 阶段收敛**：`make -C libcob install` 只装运行库与 `libcob/` 子目录头文件，顶层伞头 `libcob.h` 由配方手工补
- HarmonyOS 上 `fmemopen` 存在但不可用、临时目录可能是只读挂载或压根不存在：补丁 0004/0005 把 libcob 的临时文件路径改为可用性驱动的回退链（`access(W_OK)` 检查 + 拒绝后回退），`test_package` 对这四类 `TMPDIR` 各起一个进程做断言（libcob 的解析结果是**进程内静态缓存**）
- 构建期 `STRIP=:` 禁止自动 strip：`llvm-strip` 会破坏 HarmonyOS ELF 签名

## 参考资料

- 上游仓库 / 发布：<https://sourceforge.net/projects/gnucobol/>
- 官网：<https://www.gnu.org/software/gnucobol/>
- 编译器与完整工具链包：[gnucobol](../../g/gnucobol/README.md)

## 版本

- `3.2` — 适配 HarmonyOS PC（aarch64-linux-ohos / armv8），零补丁（仅沿用 gnucobol 的同一组上游可移植性补丁）；见 [3.2/notes.md](3.2/notes.md)

## 产物

| 路径 | 说明 |
|------|------|
| `lib/libcob.so.4.2.0` | 运行时库本体（arm64 ELF 共享库） |
| `lib/libcob.so.4` | SONAME 链接（ABI 主版本 4） |
| `lib/libcob.so` | 链接期名字（`-lcob`） |
| `include/libcob.h`、`include/libcob/*.h` | 公开 C API 头文件 |
