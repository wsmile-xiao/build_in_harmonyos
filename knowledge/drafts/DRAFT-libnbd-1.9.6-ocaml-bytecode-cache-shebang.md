# DRAFT：OCaml 工具链字节码程序内嵌构建期缓存路径失效

> Contributor: oh-executor (pc1-38) | Status: Draft | Updated: 2026-09-16
> Source: libnbd 1.9.6 首轮适配（task libnbd-1.9.6-r01-pc1-38）

## 背景

libnbd 的 git tag tarball 不含生成器输出（`lib/api.c`、`lib/states*.c`、
`lib/states.h`、`include/nbd.h`），make 时由 OCaml 生成器（`generator/`）产出。
因此配方以 `tool_requires("ocaml/4.14.1.1.4")` 引入 OCaml。构建期依次暴露
三个连锁错误：

```text
① File "command line", line 1: Error: Unbound module Stdlib
② .../generator/generator: bad interpreter:
   /storage/Users/currentUser/.cache/conan2/p/b/ocamle031b9bdb525f/p/bin/ocamlrun:
   No such file or directory
③ ocamldoc -man ... : bad interpreter ... ocamlrun: No such file
```

## 根因

1. ocaml 配方把 `package_folder` 作为 prefix 编译，字节码程序（ocamlc/ocamldoc/
   ocamlrun）的 `#!` shebang 内嵌**构建期缓存路径**（`.cache/conan2/p/b/ocamlXXXX/p/...`）；
   包被导出/重新缓存后该路径不存在 → "bad interpreter"（②③）。
2. ocamlc 通过 `OCAMLLIB` 定位 `stdlib.cmi`；未设置时即使 ocamlc 在 PATH 上也报
   `Unbound module Stdlib`（①）。
3. 字节码程序链接 `str.cma`/`unix.cma` 后运行需 `CAML_LD_LIBRARY_PATH` 定位
   stublibs（`dllcamlstr.so`/`dllunix.so`）。

## 方案

在 `build()` 内直接注入环境（**不要**走 conan env 脚本——曾因 env 脚本膨胀触发
`printenv: Argument list too long`，改回 `os.environ` 后消失）：

```python
os.environ["OCAMLLIB"] = os.path.join(ocaml_pkg, "lib", "ocaml")
os.environ["CAML_LD_LIBRARY_PATH"] = os.path.join(ocaml_pkg, "lib", "ocaml", "stublibs")
os.environ["OCAMLDOC"] = "no"   # 跳过仅 OCaml 绑定需要的 manpages
```

生成器字节码就地改写 shebang：

```python
with open(gen, "r+b") as fh:
    fh.write(b"#!" + os.fsencode(ocamlrun) + b"\n")
```

另外注意：libnbd configure.ac 中 `HAVE_OCAMLC` 同时要求 `enable_ocaml=yes`
（L378-381），**不要**传 `--disable-ocaml`，否则生成器整体禁用；
禁用 OCaml *绑定* 通过不装 ocamlfind 自然达成（HAVE_OCAML=no）。

## 验证

`conan create`（OHOS profile）全链路通过：生成器正常产出 lib/api.c 等，
test_package 2/2 通过（test_libnbd + ohos_spec_test）。

## 适用边界

- 适用：所有以 ocaml 为 tool_requires、构建期运行字节码生成器/ocamlc 的三方库
- 反例：ocaml 配方原生编译（.opt）或 prefix 不移动时不触发；本机未移缓存也不触发
- 可复用性：跨库可复用（ocaml 生成器项目、ocaml 绑定包均同模式）

## 查重

- knowledge/graph/：E037/E049/E165 覆盖通用 shebang/bad interpreter 类别
  （perl/python//bin/bash 场景），无 OCaml 字节码 + conan 缓存路径 + OCAMLLIB
  注入的组合条目 → 部分覆盖、存在新增差异
- 关系：`similar_to: E165`；`caused_by: ocaml 配方 prefix 内嵌`（不属本库）；无
  prerequisite_of / conflicts_with

## 附带观察候选（登记不建草稿）

lang-preflight（ohc/lang_detect.py）对带 golang/python/ocaml 绑定子目录的 C 库，
`_manifest_scan` 用全树文件集合检查 `go.mod` 会把绑定子目录的 go.mod 当作
manifest（libnbd 被判 mixed/go 而误报 env_unsupported）；判定应限定在顶层文件
（`p.parent == src` 的 tops），或把绑定目录排除出 manifest 探测。已按 C 主体人工
复核后继续适配并通过全链路验证。
