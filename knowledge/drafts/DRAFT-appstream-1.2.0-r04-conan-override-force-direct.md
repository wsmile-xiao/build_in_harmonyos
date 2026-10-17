# DRAFT-appstream-1.2.0-r04-conan-override-force-direct — conan 2 override=True 的 require 不算 direct requirement，版本固化应改用 force=True

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: blocking (3) | **Category**: conan / version-matrix / package_info / ohos
> **Audience**: 所有需覆盖依赖精确 require 版本（如 libxmlb 精确 require glib/2.88.3）
> 且自身 package_info 组件 requires 引用该包（glib:: 组件）的 Conan 2 项目

## 触发（trigger）

- appstream 1.2.0 R04：为覆盖 libxmlb 精确 require glib/2.88.3（干净构建 G2 无
  lockfile 时版本冲突），把 glib require 从 direct 改为 `override=True` 强制
  2.84.0.1 → 版本冲突消失，但 package_info 校验失败：

```
appstream/1.2.0: package_info(): There are '(cpp_info/components).requires' that
includes package 'glib::', but such package is not a direct requirement of the recipe
```

## 症状（symptom）

- 干净 `conan create`（conan-verify G2 同款命令）在构建成功后 package_info()
  抛 ConanException，配方验证失败（G2 FAIL）。
- 直接 require 版本（无 override）时则报 `Version conflict between glib/2.88.3 and
  glib/2.84.0.1 ... originates from libxmlb`。

## 机制（root cause）

- conan 2 `_validate_required_components`（cpp_info.py）判定 direct dependency：
  `[r.ref.name for r, d in dependencies.items() if r.direct and ... and not r.override]`
  ——`override=True` 的 require 被显式排除在 direct_dependencies 之外，因此
  package_info 组件 requires 引用 `glib::glib-2.0` 等组件时报 "not a direct
  requirement"。
- `force=True` 保留 direct requirement 语义（r.direct 默认 True 且不置 override），
  同时强制图中该包版本（libxmlb 的 glib/2.88.3 被强制为 2.84.0.1）→ 两难消解。

## 修复（rec_approach）

- requirements 中把覆盖版本的写法从 `override=True` 改为 `force=True`：
  `self.requires("glib/2.84.0.1", force=True)`
- 其余 override（pcre2/zlib/libffi）不参与 package_info 组件 requires 引用，
  可继续保留 override=True。

## 验证（verification_cmd）

- `conan create archives/a/appstream/1.2.0 -pr:h=ci/conan/profiles/ohos-aarch64
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` → G2 干净构建 EXIT=0，
  test_package 1/1 PASS；`ohc-run.py conan-verify appstream 1.2.0` 全 PASS。

## 边界（boundary）

- 适用：需要"覆盖依赖精确 require 版本"且自身 package_info 组件 requires 引用
  该包的 Conan 2 项目（版本矩阵场景）。
- 反例：被覆盖包不参与自身 package_info 组件引用时，override=True 即可。

## 查重（七轴摘要）

- exact_duplicate：否；causal_duplicate：否（根因是 conan 2 override/direct 语义）；
  trigger_overlap：否（PkgConfigDeps 生成 vs package_info 校验不同面）；
  solution_overlap：否（force=True 替代 override=True 保留 direct 语义，无既有
  条目）；combination_novelty：是；boundary_novelty：是；test_migration_novelty：部分。

## related

- similar_to: []
- caused_by: [DRAFT-appstream-1.2.0-r04-glib-component-key-version-matrix]
- prerequisite_of: []
- conflicts_with: []
- 完整七轴与决定见 reports/knowledge-candidate-ledger.md 候选 14（R04 段）。