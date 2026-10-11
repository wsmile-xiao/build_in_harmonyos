# topkg 1.1.1 适配笔记

## 编译环境
- 构建系统: custom（上游为 topkg 自举 `ocaml pkg/pkg.ml build`，内部驱动 ocamlbuild；
  registry 尚未发布 ocamlbuild，本配方用 registry ocaml 工具链直连编译未修改源码）
- 编译日期: 2026-10-06
- 编译器: OCaml 4.14.1（registry `ocaml/4.14.1.1.4`）+ OHOS clang 15.0.4
- 平台: OHOS/aarch64（HarmonyOS PC）
- 状态: built

## 软件说明
topkg 是 OCaml 生态的打包库（ISC 许可）：库本体无 OCaml 级依赖，被大量
上游包（如 xmlm）作为**构建依赖**使用（`pkg/pkg.ml` 里 `#require "topkg"`）。
本包只构建 topkg 库本体；提供 `topkg` 命令行工具的 topkg-care 是独立包，不在本任务范围。

## 依赖版本
- ocaml/4.14.1.1.4（制品仓，armv8/OHOS/Release）
- （上游声明 ocamlfind/ocamlbuild 为构建依赖；直连编译不需要，见下）

## 编译步骤
1. `ocamldep -sort src/*.ml src/*.mli` 取模块依赖顺序
2. 按序编译：`.mli` → `ocamlc -c`；`.ml` → `ocamlc -c` + `ocamlopt -c`
3. 按 `ocamldep -sort` 的**依赖顺序**归档（依赖在前；OCaml 归档为单遍解析，
   上游 `src/topkg.mllib` 的 API-模块优先顺序不能直接用于归档链接）：
   `ocamlc -a -o topkg.cma`、`ocamlopt -a -o topkg.cmxa`、
   `ocamlopt -shared -ccopt -shared -o topkg.cmxs topkg.cmxa`
4. 上游测试（R51）：编译运行 `test/test.ml`
5. 安装布局：`lib/ocaml/topkg/`（cma/cmxa/cmxs/a + 全部 cmi + API topkg.mli +
   上游 pkg/META + topkg.opam）

## 上游构建替代说明（R36 相关）
上游 topkg 的构建链为 `ocamlfind（topfind）+ ocamlbuild`：pkg/pkg.ml 通过
`#use "topfind"` 自举，并由 ocamlbuild 生成 myocamlbuild.ml 构建库与测试。
制品仓当前**没有 ocamlbuild**（其适配已作为独立依赖任务导入/认领：
`ocamlbuild/0.16.1`，PR 待提交），因此本配方与 xmlm 1.4.0 先例一致，
用 ocamlc/ocamlopt 直连编译复现同一产物与测试，避免对未发布依赖的硬阻塞。
待 ocamlbuild 发布后，下游使用 topkg 的包可直接获得完整构建链。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `as: inaccessible or not found` | registry ocaml 包 Config.asm 为裸 `as`，OHOS 无 GNU as | shim `as` → `<OHOS clang> -c` |
| 2 | `/data/service/hnp/bin/clang: inaccessible or not found`（原生链接） | 烘焙 C 编译器为 CI worker 绝对路径 | `ocamlc`/`ocamlopt` shim 追加 `-cc <clang>`（R33） |
| 3 | cmxs 链接丢 `-shared`（`undefined symbol: main/caml_call_gc`） | 加 `-cc` 后 OCaml 丢失 `-shared` | `ocamlopt` shim 检测 `-shared` 时追加 `-ccopt -shared` |
| 4 | 字节码 shebang 指向构建期缓存路径 | ocaml 包烘焙 runtime 路径 | `ocamlc` shim 追加 `-use-runtime <真实 ocamlrun>` |
| 5 | 新链接 ELF 可能 EPERM | 部分 lld `.codesign` 不被 OHOS 接受 | `ocamlopt` shim 对链接产物重签名（`binary-sign-tool -selfSign 1`） |

## 源码修改
无补丁（patches_applied 为空；上游源码零修改）。

## 上游测试（R51，真机实测）
- `test/test.ml`（pkg/pkg.ml Pkg.test 条目）：编译并运行 → discovered=1 / passed=1
- 无其他上游自动化测试（topkg-care 的测试不在本包范围）

## 验证结果
- `conan-verify topkg 1.1.1 --profile ohos-aarch64-device`：**G0–G4 全 PASS**
- W3 本地 CI（`zsh ci/conan/build_and_test.sh archives/t/topkg/1.1.1`）：
  **L0/L1/L1e/L2/L4/L5 全 PASS，1/1 包，pass rate 100%**
- 上游测试 1/1（test/test.ml 打印 `The test is ok, the arguments are: alpha beta`）
- test_package：native 与 bytecode 双路径各 14 断言全通过（含真机 OS 交互 e2e）
- 详见 `reports/test-report.md`

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/ocaml/topkg/topkg.cma` | OCaml 字节码库 |
| `lib/ocaml/topkg/topkg.cmxa` / `topkg.a` | OCaml 原生库 + 原生归档 |
| `lib/ocaml/topkg/topkg.cmxs` | OCaml 动态插件库 |
| `lib/ocaml/topkg/*.cmi` / `topkg.mli` | 全部接口与 API 文档 |
| `lib/ocaml/topkg/META` / `topkg.opam` | findlib 元数据与 opam 元数据 |

## 发现与知识
- ✅ registry ocaml 下游原生编译的统一 shim 方案（as / -cc / -ccopt -shared /
  -use-runtime / ELF 重签名）可复用于全部 OCaml 库
- ✅ 上游 topkg 自举依赖 ocamlbuild；在其发布前，直连 ocamlc/ocamlopt
  可零修改复现产物与测试（xmlm 1.4.0 同法）
- ✅ topkg 库本体无 OCaml 级依赖，消费侧仅需 cmi + 归档 + META

---
**编译结束**: 2026-10-06
**最终状态**: built
---

**编译结束**: 2026-10-06 13:09
**最终状态**: built
