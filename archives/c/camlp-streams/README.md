# camlp-streams

camlp-streams 提供 OCaml 的 Stream 与 Genlex 库。这些库从 OCaml 标准库
拆分出来，将在未来版本从 stdlib 移除并在此独立维护。

纯 OCaml + dune 构建，无 C 代码，无外部依赖（仅需 OCaml 工具链）。

## 版本

| 版本 | 状态 | 构建系统 | 备注 |
|------|------|----------|------|
| 5.0.1 | built | custom (dune) | registry ocaml/4.14.1.1.4 + dune/3.17.0 |

## 适配要点（OHOS）

- dune @install 树为指向 `_build/` 的相对软链，HMDFS 下不可靠——
  `package()` 从 `_build/default` 拷贝实文件并手写完整 META
- registry OCaml 4.14.1 无 findlib：下游消费用显式 cma/cmxa 链接
- OCAMLLIB/CAML_LD_LIBRARY_PATH/PATH 从依赖包 folder 注入
  （conan cache 重定位后 `ocamlc -where` 返回陈旧路径）
