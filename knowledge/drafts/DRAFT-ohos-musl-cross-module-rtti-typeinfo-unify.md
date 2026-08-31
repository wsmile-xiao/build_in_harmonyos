# DRAFT-ohos-musl-cross-module-rtti-typeinfo-unify：OHOS/musl 跨 dlopen 边界 RTTI typeinfo 统一

> Contributor: sea_crab | Status: Draft | Updated: 2026-08-29
> Source: bali-phy 4.1 HarmonyOS PC adaptation（patch 0003，用户决策 A）
> 对应：knowledge/drafts/DRAFT-ohos-musl-cross-module-rtti-typeinfo-unify.kv

## 现象

主程序 + dlopen 插件架构的 C++ 库在 OHOS/musl 下运行期出现"同名类型
dynamic_cast 失败"：

```text
Cannot convert 'unprintable[Box<std::__n1::shared_ptr<alphabet const>>] 0x59d1a7b180'
from type Box<std::__n1::shared_ptr<alphabet const>> to type Box<std::__n1::shared_ptr<alphabet const>>
```

bali-phy 4.1 的 `--test`、MCMC（`5d` 系列）、Haskell 运行时路径全部命中
（src/computation/object.H:144 dynamic_cast）。与上游 issue#23（`Term 'x' of
type '#19' cannot be converted to type 'Double'`，linux-aarch64 4.0）属同类
aarch64 类型转换问题；官方在 4.2 修复并关闭 issue#23（closed_at=2026-06-04）。

## 与现有知识的关系（确认去重证据）

检查范围：knowledge/graph（E001~E320，322 行 index.tsv）+ knowledge/drafts（本分支
HEAD 423 个文件）+ 经验仓 ophs_ci_review（HEAD=1715154b，工作树干净）。
检索词：rtti / typeinfo / dynamic_cast / dlopen / export_dynamic / dynsym /
-rdynamic / typeid / type_info / weak symbol / strong_ordering。
命中均为 musl 符号解析（E004/E078 BIND_NOW）、LD 搜索路径（E019/E088）、
musl pthread weak（E085）、RUNPATH（E131/E212）、LLVM 共享库不一致（E218）、
签名加载闭包（DRAFT-pam-wrapper-ctest-elf-runtime-closure）等，**均非 C++ RTTI
typeinfo 跨模块统一**；graph/drafts/经验仓无 `bali` 命中。无覆盖。

## 知识库沉淀价值

- 可复用问题类别：C++ dlopen 插件架构在 OHOS/musl 下的跨模块
  dynamic_cast/typeid 失败（weak typeinfo 不统一）。
- 适用对象：任何"主程序 + dlopen 插件 .so + 跨模块 dynamic_cast/typeid"的库
  （bali-phy 29 builtins 之外，GStreamer 类插件、语言运行时插件、mono/llvm
  插件等）迁移 OHOS 都可能命中。
- 决策价值：遇到 `Cannot convert ... from type X to type X` 可直接套用
  "readelf .dynsym 计数 → 缺省 typeinfo 清单 → 显式实例化 TU + export_dynamic"
  配方，省去多轮探针。

## 方案

1. 新增 `rtti-inject.cc` TU，对 builtins 需要而主程序缺省的 `Box<T>` 类型显式实例化
   （`template class Box<T>;`，bali-phy 0003 共 14 个）。
2. 该 TU 注册进主程序目标 sources（bali-phy：`baliphy_sources` 追加 `'rtti-inject.cc'`）。
3. 主程序 `export_dynamic: true`（等效 -rdynamic/--export-dynamic），使 weak typeinfo
   进入 `.dynsym` 导出集合。
4. 真机探针证明：主程序定义并导出同名 weak `_ZTI3Box...` 后，musl 把 dlopen 模块
   的引用插桩到主程序定义，跨模块 dynamic_cast 成功（rtti-probe3：
   `explicit_inst_cross_dynamic_cast=OK`）。

## 验证证据

- 修复前：round-2 实机 82/218 FAIL（动态类型转换错误）；exe `.dynsym`/`.symtab`
  均无 `_ZTI3BoxINSt4__n110shared_ptrIK8alphabetEEE`，而 Alphabet/Alignment/
  Parsimony .so 各自 WEAK 定义同名 typeinfo（readelf -Ws 实证）。
- 修复后：readelf 实测 exe 导出 54 行 `_ZTI3Box*`（27 个 distinct typeinfo 含
  注入的全部 14 个；`.dynsym` 内 27 个）；meson test 218/218 全量 OK、
  test_package 10/10、create_exit_code=0、29 个 builtins .so 签名成功。

## 禁止做法

- 用 `ignore_errors=True` / `meson test || true` 吞掉 RTTI 失败假装通过。
- 用 `setarch -R` 关闭地址随机化回避 typeinfo 指针比较（绕过而非修复）。
- 把 issue#23 直接等同于本诊断机理：issue#23 正文只记录症状，本配方 0003 的
  "RTTI 弱符号插桩"是 OHOS/musl 特有原创诊断（4.2 未采用注入方案）。
