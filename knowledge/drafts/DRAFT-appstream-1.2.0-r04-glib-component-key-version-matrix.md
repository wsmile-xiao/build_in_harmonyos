# DRAFT-appstream-1.2.0-r04-glib-component-key-version-matrix — glib 组件键跨版本差异（-2.0 后缀）导致 PkgConfigDeps 组件 requires 解析失败

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: blocking (3) | **Category**: conan / pkg-config / glib / version-matrix / ohos
> **Audience**: 所有 compose/渲染链命中 ohpcd 预编译（绑定特定 glib 组件键命名）的 Conan 项目

## 触发（trigger）

- appstream 1.2.0 R04：compose 门控依赖链（pango/cairo/vips/harfbuzz）命中 ohpcd
  预编译，其绑定 glib/2.84.0.1（组件键带 -2.0 后缀：glib-2.0/gobject-2.0/gio-2.0/
  gmodule-2.0）；而 libxmlb 等库配方的 package_info 组件 requires 引用旧版组件名
  （glib::glib/gobject/gio/gmodule，无后缀，为 glib/2.88.3 命名体系编写）。

## 症状（symptom）

```
Error in generator 'PkgConfigDeps': Component 'glib::gobject' not found in 'glib' package requirement
```
或反向（glib/2.88.3 下 pango 引用 -2.0 后缀）：
```
Component 'glib::glib-2.0' not found
```

## 机制（root cause）

1. glib 2.84.0.1 与 2.88.3 配方的 cpp_info 组件键命名体系不同：
   - 2.84.0.1：`glib-2.0/gobject-2.0/gio-2.0/gmodule-2.0`
   - 2.88.3：`glib/gobject/gio/gmodule`
2. ohpcd 预编译的 pango/cairo 绑定 2.84.0.1（-2.0 后缀），libxmlb/pango 配方
   package_info 引用旧名（无后缀或 -2.0 后缀两套并存）→ 同一 glib 版本无法同时
   满足两个体系 → compose 链与主链 glib 版本矩阵冲突（R03 阻塞根因）。
3. PkgConfigDeps 在生成 .pc 时校验组件 requires 引用的组件键必须存在于依赖
   cpp_info.components → 报 "Component ... not found"。

## 修复（rec_approach）

1. requirements 中 glib/2.84.0.1 用 `force=True` 固化版本（保留 direct
   requirement 语义——override=True 会被 package_info 组件 requires 校验排除，
   见同组 DRAFT ...-r04-conan-override-force-direct）。
2. generate() 中在 `PkgConfigDeps(self).generate()` 之前为 glib 依赖 cpp_info
   注入无后缀别名组件键（gobject → gobject-2.0 对象引用），使旧版组件名可解析。
3. 类级 `generators = "PkgConfigDeps"` 改为手动调用：类级 generators 先于
   generate() 运行，别名注入晚于生成器 → 注入失效（实测 create26）。

## 验证（verification_cmd）

- `conan create archives/a/appstream/1.2.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
  （干净构建，无 lockfile）→ 生成期通过 + test_package 1/1 PASS。

## 边界（boundary）

- 适用：ohpcd 预编译链绑定特定 glib 组件键命名（-2.0 后缀 vs 无后缀）的项目。
- 反例：单一 glib 版本体系（无跨版本组件键差异）的项目无需本方案。

## 查重（七轴摘要）

- exact_duplicate：否；causal_duplicate：否；trigger_overlap：部分
  （DRAFT-pc-chain-invisible-transitive-deps 同为 .pc 解析失败但触发面不同）；
  solution_overlap：部分；combination_novelty：是（组件键版本体系差异 + 依赖
  cpp_info 别名注入 + PkgConfigDeps 手动调用时序）；boundary_novelty：是；
  test_migration_novelty：部分。

## related

- similar_to: [DRAFT-pc-chain-invisible-transitive-deps, DRAFT-conan-shared-pkgconfig-requires-drop]
- caused_by: []
- prerequisite_of: []
- conflicts_with: []
- 完整七轴与决定见 reports/knowledge-candidate-ledger.md 候选 12（R04 段）。