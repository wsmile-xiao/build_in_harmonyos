# xml-light

Xml-Light 是 OCaml 的极简 XML 解析/打印库（含 DTD 解析、校验与证明），
纯 OCaml 实现无 C 依赖。上游 2.5 起使用 dune 构建，库以 `wrapped false`
发布，公开模块为 Xml / Dtd / XmlParser（内部含 ocamllex/ocamlyacc 生成
的 xml_lexer / xml_parser）。

## 版本

| 版本 | 状态 | 构建系统 | 备注 |
|------|------|----------|------|
| 2.5 | built | custom (dune) | registry ocaml/4.14.1.1.4 + dune/3.17.0 |

## 适配要点（OHOS）

- dune @install 树为指向 `_build/` 的相对软链，HMDFS 下不可靠——
  `package()` 以 `copytree(symlinks=False)` 拷贝实文件到
  `lib/ocaml/xml-light`（findlib 布局，camlp-streams/menhir 先例）
- registry OCaml 4.14.1 无 findlib：下游消费用显式 cma/cmxa 链接
  （见 test_package/test.sh）
- OCAMLLIB/CAML_LD_LIBRARY_PATH/PATH 从依赖包 folder 注入
  （conan cache 重定位后 `ocamlc -where` 返回陈旧路径）
- 上游源码 `.tbz` 归档：`source()` 显式 `filename=*.tar.bz2`
  （该 Conan 版本 unzip() 不识别 `.tbz` 扩展名，xmlm 先例）
- 上游测试（tests/ 的 2 个 runtest 动作）经 `dune runtest -p xml-light`
  在 build() 中真实执行（R51）
