# DRAFT: OHOS 真机无 GNU as —— registry OCaml 下游 ocamlopt/dune 的裸 `as` 失效与 PATH shim 修复

> Contributor: kasumizawa-miyuu（9C4A） | Status: Draft | Updated: 2026-10-04
> Source: xmlm 1.4.0 适配（PR OpenHarmonyPCDeveloper/build_in_harmonyos!14675）
> 对应 KV: `knowledge/drafts/DRAFT-xmlm-1.4.0-ocamlopt-missing-gnu-as-shim.kv`
> 关联: E253（OCaml 工具链自身迁移）、DRAFT-gas-arm64-clang-integrated-as（C 侧 .S 经 CC 编译）

## 主题 / 触发场景

用 registry 的 `ocaml/4.14.1.1.4` 包在 OHOS PC 真机做**原生 OCaml 编译**时，构建在
汇编阶段失败：

```text
sh: as: inaccessible or not found
File "caml_startup", line 1:
Error: I/O error: as  -o 'hello.o' '/.../camlasm1234.s'
```

`command -v as` 为 MISSING；SDK 只有 `llvm-as`（LLVM IR 汇编器，不能处理 GAS 文本）。
该问题对 `ocamlopt`、`dune` 的 native target、`ocaml pkg/pkg.ml build`（topkg）一视同仁，
且报错点深藏在 OCaml 驱动内部，从 conanfile 或上游源码看不出线索。

## 根因

registry `ocaml` 包在 CI worker 上构建时，`Config.asm` 被烘焙为裸 `as`（GNU 汇编器名，
文件名不带路径）。OHOS PC 真机没有 GNU as；`ocamlopt` 进入汇编阶段时按 PATH 查找
`as`，失败即中断整个原生构建。**缺少的只是一个接收 `-o out.o in.s` 语义的汇编器可执行名。**

## 可复用方案

在 `build()`（以及 test_package 的 `test.sh`）中生成最小 `as` shim：

```sh
#!/bin/sh
exec /path/to/ohos/sdk/native/llvm/bin/clang -c "$@"
```

- clang 集成汇编器原生支持 GAS 语法 aarch64 `.s`（零补丁）
- shim 目录前置到 PATH（在 ocaml bin 之前），不修改 conan 缓存里的 ocaml 包、不修改上游源码
- clang 路径从 conan conf `tools.build:compiler_executables.c` 读取（R33，不硬编码）
- shim 只存在于构建/测试工作目录，绝不进包

## 适用边界

- ✅ 一切 registry OCaml 下游包的原生编译（ocamlopt / dune / topkg / ocamlfind 工具链）
- ✅ 与 `-cc` 覆盖、cmxs `-ccopt -shared` 组合使用（另见同批草稿）
- ⚠️ 仅字节码（ocamlc）路径不触发；若环境本就有 GNU as，shim 不会被调用，无副作用

## 验证证据

- xmlm 1.4.0：conan-verify G0–G4 全 PASS；4/4 上游 Pkg.test；22 断言消费者测试
  （native+字节码双路径）与设备文件 I/O e2e 全绿（PR #14675）
- 同族先例：camlp-streams 5.0.1（dune 构建）、findlib 1.9.8 均在 registry ocaml
  工具链上适配成功

## 与现有知识的差异（查重说明）

- **E253** 处理的是「OCaml 工具链自身如何迁移到 OHOS」（configure/testsuite/hmmac），
  不含「已发布的 registry ocaml 包在真机下游编译时的汇编器缺失」
- **DRAFT-gas-arm64-clang-integrated-as** 讲 C 编译器驱动 (`$(CC) -c foo.S`) 场景；
  本条是 OCaml 驱动器内部对**外部 `as`** 的硬调用，必须靠 PATH shim 改变查找结果
