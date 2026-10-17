# DRAFT-dnswire-0.5.0-official-asset-generated-autotools-no-autoreconf

> Contributor: pc4-25 | Status: Draft | Updated: 2026-09-26
> Source: dnswire 0.5.0 R03 rework
> (task dnswire-0.5.0-r03-pc4-25-20260926T070457Z; R02 交付因远端 CI
> aclocal 缺失返工)
> 对应：knowledge/drafts/DRAFT-dnswire-0.5.0-official-asset-generated-autotools-no-autoreconf.kv

## 现象

R02 交付（conandata 已切官方 release asset、429 已消除）后，远端 CI #61483 在
build() 阶段失败：

```text
RUN: autoreconf --force --install
Can't exec "aclocal": No such file or directory at .../Autom4te/FileUtils.pm line 299.
autoreconf: error: aclocal failed with exit status: 2
```

根因：配方 build() 无条件调用 `autotools.autoreconf()`，依赖 aclocal（automake）。
远端 CI 中 automake/1.18 等 tool_requires 二进制被 Skipped（日志 WARN：
package_type 'application' 与 shared/header_only options 冲突），aclocal 不可用。
而官方 release asset 自带预生成 configure/Makefile.in/aclocal.m4/ltmain.sh，
本无需 autoreconf；本地（pc4-25）因环境有 automake 能过，CI 即失败。

## 根因分析

1. **生成物完整则无需 autoreconf**：官方 release asset（静态 tarball）自带全套
   Autotools 生成物；R01 用 codeberg 动态 archive（git archive 无生成物）时必须
   autoreconf 自举，R02 换官方 asset 后该前提失效，但 build() 仍保留 autoreconf。
2. **生成物修改不能放 conan patches**：configure（protoc-c optional）、
   src/Makefile.in（预生成 pb-c）、顶层 Makefile.in（automake 重建规则）的修改
   若做成 conan 补丁，finish 的 refresh-patch 步骤按 edit-tracker 重排补丁，
   会把不被 tracker 管理的生成物补丁移入 `.patch-backup-*`，导致 conan
   export_sources 报 "Patch file does not exist"（W3/finish 实际复现）。
3. **pkg.m4 陷阱**：即使不跑 autoreconf，source() 若把 pkg.m4 复制进 m4/，
   `am__configure_deps` 中 m4/*.m4 的 mtime 变新，会触发顶层 Makefile.in 的
   `$(srcdir)/Makefile.in: ... $(am__configure_deps)` 重建规则再次调用
   AUTOMAKE/ACLOCAL → 同样失败。官方 configure 已内联 PKG_INSTALLDIR，宏源
   并非必需。
4. **automake maintainer 重建规则**：automake 生成的 Makefile.in 含
   Makefile.in/configure/aclocal.m4 三条重建规则，任何依赖 mtime 变新都会
   shell out 到 AUTOMAKE/ACLOCAL/AUTOCONF。

## 解决方案

1. `build()` 删除 `autotools.autoreconf()`，直接使用自带 configure；
2. 生成物修改改为 build() 内 `_rewrite()`（Python 字符串替换，与 E011 umask
   修复同风格）：
   - configure：protoc-c 缺失时 `PROTOC_C=true` 回退（替换 AC_MSG_ERROR 块）；
   - src/Makefile.in：主源含 `dnstap.pb-c.c`、删除 protoc-c codegen 规则、
     `dnswire/dnstap.pb-c.h` 改由 `$(srcdir)` 复制；
   - 顶层 Makefile.in：三条 automake 重建规则体改为 `@:` 空操作；
   - E011：umask 077→022；
3. source() **不再复制 pkg.m4** 到 m4/（防止 mtime 触发重建规则）；
4. conandata.yml 只保留 edit-tracker 可管理的源码补丁（本库为
   0003/0004/0005 三个 src/test 文件），生成物修改全部内联。

## 验证（R03 实测）

- 干净环境（PATH 仅 /data/service/hnp/bin，无可 automake 干扰）：
  configure rc=0；make rc=0（日志 0 次 automake/aclocal 实际调用）；
- make check 6/6 PASS：`# TOTAL: 6, # PASS: 6, # FAIL: 0`；
- 鸿蒙专项 16/16 PASS；consumer rc=0；
- conan create -tf test_package PASSED；
- conan-verify G0-G4/L2/L4/L5 全过；finish=published；W3 .ci-result.json exit_code=0。

## 适用边界与反例

- **适用**：官方 release asset 自带完整 Autotools 生成物的 C/C++ 库 Conan 适配，
  CI 构建主机无 automake/aclocal 二进制。
- **反例/边界**：
  - git 托管动态 archive（codeberg/github /archive/<tag>.tar.gz，无生成物）场景
    仍需 autoreconf —— 此时应为已知依赖路线（E041/E071 bypass 或 tool_requires
    补齐 automake），不适用本条目；
  - 生成物文件被上游排除（如 dist-hook 删除 pb-c）时，仍需配合预生成文件
    （C2 草稿）处理；
  - 若必须保留生成物补丁（团队偏好），需在 finish 的 refresh-patch 之外单独
    保障补丁文件不被重排（尚无工具支持，本条目即为绕过该限制的推荐形态）。

## 四范围查重（七轴）

- **exact_duplicate**: false — 无条目描述"官方 asset 自带生成物 → 不 run autoreconf + 内联改写生成物"
- **causal_duplicate**: partial — E041/E071/E059 同属"automake/aclocal 环境缺失"
  因果族，但为生成物不完整/版本不匹配场景；本条目为"生成物完整、纯属多余 autoreconf"
- **trigger_overlap**: true — 与 E041/E071 共现 `Can't exec "aclocal"` 触发面
- **solution_overlap**: partial — E041/E071 bypass 用假工具/环境变量；本条目
  "利用自带生成物消除依赖 + 内联改写"，同属绕开 automake 族但机制不同
- **combination_novelty**: true — "官方 asset 自带生成物 + build() 内联改写 +
  不复制 pkg.m4 防 mtime 触发 + 禁用 automake 重建规则"组合无既有条目
- **boundary_novelty**: true — 适用边界（自带完整生成物）与反例（git archive
  无生成物仍须 autoreconf）明确
- **test_migration_novelty**: true — 干净环境（无 automake PATH）验证方式
  可迁移至其他官方 asset 适配任务

- **similar_to**: E041, E071, E059
- **caused_by**: —（上游发布形态）
- **prerequisite_of**: —（暂无后续条目）
- **conflicts_with**: —（无冲突）

## 决策

- knowledge/doc：未命中（E041/E071 为绕过路线、E059 占位符、E089 pkgconfigdir）
- knowledge/graph：未命中
- knowledge/drafts：未命中（DRAFT-10251/DRAFT-6048 不同主题）
- index.tsv：未命中
- **路径决定：B（new_draft）** — R03 build() 修复过程中出现的真实可复用问题，
  已验证（干净环境构建 + 6/6 + 全门禁）、可跨库复用、查重未命中且存在新增差异；
  建同 stem .kv/.md 草稿随 dnswire PR 交付。