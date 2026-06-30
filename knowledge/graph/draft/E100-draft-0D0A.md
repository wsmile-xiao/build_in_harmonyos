# E100: OCaml Stdlib 模块未绑定错误

## 问题表现

OCaml编译时出现模块未绑定错误：
```
Unbound module Stdlib
ocaml: cannot find
bytecode: path hardcoded
Caml1999X031: wrong path
```

## 根因分析

OCaml bootstrap编译的顶层解释器字节码头部包含编译时的源码目录路径，而非安装后的标准库路径。

## 解决方案

设置CAMLLIB环境变量指向标准库位置：

```bash
export CAMLLIB=/storage/Users/currentUser/usr/local/lib/ocaml
ocamlrun -I $CAMLLIB ocaml
```

## 影响范围

OCaml及其衍生项目，opam冷启动编译，所有需要OCaml环境的项目。

## 验证方法

```bash
ocamlrun -config | grep -q "standard_library"
echo "OCaml path configured"
```

## 分类

- 类别: ocaml, toolchain, bytecode, bootstrap
- 严重性: 3（阻塞OCaml编译）
- 贡献者: 0D0A