# libgig 4.5.2 适配笔记

## 编译环境
- 构建系统: autotools（configure + make + libtool）
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4 / clang++（`aarch64-unknown-linux-ohos`，stdlib=libc++，C++17）
- 状态: built（G2/W3 通过后由 finish 更新）

## 交付面（实测 `make install` 清单，非推测）

```
bin/            14 个 CLI：rifftree dlsdump gigdump gigextract gigmerge gig2mono
                gig2stereo sf2dump sf2extract korgdump korg2gig akaidump
                akaiextract wav2gig
include/libgig/ RIFF.h DLS.h SF.h gig.h Korg.h Serialization.h sysdef.h Akai.h
lib/libgig/     libgig.a libakai.a（上游 pkglib_LTLIBRARIES，**不在 lib/ 顶层**）
lib/pkgconfig/  gig.pc akai.pc
share/man/man1/ 14 个工具的 man page
```

`bin/` 非空 ⇒ 软件级 `commands.json`（R38/L0k）；库落在 `$(libdir)/libgig/` ⇒
`cpp_info.libdirs` 必须含 `lib/libgig`，否则消费者链接期找不到 `-lgig`。

## 编译步骤

```sh
# 依赖（configure.ac 的硬依赖，缺任一直接 exit -1）
#   PKG_CHECK_MODULES(SNDFILE, sndfile >= 1.0.2)   → libsndfile/1.2.2
#   AC_CHECK_FUNCS(uuid_generate)                  → libuuid/2.42.2
conan create . -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<同一 profile>
# 配方内：PkgConfigDeps（sndfile.pc）+ 依赖头/库目录注入 CXXFLAGS/LDFLAGS（uuid 不走 pkg-config）
#         --enable-static --disable-shared；build() 内跑 make check 与 4 个测试程序
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | shared 构建下 14 个工具 `RUNPATH=//lib/libgig`，裸环境 `Error loading shared library libgig.so.13` | libtool 按安装期前缀（`--prefix=/` + `pkglibdir=$(libdir)/$(PACKAGE)`）写绝对 RUNPATH | 改静态（`--enable-static --disable-shared`），工具自包含，从结构上消除该面 |
| 2 | 静态构建下 `serializationtests` 在 `main()` 之前 SIGSEGV（rc=139，输出 0 字节） | **静态初始化顺序缺陷**：消费者 TU 的全局 `NativeDataTypeRegistry<>` 构造器先于库内 `static std::map DataType::m_nativeTypes` 的动态初始化运行 | 补丁 0002/0003：把该静态数据成员改为**函数内 static 访问器**（首次使用即构造），删掉类外定义；修复后 4 套测试全绿 |
| 3 | 14 个工具 `--version`/`--help` 全部非 0（`Unknown option` 或 `fopen` 失败） | 上游只实现短选项 `-v`；L2 smoke 探针用 `--version/--help/-V/-h` | 补丁 0004–0017（按 E503 / libubox jshn 先例）：`main()` 开头拦截 `--version`（同 `-v` 语义）与 `--help`（同 usage 语义）并 `return 0` |
| 4 | `configure` 在 HMDFS 上 `mktemp -d` 建出的 0700 临时目录不可写 | configure 内 `umask 077`（E011） | 配方 `build()` 内联 `sed` 把 `umask 077` 改 `umask 022`（libuuid/libbfio 家族同口径，不改生成文件以外的语义） |
| 5 | conan 的 `conan create` 下 `configure` 报 `config.guess: unable to guess system type`（`uname -s = HarmonyOS`），并在 `$TMPDIR/confXXXXXX/dummy.c` 报 `Permission denied` | `config.guess`（2024-07-27）无 HarmonyOS 分支；conan 的 AutotoolsToolchain 未传 `--host/--build`，于是 configure 走 `config.guess` 的探测路径（第 1613 行还会用 `umask 077 && mktemp -d` 建 0700 目录，在 HMDFS 上不可写） | 补丁 0001：加 `*:HarmonyOS:*:*` 分支直接输出 `aarch64-unknown-linux-ohos` 并 `exit`，短路探测路径（E007；手工原生构建时我显式传了 `--host/--build` 才没暴露） |
| 6 | `test_package` 编译报 `fatal error: 'RIFF.h' file not found` | 上游 `libgigincludedir = $(includedir)/libgig`，头文件装在 **`include/libgig/` 子目录**；`cpp_info.includedirs` 只给了默认的 `include` | `self.cpp_info.includedirs = ["include", "include/libgig"]`（两个都给出：`include/libgig` 供 `#include <gig.h>`，`include` 供 `#include <libgig/gig.h>`） |
| 7 | 包内 `gig.pc`/`akai.pc` 写成 `prefix=/`、`libdir=/lib/libgig`、`includedir=/include/libgig` | Conan 以 `--prefix=/` 配置 + `DESTDIR=<package_folder>` 安装，上游 `*.pc.in` 的 `@prefix@` 因此展开成 `/`（libart-lgpl 家族同型缺陷） | `package()` 内按四个键逐行重写为实际包目录（`_fix_pkgconfig_prefix()`），非 conan 消费者按 .pc 取到的才是包路径 |
| 8 | `AC_SEARCH_LIBS(uuid_generate, uuid)` 找不到 libuuid | 上游对 uuid 不用 pkg-config，仅靠 `PKG_CONFIG_PATH` 不够 | `generate()` 里把 `libuuid` 的 include/lib 目录注入 `tc.extra_cxxflags`/`tc.extra_ldflags` |

## 源码修改

`patches/` 共 17 个补丁，由 `refresh-patch --auto` 按被改源文件逐文件生成（三组）：

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001 | `config.guess` | E007：增加 `*:HarmonyOS:*:*` 分支，输出 `aarch64-unknown-linux-ohos`（见问题 5） |
| 0002 / 0003 | `src/Serialization.cpp` / `src/Serialization.h` | 静态初始化顺序修复（函数内 static 访问器） |
| 0004–0017 | `src/tools/{akaidump,akaiextract,dlsdump,gig2mono,gig2stereo,gigdump,gigextract,gigmerge,korg2gig,korgdump,rifftree,sf2dump,sf2extract,wav2gig}.cpp` | `main()` 开头 GNU 长选项 `--version`/`--help`，`return 0` |

补丁内**无任何平台宏**（PF5 口径；`patch_type: portability`）。补丁全部经
`patch -p1` 对 pristine 解压树 dry-run 通过，顺序应用后与编辑树**逐字节一致**（`diff -rq` 无差异）。

## 依赖版本

- `libsndfile/1.2.2`（静态；供 gigextract/sf2extract/akaiextract/wav2gig 写音频文件）
- `libuuid/2.42.2`（静态；DLSID/gig UUID 生成）
- 传递闭包：两个依赖配方均无 `requires()`，故 W0 检查条数 = 2。

## 验证结果

```sh
# 上游测试（沙箱 HOME=$TASK_DIR/test-home）：4 个测试程序，合计 406 条断言
helpertests        OK (90 tests)
serializationtests OK (104 checks)
rifftests          OK (84 checks)
gigtests           OK (128 checks)

# 工具裸环境 smoke（unset LD_LIBRARY_PATH）
./gigdump --version  → "gigdump revision 4245 / using libgig 4.5.2"，rc=0
./rifftree --help    → usage，rc=0     （14/14 工具 rc=0）

# W3 采信轮 / conan create / test_package 证据见 reports/
```

## 注意事项

- **必须真跑上游测试**：静态链接下 `make` 全绿而 `make check` 崩（问题 2），只看编译通过会漏。
- **裸环境 smoke 不可省**：`conanrun` 的 `LD_LIBRARY_PATH` 会掩盖 RUNPATH 错误；
  本包的库在 `lib/libgig/`，`conan-verify` L2 注入的 `cache/lib` 覆盖不到它，
  工具会走「loader 缺库 → SKIP」分支，**SKIP ≠ 可用**。
- 库产物不在 `lib/` 顶层（`pkglibdir`），G4 的 `lib/*.a|*.so` 顶层扫描为空属正常。
- 上游 `make check` 的 4 个测试程序会在 `src/testcases/` 写 `a.riff`/`b.riff`/`foo.gig` 等中间文件，
  不写 HOME；仍以 `HOME=$TASK_DIR/test-home` 沙箱运行。
