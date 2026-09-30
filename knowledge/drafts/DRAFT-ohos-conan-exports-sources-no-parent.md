# DRAFT-ohos-conan-exports-sources-no-parent — conan 2 exports_sources 禁止 '..' 相对路径，vendored 大目录无法跨版本共享

> Contributor: ohpcd / AtomCode | Status: DRAFT | Updated: 2026-09-18 | Severity: 🟠 major
> Source: gobject-introspection 1.80.1（PR #10682）——gi-distutils 147 文件体量问题，裁剪为 24 文件

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|----------|---------|--------|--------------------------|
| E308 | 已收录 | Conan **test_package 模板后缀**不被 CI L0c 识别（`no_test_sources`）——完全不同的 conan 细节 | 本 skill 是 `exports_sources` **路径越界**报错（`'..'` 相对模式被拒），与 test_package 模板无关 |
| DRAFT-celero-2.10.0-conandata-patches-export-sources-hook | draft | `export_sources()` **钩子方法**用法（`export()` 钩子里 export_folder 为 None 报 TypeError，改 `export_sources` 属性通过） | 本 skill 是 `exports_sources` **路径模式本身**不能含 `..`——即使正确使用 `exports_sources` 属性，越界模式也会被拒；两者是 export 阶段的两个不同错误面 |
| E429-draft-E4BC | draft | 与 conan export 无关（同一 E429 编号下的其他草稿变体） | 无冲突 |

**撞车判定**：全库查证 `exports_sources.*\.\.` 精确语义（0 命中）。E308 与 celero 草稿均为 export 阶段不同错误面，未覆盖「`..` 相对模式被拒 → vendored 大目录无法跨版本共享，只能复制或裁剪」这一结论，作为独立条目申报。

## Scope（何时用）

- 版本目录内 vendoring 了第三方大目录（distutils / setuptools / 其他），需要为同库新增版本变体、想复用既有 vendored 内容时
- 报错：`ERROR: copy() it is not possible to use relative patterns starting with '..'`
- 提 PR 前评估体量（平台评审上限约 152 文件 / 46200 行，超出跳过 AI 评审）

## Symptom

```
$ conan export .
...
ERROR: copy() it is not possible to use relative patterns starting with '..'
```

（试图 `exports_sources = ["../1.78.1.1/gi-distutils/*"]` 复用兄弟版本目录时的直接报错）

## Root Cause

1. conan 2 对 `exports_sources`（及 `export_sources`）的路径解析**不允许越出 recipe 目录**：任何以 `..` 开头的相对模式直接拒绝（实测于 conan 2.x）。
2. 因此仓库惯例「版本后缀 = 变体、每版本目录自包含」下，大体积 vendored 目录**无法**跨版本共享，只能二选一：
   - **逐版本复制**（既有惯例）——推高 PR 体量，可能触发平台评审跳过；
   - **裁剪到运行时最小依赖闭包**——用目标解释器（无 setuptools 劫持的 conan python）实测 `import` 闭包，只保留真实引用的模块（GI 实测 147 → 24 文件）。
3. 陷阱：宿主 python 可能因 setuptools 的 `_distutils_hack` 劫持 `distutils` 而给出错误的（更大或不同的）闭包——裁剪依据**必须**用配方实际使用的 conan python 测，否则闭包判定失真。

## Workaround / 修复

- 无跨版本共享合规路径；选「裁剪到最小闭包」：
  1. 用 conan python（`LD_LIBRARY_PATH` + 直接跑）逐个加载消费方真实 import 的模块，枚举 `sys.modules` 取闭包；
  2. 只保留闭包内文件 + 其 companion 包；
  3. 补运行时发现缺失的模块（如 `more_itertools.recipes`，闭包探测可能漏末行）；
  4. `conan create` 全绿（gir 生成 + 上游测试 + test_package）为验收。
- 体量收益（GI 实证）：158 文件 / 47142 行 → 35 文件 / ~12600 行。

## Prevention

- 新增版本变体前先评估 vendored 目录体量，能裁则裁，避免提一个大到被评审跳过的 PR。
- 评审体量上限约为 152 文件 / 46200 行，超过即 AI 评审整体跳过。

## References

- PR #10682（GI 1.80.1，gi-distutils 147→24 文件）
- 仓库惯例「版本后缀 = 变体」
