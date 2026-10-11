# DRAFT: registry OCaml 包的 C 编译器死路径与 cmxs 链接契约 —— `-cc` 覆盖后必须 `-ccopt -shared` 补回

> Contributor: kasumizawa-miyuu（9C4A） | Status: Draft | Updated: 2026-10-04
> Source: xmlm 1.4.0 适配（PR OpenHarmonyPCDeveloper/build_in_harmonyos!14675）
> 对应 KV: `knowledge/drafts/DRAFT-xmlm-1.4.0-ocamlopt-baked-cc-dead-path-cmxs-shared.kv`
> 关联: E253（工具链自身迁移）、DRAFT-ocamlopt-lld-static-shadow-explicit-closure（-L 影子归档）

## 主题 / 触发场景

registry 的 `ocaml/4.14.1.1.4` 包在真机下游使用时，原生链接阶段依次出现两个连锁错误：

```text
# ① 死路径：ocamlopt 调用的 C 编译器是 CI worker 绝对路径
sh: /data/service/hnp/bin/clang: inaccessible or not found
File "caml_startup", line 1:
Error: I/O error: /data/service/hnp/bin/clang -shared -L... -o 'xmlm.cmxs' ...

# ② 用 -cc <OHOS clang> 覆盖后，cmxs 链接丢失 -shared
ld.lld: error: undefined symbol: main
>>> referenced by crt1.c ... Scrt1.o:(_start_c)
ld.lld: error: undefined symbol: caml_call_gc
>>> referenced by xmlm.cmxs.startup.o
```

## 根因

1. `ocamlopt -config` 显示 `c_compiler` / `native_c_compiler` / `bytecomp_c_compiler` 均烘焙为
   `/data/service/hnp/bin/clang ...`（CI worker 路径），真机不存在 → 任何需要 C 编译器的
   阶段（原生可执行链接、cmxs）直接 I/O error。
2. 显式 `-cc <OHOS clang>` 覆盖后，OCaml 4.14 的 cmxs `-shared` 链接路径不再自动向 C
   编译器附加 `-shared`：实测链接行变成
   `clang -o xmlm.cmxs -L... xmlm.cmxs.startup.o xmlm.o`（无 `-shared`），lld 遂以
   PIE 可执行语义链接（拉入 Scrt1.o / crt1.c），报 `undefined symbol: main` 与
   OCaml 运行时符号。

## 可复用方案

```bash
# 1) 所有 ocamlopt 调用显式 -cc（路径取 conan conf tools.build:compiler_executables.c，R33）
ocamlopt -cc "$CC" -I src src/xmlm.cmxa test/test.ml -o test.exe
# 2) cmxs（动态插件）链接补回 -shared
ocamlopt -cc "$CC" -shared -ccopt -shared -o xmlm.cmxs xmlm.cmx
```

- 两条命令互补：`-cc` 治死路径，`-ccopt -shared` 治共享标志丢失
- 不需要时（如纯 `ocamlc -a` 字节码归档）无需改动

## 适用边界

- ✅ 一切 registry OCaml 下游包的原生可执行链接与 `.cmxs` 插件构建
- ✅ 与「as shim」草稿组合成完整的 registry OCaml 下游原生工具链修复三件套
- ⚠️ 不产生 cmxs 的包可省第 2 步；纯字节码不受影响

## 验证证据

- xmlm 1.4.0：`xmlm.cmxs` 生成成功（ELF）；conan-verify G0–G4 全 PASS；4/4 上游
  Pkg.test；22 断言消费者测试 + 设备 e2e 全绿（PR #14675）
- 判定入口：`ocamlopt -config` 查看烘焙编译器路径；`ocamlopt -verbose` 查看实际链接行

## 与现有知识的差异（查重说明）

- **E253**：编译器自身的迁移（configure/make/testsuite），不涉及下游链接驱动契约
- **DRAFT-ocamlopt-lld-static-shadow-explicit-closure**：根因是 `-L` 目录里 `.a` 影子化
  `.so`，修复靠绝对路径显式供给；本条根因是死路径 + `-shared` 标志丢失，修复靠
  `-cc` / `-ccopt -shared`
