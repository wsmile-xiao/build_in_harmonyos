# stdlib-shims 0.3.0 适配笔记

## 编译环境
- 构建系统: dune (OCaml build tool, Jbuild_plugin.V1)
- 编译日期: 2026-08-15
- 编译器: clang/clang++ + OCaml 4.14.1 (via Conan ocaml/4.14.1.1.2)
- 状态: built

## 源码来源
- 上游: https://github.com/ocaml/stdlib-shims/releases/download/0.3.0/stdlib-shims-0.3.0.tbz
- 本地缓存: .dep-cache/stdlib-shims.tar.gz (SHA256: 6d0386313a021146300011549180fcd4e94f7ac3c3bf021ff165f6558608f0c2)

## 编译步骤

stdlib-shims 使用 dune 构建系统，src/dune 使用 Jbuild_plugin.V1 在构建时生成 dune 规则：
1. 设置 OCaml 工具链环境变量 (PATH, OCAMLLIB, CAML_LD_LIBRARY_PATH)
2. 需要修复 OCaml Conan 包的 standard_library 路径 (symlink p/b/ → p/ 目录)
3. `dune build -p stdlib-shims` 构建字节码 (.cma)、原生 (.cmxa) 和共享 (.cmxs) 库
4. `dune runtest -p stdlib-shims` 运行上游测试
5. `dune install -p stdlib-shims --prefix=...` 安装到暂存目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | dune 报 `Makefile.config: No such file or directory` | OCaml Conan 包的 `standard_library` 指向 p/b/ 构建目录而非 p/ 包目录 | symlink `p/b/ocaml.../p/lib/ocaml` → `p/ocaml.../p/lib/ocaml` |
| 2 | `dune install --destdir` 报 `Operation not permitted` | HMDFS 文件系统限制 | 改用 `dune install --prefix=<stage>` 直接安装到暂存目录 |
| 3 | GitHub 下载超时 | HarmonyOS PC 网络无法直连 GitHub | 使用本地缓存 `.dep-cache/stdlib-shims.tar.gz` + `--no-download` |
| 4 | `ohc-run.py init-build` 解压失败 | /tmp 只读 (E002) | 脚本已使用 $TMPDIR (~/tmp)，但 file:// URL 的 tarball 格式检测有误 |

## 依赖版本

- ocaml/4.14.1.1.2 (Conan 包)
- dune (本地安装)

## 验证结果

```bash
dune build -p stdlib-shims    # exit 0
dune runtest -p stdlib-shims  # exit 0 (tests Stdlib.(+) and Stdlib.List.map)
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/stdlib-shims/stdlib_shims.cma | 字节码归档 |
| lib/stdlib-shims/stdlib_shims.cmxa | 原生归档 |
| lib/stdlib-shims/stdlib_shims.cmxs | 共享库插件 |
| lib/stdlib-shims/META | ocamlfind 元数据 |
| lib/stdlib-shims/dune-package | dune 包元数据 |
---

**编译结束**: 2026-08-15 14:48
**最终状态**: built
