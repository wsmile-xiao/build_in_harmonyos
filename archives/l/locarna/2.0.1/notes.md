# locarna 2.0.1 适配笔记

## 编译环境
- 构建系统: autotools（预生成 configure + Makefile.in，上游 release tarball 自带 install-sh）
- 编译日期: 2026-10-09
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，aarch64-unknown-linux-ohos，musl + libc++）
- 目标: HarmonyOS PC / OpenHarmony aarch64（Conan profile `ohos-aarch64`，settings: os=OHOS arch=armv8 compiler=clang libc++ cppstd=17）
- 状态: built

## 编译步骤
1. `conan create archives/l/locarna/2.0.1 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
2. `source()` 取官方 release tarball（sha256 1f50748d…edf7）并 `strip_root=True`；`generate()` 完成 OHOS 环境准备（TMPDIR/AWK、RNAlib2.pc prefix 重写、以及 config.sub/config.guess、configure、lib/Makefile.in 的内容锚定修补，R6）；`build()` 先 `apply_conandata_patches()`（0001 补丁），然后 `./configure` → `make -j1` → `make -j1 check TESTS=test_locarna_lib`，最后 `package()` 用 bundled `config/install-sh` 驱动 `make install`。
3. 关键 configure 参数：`--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu --disable-shared AWK=<gawk>`；`PKG_CONFIG_PATH` 指向重写 prefix 后的 `RNAlib2.pc`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 全部 CLI（locarna/locarna_p/sparse/…）任何调用都 100% CPU 空转、零输出、timeout 124 | `LocARNA/options.cc` 的 `process_options()` 用 `char c` 承接 `getopt_long()` 的 int 返回值；AArch64 下 plain char 默认无符号（AAPCS / `__CHAR_UNSIGNED__`），EOF(-1) 截断为 255，`while ((c = getopt_long(...)) != EOF)` 永不退出 | patches/0001-src-LocARNA-options.cc.patch 把接收变量改为 `int c`（getopt_long 的文档返回类型）。修复后 8 个 C++ 工具全部正常，实测 `locarna a.fa b.fa` 输出 `Score: 2928` 与比对结果 |
| 2 | `configure` 建 `confXXXXXX`（umask 077）在 HMDFS 上不可写；`ac_pwd=\`pwd\`` 在沙箱内 getcwd 失败 | autoconf 硬编码 umask 077 且 `pwd` 依赖 getcwd（E011/E052） | `generate()` 内把 `configure` 中 `umask 077`→`022`，`ac_pwd=\`pwd\`` 追加 `|| ac_pwd="$PWD"` 回退（内容锚定、幂等） |
| 3 | 老版 `config.sub`(2014) 不识别 ohos；configure 收到 ohos 三元组会判定为未知系统 | 上游 config.guess/sub 早于 HarmonyOS | 采用 libuuid 模式：显式传 `--build/--host=aarch64-unknown-linux-gnu`，autotools 永不直接收到 ohos；同时对 config.sub/config.guess 做防御性 HarmonyOS 识别改写（非必需） |
| 4 | viennarna 包内 `RNAlib2.pc` 的 `prefix=/`，OHOS 上解析到宿主 `/lib`，`PKG_CHECK_MODULES([VRNA],[RNAlib2 >= 2.5.1])` 失败 | 上游 .pc 以 `/` 为前缀（DESTDIR staging 遗留） | generate() 把 `prefix=/` 重写为 viennarna 包目录，生成到 `build_folder/vrna-pc` 并 prepend `PKG_CONFIG_PATH` |
| 5 | `make install` 在 pkginclude 多文件头批次上报宿主 install shim `Error 64` | OHOS 宿主 install 包装器限制 | 用上游 bundled `config/install-sh`（经 `/bin/sh`）作为 `INSTALL`/`MKDIR_P` 驱动 `make install DESTDIR=…` |
| 6 | `lib/perl` 子目录构建/安装 MLocarna.pm 失败 | MLocarna.pm → MLocarna::threaded → `use threads`；OHOS PC 镜像自带 Perl 未编译线程支持（`This Perl not built to support threads`） | 禁用 `lib/perl`（`lib/Makefile.in` 的 `SUBDIRS = perl` → `SUBDIRS =`）；Perl 前端脚本属独立交付物 |
| 7 | 上游 `test_programs` 集成驱动（bash/perl）在 OHOS 跑不了（无 /bin/bash、需 Perl 模块） | 集成驱动非自包含 | `make check` 命令行覆盖 `TESTS=test_locarna_lib`，仅跑 Catch2 单元套件（22 用例 / 175 断言） |
| 8 | conan 应用补丁报 `source/target file does not exist: a/LocARNA/options.cc` | 补丁路径前缀写错：tarball 根下是 `src/LocARNA/options.cc`，而 Conan `patch()` 以 `strip=0`、root=source_folder 解析 | 补丁头改为 `a/src/LocARNA/options.cc` / `b/src/...` |

## 源码修改

`patches/0001-src-LocARNA-options.cc.patch`：`src/LocARNA/options.cc` 中 `process_options()` 的 `char c;` → `int c;`（附行内根因注释）。

该补丁由 `ohc-run.py refresh-patch --auto` 生成（`patch_generation.method=per-file-difflib`，基线
`/data/storage/el2/base/cache/builds/locarna-2.0.1.{orig,work}`，orig/work hash 见 manifest.yaml），
非手工创建；`patch_classification` 标为 `type: portability / platform_only: false / guard: none`
（`int` 是 `getopt_long` 的文档返回类型，各平台皆正确，无需 `__OHOS__` 守卫）。

其余为**构建期内容锚定修补，不改变交付源码语义、不入补丁**：`configure` 的 umask 077→022 与
ac_pwd 回退、`lib/Makefile.in` 的 `SUBDIRS = perl` → `SUBDIRS =`、`config/config.sub`+`config.guess`
的 HarmonyOS 识别。按 R6，这些改写全部在 `generate()` 内完成（源码已就绪、build() 内不再改写生成文件）。

## 依赖版本
- viennarna/2.7.2（硬依赖：`RNAlib2 >= 2.5.1`，经 pkg-config 探测）
- check/0.15.2（传递依赖，Conan 解析所得）
- 系统库：libc.so（musl）、libc++_shared.so（SDK 提供）

## 验证结果

```bash
# 8 个 C++ CLI 全部可运行（修复前全部 timeout 124 / 零输出）
# 下列 8 条 --version 输出为手工实测记录；W3 本地 CI 的 L2 对同一批二进制
# 逐条记录为 "[ok] <tool> --version OK"（完整输出仅 locarna 一条被日志捕获）。
$ for b in locarna locarna_p exparna_p sparse locarna_deviation locarnap_fit locarna_rnafold_pp ribosum2cc; do ./$b --version; done
LocARNA 2.0.1
locarna_p (LocARNA 2.0.1)
exparna_p (LocARNA 2.0.1)
sparse (LocARNA 2.0.1)
locarna_deviation (LocARNA 2.0.1)
locarnap_fit (LocARNA 2.0.1)
locarna_rnafold_pp (LocARNA 2.0.1)
ribosum2cc (LocARNA 2.0.1)

# 真实端到端比对（test_package._cli_smoke 亦执行同一断言）
$ locarna a.fa b.fa
Score: 2928

a                  GGGGAAAACCCCUUUU
b                  GGGGAAAACCCCUUUU

# 上游单元套件（build() 内 make check）
HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"catch2","command":"make check (test_locarna_lib)","discovered":22,"executed":22,"passed":22,"failed":0,"skipped":0,"assertions":175}

# 门禁
conan-verify G0/G1/G2/G3/G4（verdict=pass，见 reports/conan-verify-report.md）
W3 本地 CI：L0/L1/L2/L4/L5 全 pass，pass rate 100%（见 .ci-result.json / reports/w3-local-ci.log）
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libLocARNA-2.0.a | 静态库（**不内嵌** ViennaRNA：保留 8 个未定义 `vrna_*` 符号，消费端须链 viennarna 的 libRNA） |
| include/LocARNA-2.0/LocARNA/*.hh | C++ 头（`#include <LocARNA/sequence.hh>` 需 include + include/LocARNA-2.0 双根） |
| lib/pkgconfig/LocARNA-2.0.pc | prefix 已重写为包目录；并剔除指向 viennarna Conan 缓存目录与 `~/usr/local` 的绝对 `-L`/`-I`（换机后可移植） |
| bin/{locarna,locarna_p,exparna_p,sparse,locarna_deviation,locarnap_fit,locarna_rnafold_pp,ribosum2cc} | 8 个原生 C++ 工具 |

## 注意事项
- **AArch64 plain char 默认无符号**是本包（以及任何用 `char` 承接 getopt/getc 返回值的老代码）在 OHOS 上最隐蔽的坑：症状是 100% CPU 空转 + 零输出 + timeout 124，不会给出任何报错。定位手段：`ITIMER_PROF` + `SIGPROF` 采样 PC（`ucontext_t.uc_mcontext.pc`）后 `llvm-addr2line` 反查——OHOS 沙箱禁用 ptrace，gdb/lldb 均不可用。
- **Perl 前端（mlocarna/locarnate 等）**在 OHOS 上不可用：镜像 Perl 无线程支持。这些脚本已从包内 bin/ 剔除（只保留 ELF 工具），避免交付“存在但无法执行”的可执行文件并拖慢 L2 bin/ smoke 矩阵。
- 库消费端 include 路径需双根：`include` + `include/LocARNA-2.0`；API 访问为 `s.seqentry(0).name()`（`std::string`）与 `s.seqentry(0).seq().str()`（`string1` 无隐式转换到 `std::string`）。
- **交付 .pc 不含构建机绝对路径**：上游 `.pc.in` 把 configure 期的 `@LIBS@`/`@CPPFLAGS@` 原样落盘，其中含 viennarna 的 Conan 缓存目录与共享 `~/usr/local` 前缀；`package()` 在重写 `prefix` 之外还删除所有不落在包目录内的绝对 `-L`/`-I` 词元（`_strip_foreign_pc_flags`，含 `.private` 变体与 `-L /path` 空格形式），否则制品换机/入制品仓后 pkg-config 会给出失效路径（E524）。`prefix` 同时改为可重定位的 `${pcfiledir}/../..`，并补上游缺失的 `Requires: RNAlib2`——静态库保留 8 个未定义 `vrna_*` 符号、5 个已安装公共头 include `<ViennaRNA/...>`，ViennaRNA 是公共依赖（此前 `Libs:` 里的 `-lRNA` 没有对应搜索路径，直接 `pkg-config --libs` 的消费者链不上）。
- **R6 落点**：对预生成 autotools 文件（`config.sub`/`config.guess`/`configure`/`lib/Makefile.in`）的改写全部在 `generate()` 内，`build()` 只做 `apply_conandata_patches()` 与编译/测试。
---

**编译结束**: 2026-10-10 00:50
**最终状态**: built
