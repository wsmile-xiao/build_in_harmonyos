# kaldi g20231112 适配笔记（HarmonyOS PC / aarch64）

## 版本与源码

- 上游：https://github.com/kaldi-asr/kaldi （官方仓库，无 release tag）
- 快照：`e8ed6107cb8880fb2b9a2b7dea2f5889962b614b`（2023-11-10，2023-11-12 当日 HEAD），
  版本号按仓库 git 快照惯例记为 `g20231112`
- 源码包 sha256：`a6f29f01e801d62324c2e7cbc95aa905a3ba8f7c00e23e4cd5f264a5df9b1271`

## 定位与范围

kaldi 本体是 C++ 库（`src/*/kaldi-*.a`）+ 一大批命令行工具（`src/*bin/`）。本配方**只打包静态库与头文件**：

- 消费方（vosk-api 的 `libvosk.so`）只链接 `kaldi-online2/decoder/...` 等静态库；
- `src/*bin/` 每个可执行文件都静态链入整套 kaldi（单个 3~8 MB，全量约 GB 级），且运行时需要
  语音模型数据，不适合作为制品仓包内容；
- 因此本包 `package_type=static-library`，不声明 commands.json。

上游 `tools/` 需要自行下载并编译 OpenBLAS/OpenFST/CLAPACK。本配方不碰 `tools/`，而是复用
制品仓中已适配的 `openfst/1.8.4` 与 `openblas/0.3.34`（OpenBLAS 同时提供 LAPACK），
通过 `--openblas-root` / `--fst-root` 指向其 `package_folder`。

## 依赖

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| openfst | 1.8.4 | 静态库 | `--fst-root`，`--static-fst`（制品仓的 openfst 只出 libfst.a） |
| openblas | 0.3.34 | 动态库 | `--mathlib=OPENBLAS`，同时提供 BLAS + LAPACK + cblas.h/lapacke.h |

kaldi 自身不使用 OpenFST ngram 扩展，故不依赖 `libfstngram`（vosk-api 才用）。

## 构建

```
src/configure --use-cuda=no --mathlib=OPENBLAS \
  --openblas-root=<openblas> --fst-root=<openfst> --static-fst --fst-version=1.8.4
make -j<JOBS> SHELL=<bash> EXTRA_CXXFLAGS="-std=c++17 -fPIC" libs
make -j<JOBS> SHELL=<bash> EXTRA_CXXFLAGS="-std=c++17 -fPIC" test   # 上游测试
```

- `-std=c++17`：OpenFst 1.8.4 头文件（`fst/lock.h` 用 `std::shared_mutex` 等）要求 C++17；
  kaldi 的 `makefiles/linux_openblas_aarch64.mk` 写死 `-std=c++14`，用 `EXTRA_CXXFLAGS`
  （在 `CXXFLAGS` 中排在 `-std=c++14` 之后）覆盖。
- `-fPIC`：静态库要被消费方链进 `.so`（libvosk.so）；上游静态构建默认不加 `-fPIC`。
- 上游 kaldi 默认构建 = `libs + *bin`；本配方用 `make libs` 只编库。

## 平台适配（patches/0001）

| 问题 | 现象 | 修复 |
|------|------|------|
| 平台探测 | `src/configure` 用 `` `uname` `` 判 OS，OHOS 返回 `HarmonyOS` → `Could not detect the platform` | Linux/FreeBSD 分支加入 `HarmonyOS` |
| 解释器 | `src/configure` shebang `#!/bin/bash`，OHOS 无 `/bin/bash`（`checkversion` 目标会 `./configure --version`）| 改为 `#!/usr/bin/env bash` |
| Makefile SHELL | `src/Makefile` / `makefiles/default_rules.mk` 写死 `SHELL := /bin/bash`，configure 内部的 expf 探针 make 直接失败 → 误判 `KALDI_NO_EXPF` | 改为 `$(shell command -v bash 2>/dev/null || echo /bin/bash)` |
| 临时目录 | `src/base/get_version.sh` 用 `mktemp /tmp/temp.XXXXXX`，OHOS `/tmp` 只读（E002）→ 版本脚本非零退出 → `base/Makefile` `$(error)` | 改用 `"${TMPDIR:-/tmp}/temp.XXXXXX"` |
| 链接参数 | OPENBLAS 分支追加 `-lgfortran`，OHOS 无 gfortran 运行库（OpenBLAS 包也无） | 去掉 `-lgfortran` |

## OpenFst 1.8 API 迁移（patches/0002）

制品仓只有 openfst 1.8.4，而 kaldi g20231112 面向 OpenFst 1.7.x。逐项：

| OpenFst 1.7 | OpenFst 1.8.4 | 涉及 |
|-------------|---------------|------|
| `<fst/types.h>`（全局 int8..uint64） | 头文件已移除 | `base/kaldi-types.h` 改从 `<cstdint>` 复刻全局别名 |
| `FLAGS_fst_weight_separator` / `FLAGS_fst_field_separator` / `FLAGS_v` | `FST_FLAGS_*` | `fstext/kaldi-fst-io-inl.h`、`fstext/lattice-weight.h`、`lat/kaldi-lattice.cc`、`lat/lattice-functions-transition-model.cc` |
| `MapFst` / `MapFstOptions` | `ArcMapFst` / `ArcMapFstOptions` | `fstext/lattice-utils-inl.h`、`latbin/lattice-compose.cc`、`latbin/lattice-lmrescore.cc` |
| 自由函数 `Map()` | `ArcMap()` | `fstext/fstext-utils.h`、`fstext/fstext-utils-inl.h`、`fstext/*-test.cc`、`kws/*`、`kwsbin/*`、`latbin/lattice-oracle.cc`、`chain/chain-den-graph.cc` |
| `FstPrinter::Print(std::ostream*, ...)` | `Print(std::ostream&, std::string_view)` | `lat/kaldi-lattice.cc`、`bin/phones-to-prons.cc`、`decoder/lattice-biglm-faster-decoder.h`、各 `*-test.cc` |
| `FloatWeightTpl::GetPrecisionString()` 返回 `const std::string&` | 返回 `std::string_view` | `lat/arctic-weight.h`（`std::string + string_view` 无法编译） |
| `MatcherBase::Properties(uint64)` | `Properties(uint64_t)` | `fstext/table-matcher.h`（否则 override 不成立，TableMatcher 不能当 MatcherBase 用） |
| `StateIteratorData::base`（裸指针） | `std::unique_ptr` | `fstext/trivial-factor-weight.h`（`data->base.reset(...)`） |
| `CompactFst::WriteFst()` 静态成员 | 已移除（保留 `Write()` 实例方法） | `chain/chain-supervision.cc` 改为构造 `StdCompactAcceptorFst` 后 `Write(os, opts)` |

## OpenBLAS / LAPACK 头文件兼容（patches/0003）

OpenBLAS 0.3.34 自带的 `lapack.h`（LAPACK >= 3.10）定义 `LAPACK_FORTRAN_STRLEN_END`，
把 Fortran 入口声明带上了隐藏的字符串长度参数（如 `stptri_` 由 5 参变 7 参）；
而 `matrix/cblas-wrappers.h` 的 CLAPACK 风格调用是 5 参（`stptri_(char*, char*, int*, float*, int*)`），
于是 `no matching function for call to 'stptri_'`。

修复：`matrix/kaldi-blas.h` 的 `HAVE_OPENBLAS` 分支不再 `#include "lapacke.h"`，
改为包含 kaldi 自带 `tools/CLAPACK/f2c.h` + `tools/CLAPACK/clapack.h`
（同一例程 ABI、纯指针参数，与 cblas-wrappers.h 的调用一致）。

## 上游测试

- 上游**没有**顶层 `make check` / `ctest` / `pytest`。真实入口是 `make -C src test`
  （`src/Makefile`: `test: $(addsuffix /test, $(SUBDIRS_LIB))`；`src/makefiles/default_rules.mk`:
  `test: test_compile`，编译并运行各库目录下的 `*-test` 程序）。
- 本配方在 `build()` 内执行 `make libs` 后继续 `make test`，把上游测试作为构建门禁。
- 实测结果见 `reports/test-report.md`（123 个测试程序全部 SUCCESS）。

## 鸿蒙特有测试

`test_package/test_ohos_kaldi.sh`：校验产物确为 HarmonyOS/aarch64 原生
（`uname` = HarmonyOS、21 个 `kaldi-*.a` 为非空 ar 归档、归档成员为 AArch64 ELF、
公共头文件齐全），并把 kaldi 静态库链成的共享库在真机上 `dlopen` 调用
（验证 `-fPIC` 与 musl 加载器下的符号解析）。

## 已知限制

- 只发布静态库（不发布 `src/*bin/` CLI 工具），理由见上“定位与范围”。
- `--shared` 不支持：kaldi 的动态库分支依赖 `uname == Linux`（`makefiles/default_rules.mk`、
  `src/Makefile` 的 biglib），且制品仓 openfst 也是静态库。
---

**编译结束**: 2026-09-26 01:33
**最终状态**: built
