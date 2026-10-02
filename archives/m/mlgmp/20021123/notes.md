# mlgmp 20021123 适配笔记

## 编译环境
- 构建系统: makefile（GNU Make，非 autotools；上游无 configure 脚本）
- 编译日期: 2026-09-30
- 编译器: clang 15.0.4 (OHOS /data/service/hnp/bin/clang)
- 平台: OHOS/aarch64 (os=OHOS, arch=armv8, libc++)
- 状态: built（本地 conan create 验证通过，待 CI release 流水线 upload 后更新为 published）

## 编译步骤

mlgmp 是 GNU MP (GMP) / MPFR 的 Objective Caml (OCaml) 绑定库，输出 OCaml 库
(gmp.cma/gmp.cmxa/gmp.a) 和 C 存根静态库 libmlgmp.a。上游为纯 Makefile 项目，
无 configure。

1. 依赖安装（conan 制品仓预编译包）：
   - ocaml/4.14.4（含 ocamlc/ocamlopt/ocamlmktop/ocamldep）
   - gmp/6.3.0（libgmp.a + gmp.h）
   - mpfr/4.2.2.1（libmpfr.a + mpfr.h）
   - 通过 `conan install` 拉取到本地 cache，源码编译时用
     `GMP_PREFIX`/`MPFR_PREFIX`/`OCAMLLIB` 指向对应包路径。
2. 生成依赖文件：`ocamldep *.ml *.mli > depend`（上游 tarball 缺 depend，Makefile
   `include depend` 需要）。
3. 修改 Makefile：
   - GMP/MPFR 路径改为 `$(GMP_PREFIX)`/`$(MPFR_PREFIX)` 变量（可用环境变量覆盖）
   - `CC ?= clang`，CFLAGS 增加 `-fPIC -fcommon`
   - `RLIBFLAGS` 置空（gmp/mpfr 静态链接，无需 rpath）
   - 字节码测试 `test_suite` 改用 `-dllib dllmlgmp.so` + ocamlrun 运行
     （-custom ELF 在 OHOS 上 EPERM 无法直接执行，见问题表）
   - 新增 `dllmlgmp.so` 共享存根库规则（字节码运行时查找 C 原语）
4. 编译：`make -j1`
5. 测试：`make tests`（等价上游 `make check`）
6. 安装：`make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.h 用 `int32`/`uint32` 类型 | OCaml 4.14 无裸 `int32`/`uint32` 类型（改用 `int32_t`/`uint32_t`，序列化函数签名 `intnat`） | config.h 声明改为 `int32_t`/`uint32_t`/`intnat` |
| 2 | gmp.ml `String.create`/`String.set` 报错 | OCaml 4.14 中 `String.create`/`String.set` 返回 `bytes` 类型，不能当 `string` 用 | 改用 `Bytes.create`/`Bytes.blit_string`/`Bytes.set`/`Bytes.to_string`（2 处） |
| 3 | 链接重复符号 `_mlgmp_custom_*` | 各 .c 文件均 `#include "conversions.c"`，含非初始化全局定义；LLVM/clang 15 默认 `-fno-common` 不再合并 common symbol | CFLAGS 加 `-fcommon` |
| 4 | `mpfr_random`/`mpfr_random2` undefined | MPFR 4.x 移除这两个 API | 改用 `mpfr_urandomb` + 静态 `gmp_randinit_default` 状态重实现 |
| 5 | 字节码可执行文件 `-custom` 无法直接运行 (EPERM) | OHOS 对嵌运行时 ELF（未签名）直接执行限制（E046/E051 类） | 构建 `dllmlgmp.so` 共享存根库，字节码测试用 `ocamlrun` + `CAML_LD_LIBRARY_PATH` 运行 |
| 6 | 上游 tarball 缺 `depend` 文件 | Makefile `include depend` | 编译前 `ocamldep *.ml *.mli > depend` |
| 7 | 依赖版本冲突 gmp/6.3.0 vs 6.3.0.1 | mpfr/4.2.2.1 依赖 gmp/6.3.0 | 采用 gmp/6.3.0（不引入 6.3.0.1） |
| 8 | 64 位平台 Int_val 截断核心 API 静默算错 | OCaml 4.14 `Int_val` = `(int) Long_val` 强转 32 位；OHOS/aarch64 是 64 位，`Z.of_int (1 lsl 40)` 等 ≥2^31 实参被截断为 0（Debian bug #573978，上游 `mlgmp_z.c` 有 29 处、`conversions.c` 4 处） | 新增 `0005-mlgmp-z-long-val.patch`：`mlgmp_z.c` 数值实参 `Int_val`→`Long_val`（25 处）；`Int_val(base)`×3、`mpz_probab_prime_p(reps)` 等 GMP 本就要求 `int` 的场合保留。`conversions.c` 的 4 处（prec×2、mp_rnd_t、未用 Int_option_val）保留。test_package 增加大整数回归断言（native+bytecode 双路径） |

## 源码修改

- config.h: 序列化函数声明类型修正 (int32→int32_t 等)
- gmp.ml: String→Bytes 序列化格式化（2 处）
- mlgmp_fr.c: mpfr_random/mpfr_random2 用 mpfr_urandomb 重实现
- Makefile: 路径变量化 / clang / -fcommon / 字节码测试运行方式 / dllmlgmp.so 规则

## 依赖版本

- ocaml/4.14.4
- gmp/6.3.0
- mpfr/4.2.2.1

## 验证结果

```bash
make -j1 tests   # 全部通过（75 断言 × 字节码/原生 两变体）
# 原生: ./test_suite.opt exit=0
# 字节码: ocamlrun ./test_suite exit=0
# 外部 smoke test: ocamlopt/ocamlc 链接 gmp.cma/gmp.cmxa 均通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| gmp.cma | OCaml 字节码库 |
| gmp.cmxa / gmp.a | OCaml 原生库 + 原生代码归档 |
| gmp.cmi / gmp.mli | 接口 |
| libmlgmp.a | C 存根静态库 |
| dllmlgmp.so | C 存根共享库（字节码运行时用） |

## 注意事项

- 库类型包（无 CLI 可执行产物），不需要 commands.json (R38)
- 字节码可执行（-custom ELF）在 OHOS 无法直接运行，测试/运行一律走 ocamlrun
- ocaml/4.14.4 预编译包 `ocamlc -where` 指向陈旧路径，需设 `OCAMLLIB` 指向实际
  lib/ocaml
---

**编译结束**: 2026-09-30 13:29
**最终状态**: built
