# ML GMP (Objective Caml interface to GNU MP / MPFR)

## 简介
ML GMP 是 GNU MP（GMP，任意精度算术库）与 MPFR（多精度浮点库）的
Objective Caml（OCaml）绑定。提供整数 `Z`、有理数 `Q`、GMP 浮点 `F`、
MPFR 浮点 `FR` 四个 OCaml 模块。

## 基本信息
- 上游: Debian 源 mlgmp_20021123（David Monniaux, 2001-2002）
- 源码: https://deb.debian.org/debian/pool/main/m/mlgmp/mlgmp_20021123.orig.tar.gz
- 许可证: LGPL-2.1
- 构建系统: makefile（GNU Make，无 configure）

## 已编译版本
- 20021123 (2026-09-30) —— built（本地 conan create 验证通过，待 CI release 流水线 upload 后更新为 published），OCaml 4.14.4 + GMP 6.3.0 + MPFR 4.2.2.1

## 依赖
- ocaml/4.14.4（工具链 + 运行时）
- gmp/6.3.0
- mpfr/4.2.2.1

## OHOS 适配要点
- 产物是 OCaml 库（gmp.cma/gmp.cmxa/gmp.a/gmp.cmi/gmp.mli）与 C 存根
  （libmlgmp.a 静态 + dllmlgmp.so 共享），非 C 可执行/系统同名库。
- 字节码可执行（`ocamlc -custom` 内嵌运行时的 ELF）在 OHOS 上无法直接执行
  （EPERM，未签名 ELF 限制），下游一律经 `ocamlrun` + `dllmlgmp.so` 运行。
- OCaml 4.14 兼容：序列化函数类型 int32→int32_t/intnat；String→Bytes API；
  MPFR 4.x 移除 mpfr_random/mpfr_random2，改用 mpfr_urandomb。

## 使用方式
```bash
# OCaml 原生链接
ocamlopt -I <prefix>/lib/ocaml/gmp gmp.cmxa your_prog.ml -o your_prog

# OCaml 字节码链接（需要 dllmlgmp.so）
ocamlc -dllib dllmlgmp.so -I <prefix>/lib/ocaml/gmp gmp.cma your_prog.ml -o your_prog
CAML_LD_LIBRARY_PATH=<prefix>/lib/ocaml/gmp ocamlrun ./your_prog
```
