# xmlm 1.4.0 适配笔记

## 编译环境
- 构建系统: custom（上游 topkg `ocaml pkg/pkg.ml build` + ocamlbuild；registry 无 topkg/ocamlbuild，改为 ocamlc/ocamlopt 直接编译未修改源码）
- 编译日期: 2026-10-04
- 编译器: OCaml 4.14.1（registry `ocaml/4.14.1.1.4`，ocamlc/ocamlopt）+ OHOS clang 15.0.4
- 平台: OHOS/aarch64（HarmonyOS PC）
- 状态: built

## 软件说明
xmlm 是 OCaml 的流式 XML 编解码库（单模块，ISC 许可），可在不构建完整
内存表示的情况下解码/编码 XML；同时安装 `xmltrip` 检查工具。

## 语言预检说明（R47）
lang-preflight 判 `detected_language=other`（`lang_detect.py` 的扩展名表与
§4.6 枚举均不含 OCaml），并自动写了一条 `env_unsupported` 终态。经核验这
是**工具盲区误报**，不是真实的语言不匹配：
- 源码主体为 OCaml（`src/xmlm.ml` + `src/xmlm.mli`，测试为 `.ml`），无其他语言
- registry 已提供 OCaml 工具链（`ocaml/4.14.1.1.4`），且同族纯 OCaml 包
  （camlp-streams 5.0.1、mlgmp、ocaml-syntax-shims、ocaml 4.14.x 等）均已
  按同一流程适配成功并合入本仓库
- 按 camlp-streams 5.0.1 已确立的先例继续适配，最终 result.json 以真实
  结果重写（本任务不做语言迁移）

## 编译步骤

1. 依赖（W0，制品仓预编译包）：`ocaml/4.14.1.1.4`（armv8/OHOS/Release）
2. 库（`src/` 内）：
   - `ocamlc -c xmlm.mli` → `xmlm.cmi`
   - `ocamlc -c xmlm.ml` → `xmlm.cmo`；`ocamlc -a -o xmlm.cma xmlm.cmo`
   - `ocamlopt -c xmlm.ml` → `xmlm.cmx/.o`；`ocamlopt -a -o xmlm.cmxa xmlm.cmx`
   - `ocamlopt -cc <clang> -shared -ccopt -shared -o xmlm.cmxs xmlm.cmx`
3. 上游测试（R51，4 个 `Pkg.test`）：`ocamlopt -I src src/xmlm.cmxa test/<t>.ml`
   编译并执行（test/test_tree/xhtml/examples），全部 exit 0
4. 工具（`Pkg.bin`）：`ocamlopt ... test/xhtml.ml test/xmltrip.ml -o xmltrip`，
   并用样例 XML `-p` 冒烟
5. 安装布局（等价 topkg install）：`lib/ocaml/xmlm/`（cma/cmxa/cmxs/a/cmi/ml/mli
   + 上游 `pkg/META`）+ `bin/xmltrip`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 判 other/env_unsupported | lang_detect.py 不识别 `.ml`/opam/topkg | 工具盲区误报，按 camlp-streams 先例继续适配，终态以真实结果重写 |
| 2 | `ocamlopt` 报 `as: inaccessible or not found` | registry ocaml 包配置的汇编器是裸 `as`，OHOS 无 GNU as（SDK 只有 llvm-as，语义不同） | build()/test.sh 生成 `as` shim：`exec <OHOS clang> -c "$@"`，PATH 前置 |
| 3 | 链接报 `/data/service/hnp/bin/clang: not found` | ocaml 包烘焙的 `native_c_compiler` 是 CI worker 路径，真机不存在 | 所有 ocamlopt 调用加 `-cc <conf 中的 OHOS clang>` |
| 4 | 加了 `-cc` 后 cmxs 链接丢 `-shared`（报 undefined `main`/`caml_call_gc`） | OCaml 的 `-cc` 覆盖路径下未附加 `-shared` | 追加 `-ccopt -shared` |
| 5 | `conan create` source 解压失败/未平铺 | Conan `unzip()` 不识别 `.tbz` 扩展名；get() 需显式 strip_root | `get(..., filename="xmlm-1.4.0.tar.bz2", strip_root=True)` |
| 6 | `copy(keep_permissions=True)` TypeError | 本版本 Conan `copy()` 无此参数 | 去掉该参数，copy 后 `os.chmod(0o755)` |
| 7 | e2e 测试属性/数据类型混淆 | xmlm 属性类型为 `Xmlm.attribute = name * string`（name 为二元组），与 `(string*string)` 不同 | node 类型直接使用 `Xmlm.attribute list`，数据节点独立 `Data` 变体 |

## 源码修改
无补丁（patches_applied 为空；上游源码零修改）。

## 依赖版本
- ocaml/4.14.1.1.4（制品仓，revision 1537a565…，armv8/OHOS/Release）

## 依赖发布检查（W0）
`conan download ocaml/4.14.1.1.4 -r=ohpcd [--only-recipe]` + `conan list` 双确认：
recipe 与 armv8/OHOS/Release binary 均在制品仓，无缺失依赖（R36 无阻塞）。

## 验证结果
- `conan-verify xmlm 1.4.0 --profile ohos-aarch64-device`：**G0–G4 全 PASS**
- W3 本地 CI（`zsh ci/conan/build_and_test.sh archives/x/xmlm/1.4.0`）：
  **L0/L1/L1e/L2/L4/L5 全 PASS，1/1 包，pass rate 100%**
- 上游 4/4 测试通过；test_package 22 断言通过（native+bytecode 双路径）；
  鸿蒙 e2e 9/9 断言通过
- 详见 `reports/test-report.md`

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/ocaml/xmlm/xmlm.cma` | OCaml 字节码库 |
| `lib/ocaml/xmlm/xmlm.cmxa` / `xmlm.a` | OCaml 原生库 + 原生归档 |
| `lib/ocaml/xmlm/xmlm.cmxs` | OCaml 动态插件库 |
| `lib/ocaml/xmlm/xmlm.cmi` / `xmlm.mli` / `xmlm.ml` | 接口与实现 |
| `lib/ocaml/xmlm/META` | findlib/ocamlfind 元数据（上游 pkg/META 原样） |
| `bin/xmltrip` | XML 流检查工具（可解析/输出/树形/diff 模式） |

## 发现与知识
- ✅ 纯 OCaml 库适配路径：`requires ocaml/4.14.1.1.4` + 直接 ocamlc/ocamlopt
  （registry 无 topkg/ocamlbuild 时的等价替代）
- ✅ OHOS 无 GNU as：ocamlopt 需要 `as` shim → `<OHOS clang> -c`
- ✅ registry ocaml 包烘焙工具链为 CI 路径，真机必须 `-cc <clang>` 覆盖；
  `-cc` 会导致 cmxs 丢掉 `-shared`，需 `-ccopt -shared` 补回
- ✅ Conan `get()`：`.tbz` 不在 unzip 扩展名映射中，需 `filename=` 重命名
  为 `.tar.bz2` 才走 bz2 解压分支
- ✅ 纯 OCaml 字节码（无 C stub）可直接 `ocamlrun` 执行（与 mlgmp 的
  -custom EPERM 情形不同），消费者测试可原生+字节码双路径

---
**编译结束**: 2026-10-04
**最终状态**: built
