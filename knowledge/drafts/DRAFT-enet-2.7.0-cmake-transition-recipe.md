# DRAFT-enet-2.7.0-cmake-transition-recipe：同库跨大版本构建系统迁移时 conan-init 历史模板过期

> Contributor: pc3-4 | Status: Draft | Updated: 2026-09-05
> Source: enet 2.7.0 适配（task enet-2.7.0-r01-pc3-4-20260904T191522Z）

## 背景

enet 1.3.18（autotools）之后，2.7.0 迁移为原生 CMake（CMakeLists.txt：
`project(enet C)`，ENET_STATIC/ENET_SHARED/ENET_TEST 选项）。`ohc-run.py
conan-init enet 2.7.0` 依据同库旧版本归档推断构建系统，生成了
AutotoolsToolchain 配方模板与 `REPLACE_WITH_ACTUAL_SHA256` 占位符，
与新版本实际构建系统不符。

## 现象

```text
ohc-run.py conan-init enet 2.7.0
  -> 构建系统: autotools            # 实际 2.7.0 为 CMake
  -> conanfile.py 使用 AutotoolsToolchain / configure_args
  -> conandata.yml sha256: "REPLACE_WITH_ACTUAL_SHA256"
```

## 根因

conan-init 的构建系统推断依赖同库旧版本归档（1.3.18 autotools），
未感知新版本构建系统迁移；sha256 需人工回填。

## 修复

1. 按新版本实际构建系统（CMake）重写 conanfile.py（参考
   `templates/conanfile-cmake.py.tmpl`）：CMakeToolchain + ENET_STATIC=ON /
   ENET_SHARED=OFF / ENET_TEST=OFF（测试单独构建），package_info libs=["enet"]。
2. conandata.yml 回填官方 tarball 真实 sha256（`sha256sum` 核验）。

```sh
sha256sum enet-2.7.0.tar.gz
# 87aedd04b159e6f7405b1252a79ee7a6b617793347ae95a7eae556ede45e2f64
```

## 验证

- conan-verify G0-G4 + L2/L4/L5 全 PASS（OHOS armv8，clang 15.0.4）
- W3 本地 CI incremental 100% (1/1)
- W4 审计 P0/P1=0
- 上游 7 用例（6 单元 + 1 集成）全过；HarmonyOS 专项回环测试全过

## 适用边界

- 同库大版本升级时构建系统发生迁移（autotools→cmake/meson 等）的配方适配
- conan-init 依据旧版本历史生成模板的所有任务
- 反例：新版本仍用 autotools 时无需重写；重写后必须过 conan-verify/W3

## 查重差异

- E257（header-only 无构建系统 no-op build）：不覆盖"构建系统迁移导致模板过期"
- E321/E322（header-only INTERFACE 配方）：针对持续 header-only 库，不覆盖本场景
- E288（CMake 双库目标收敛）：engine 间接命中（打包产物形态），不覆盖本场景
- 草稿目录无相关条目 → 未命中，新增差异成立