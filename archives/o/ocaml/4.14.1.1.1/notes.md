# ocaml 4.14.1.1 适配笔记

**日期**: 2026-07-31
**状态**: ✅ built（conan create RC=0，test_package 通过）
**最终状态**: built

## 概述

OCaml 4.14.1（函数式语言编译器 + 运行时）完整自举构建到 HarmonyOS aarch64。
构建系统为 OCaml 自研 configure（autoconf 风格） + make 自举（无 dune 参与本体构建）。

## 构建链路

```
configure --no-create → config.status → make world.opt → make install(DESTDIR) → test_package
```

产物：ocamlc/ocamlopt（byte/native）、ocamlrun、stdlib.cma/.cmxa、ocaml 顶层、ocamldoc 等。

## 关键适配点（均为真机实测验证）

### 1. OHOS hmmac 拒绝直接执行 shebang 脚本（EACCES/126）
- 现象：`./configure`、`./gen_primitives.sh`、`./Compflags`、`./generate_runtimedef.sh`
  均报 `Permission denied`（126），无论 shebang 指向 `/bin/sh` 还是 `/data/service/hnp/bin/bash`
- E165 知识条目建议的「改 shebang 路径」**在本真机不适用**（bash shebang 同样被拒）
- 正确方案：**显式解释器调用** `/bin/sh script`
- 落点：conanfile.py build() 中 configure/config.status 显式 `/bin/sh`；
  Makefile 内 `$(shell ./xxx)` 改为 `$(shell /bin/sh ./xxx)`

### 2. OHOS 拒绝创建符号链接（ln -sf → Permission denied）
- 现象：`cd boot; ln -sf ../runtime/libcamlrun.a .`、install 阶段 `ln -sf xxx.opt xxx` 均失败
- 方案：根 Makefile `LN = ln -sf` → `LN = cp -f`；tools/Makefile `LN := ln -sf` → `LN := cp -pf`
  （上游 win32 分支本就使用 cp，语义对齐）

### 3. autoconf 不探测 clang
- OCaml configure 的 AC_PROG_CC 只探测 gcc/cc/cl.exe，找不到本机 OHOS Clang 15
- 方案：显式注入 `CC=/data/service/hnp/bin/clang`（从 conan conf 读取，R33 不硬编码）
- 同时注入 `AS`/`AR`（GNU binutils）与 `TMPDIR`（可写目录）

### 4. HMDFS 拒绝覆盖已存在文件
- 现象：`cp runtime/ocamlrun boot/ocamlrun` → `Operation not permitted`
- 方案：改为 `rm -f && cp`

### 5. config.status 临时目录
- config.status 用 `mktemp -d` 创建临时目录（umask 077），OHOS 权限模型下失败
- 方案：配方内替换为 `mkdir -p` 方案（rm -rf + mkdir -p）

## 验证证据

- `conan create` RC=0（2026-07-31）
- test_package：`ocaml -version` → "The OCaml toplevel, version 4.14.1"
- 日志：`reports/conan-create.log`（成功版）、工作区 `ocaml-create-final2.log`

## 后续建议

- 产物级冒烟：用 ocamlopt 编译 hello.ml 并运行（验证 native 代码运行时）
- opam/dune 生态工具链适配为独立后续任务（不在本次范围）
