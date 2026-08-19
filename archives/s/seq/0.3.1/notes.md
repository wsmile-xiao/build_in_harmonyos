# seq 0.3.1 — 适配笔记

## 概述

seq 提供了 OCaml < 4.07 的兼容性 Seq 模块。作为 yojson (OCaml 4.14) 的运行时依赖。

## 构建系统

- dune (OCaml 构建工具)
- 依赖: ocaml/4.14.1.1.2, dune/3.17.0@ohpcd/stable

## 关键适配点

1. **OCaml shebang 修复**: Conan 构建时路径在安装后不存在，需要在 build() 中修正 shebang
2. **环境变量**: 必须设置 OCAMLLIB、CAML_LD_LIBRARY_PATH、PATH
3. **HMDFS 限制**: 使用 `--root=.` 避免 dune 遍历 HMDFS 父目录
4. **META 文件**: package() 中手动生成 OCaml findlib META 文件

## 上游测试

- `test/t.ml`: 验证 Seq.fold_left 对 0..10 求和 = 55
- 执行: `dune runtest`
- 结果: 通过 ✅

## Conan verify

- G0-G4 + L2/L4/L5: 全部 PASS
- conan create: 成功
