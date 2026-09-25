# findlib (ocamlfind) 1.9.8 — HarmonyOS 编译记录

## 概述

findlib（命令行 `ocamlfind`）是 OCaml 的库管理器：读取包的 META 文件，把
`-package X` 翻译为编译/链接参数并驱动 OCaml 编译器。

**编译状态**: ✅ built（conan create RC=0，test_package 通过）

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS PC aarch64 |
| 编译器 | Clang 15.0.4 |
| C 库 | musl libc |
| 工具链依赖 | `ocaml/4.14.1.1.4`（`tool_requires`，CI 无系统 OCaml） |
| 构建系统 | 项目自带 autoconf 风格 configure + GNU Make |

## 编译步骤

```sh
/bin/sh ./configure -bindir <prefix>/bin -mandir <prefix>/share/man \
    -sitelib <prefix>/lib/ocaml -config <prefix>/etc/ocamlfind.conf \
    -no-custom -no-camlp4
make all        # 字节码
make opt        # 原生（含 findlib*.cmxs）
make install    # 优先安装原生 ocamlfind_opt
```

## OHOS 适配要点（1 个补丁，3 类问题）

补丁 `patches/0001-configure.patch`（+45/-7），全部以 `$OCAMLRUN` 为守卫：

1. **字节码工具 shebang 失效 + hmmac 拒绝脚本**：`ocaml` 顶层与构建出的
   `extract_args` 的 shebang 指向编译期嵌入的 ocamlrun 绝对路径；改为
   `ocaml_run()` 显式 `"$OCAMLRUN" tool ...` 调用。
2. **C stubs 搜索路径缺失**：`configure` 早期把 `lib/ocaml/stublibs` 注入
   `CAML_LD_LIBRARY_PATH` 并写入 `Makefile.config`，否则 dllunix 加载失败、
   且 DLL/ppxopt 能力探测误判。
3. **无 GNU install(1)**：探测 `install` 是否存在，缺失时回退 `mkdir -p` / `cp`。

## 测试

见 `1.9.8/test_package/MANIFEST.yml` 与 `1.9.8/reports/test-summary.md`。
上游 `itest` 在 4 个库上编译阶段全部通过；执行阶段受 OHOS OCaml
`-custom` 运行时平台限制，按 `docs/TEST_QUALITY_SPEC.md §3.3` 豁免，并以
原生 `ocamlopt` 等价路径完成 4/4 验证。

## 产物

- `bin/ocamlfind`（原生 ELF，可直接执行）
- `lib/ocaml/findlib/`（findlib.cma/.cmxa/.cmxs + 各 .cmi/.mli）
- `lib/ocaml/*/META`（stdlib/unix/str/threads/bigarray/dynlink/... 包描述）
- `etc/ocamlfind.conf`
