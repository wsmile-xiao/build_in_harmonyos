# ocaml-syntax-shims 1.0.0 适配笔记

## 编译环境
- 构建系统: dune (OCaml build system)
- 编译日期: 2026-08-15
- 编译器: clang/clang++ (OCaml 4.14.1 native compiler ocamlopt)
- 状态: built

## 编译步骤

1. `conan install --requires=ocaml/4.14.1.1.2 --requires=dune/3.17.0` 安装依赖
2. 设置 PATH 包含 OCaml bin 和 dune bin
3. 创建 dune 需要的 OCaml Conan 路径符号链接（解决 stale path 问题）
4. `dune build -p ocaml-syntax-shims` 编译
5. 手动拷贝构建产物到 staging 目录（dune install 在 HMDFS 上失败）
6. `dune runtest -p ocaml-syntax-shims` 运行测试

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | dune 找不到 ocamlc | conanrun 环境未包含 OCaml bin 路径 | 手动设置 PATH 指向 OCaml Conan 包的 bin 目录 |
| 2 | dune 报 Makefile.config not found (stale path) | dune 二进制硬编码了编译时 OCaml 包路径，该路径已不存在 | 创建符号链接指向实际 OCaml 包目录 |
| 3 | dune install 报 Operation not permitted | HMDFS 不允许 dune 遍历父目录 | 手动从 _build/install/default/ 和 _build/default/ 拷贝产物 |

## 源码修改

无源码修改，无需补丁。

## 依赖版本

- ocaml/4.14.1.1.2
- dune/3.17.0

## 验证结果

```bash
$ dune build -p ocaml-syntax-shims  # 编译成功
$ dune runtest -p ocaml-syntax-shims  # 测试通过
$ file staging/bin/ocaml-syntax-shims  # ELF shared object, 64-bit LSB arm64
$ echo "let x = 1" | staging/bin/ocaml-syntax-shims  # 运行正常
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/ocaml-syntax-shims | ~13MB | OCaml 语法预处理器可执行文件 |
| lib/ocaml-syntax-shims/META | - | OCaml findlib 元数据 |
| lib/ocaml-syntax-shims/dune-package | - | dune 包元数据 |

## 注意事项

- ocaml-syntax-shims 是命令行工具（application），不是库
- 需要 R38 commands.json 声明
- dune install 在 HMDFS 上不可用，package() 方法使用手动拷贝
- 构建时需要创建 stale Conan 路径的符号链接
---

**编译结束**: 2026-08-15 15:15
**最终状态**: built
