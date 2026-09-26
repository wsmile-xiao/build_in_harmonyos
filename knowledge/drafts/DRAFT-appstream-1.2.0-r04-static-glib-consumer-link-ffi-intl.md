# DRAFT-appstream-1.2.0-r04-static-glib-consumer-link-ffi-intl — 静态 glib（shared=False，pango 链强制）下可执行目标/消费者链接缺 libffi 与 g_libintl_gettext

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: blocking (3) | **Category**: conan / glib / static-linking / pango / ohos
> **Audience**: 所有 pango/gtk 链强制静态 glib（shared=False）且上层含可执行目标或消费者的 Conan 项目

## 触发（trigger）

- appstream 1.2.0 R04：compose 门控使 pango/harfbuzz 链强制 glib shared=False（静态）。
  R03 时 glib 动态（shared=True），符号由 .so 内部解析；R04 静态链下：
  - `tools/appstreamcli` / `compose/worker/asc-mediaworker` 链接缺
    `ffi_type_void / ffi_call / ffi_prep_cif`（libgobject-2.0.a 需要 libffi）
  - test_package 消费者 `undefined symbol: g_libintl_gettext`（libappstream.a → 静态 glib）
- 干净构建（conan-verify G2，无 lockfile、无 conf 注入）必现；带 lockfile/conf 注入
  时被 libxmlb conf 掩蔽。

## 症状（symptom）

```
ld.lld: error: undefined symbol: ffi_type_void
>>> referenced by gclosure.c ... in archive .../libgobject-2.0.a
ld.lld: error: undefined symbol: g_libintl_gettext
>>> referenced by as-category.c.o ... in archive .../libappstream.a
```

## 机制（root cause）

1. R02/R03 的 glib pc-fix 剥离 Requires.private 里的 zlib/libffi/pcre2（那时 glib
   动态，符号由 .so 提供，剥离安全）；R04 静态 glib 下这些符号必须由消费者补。
2. 可执行目标（appstreamcli/asc-mediaworker）依赖链中 PkgConfigDeps 生成的 pc 已
   剥离 libffi → 链接缺符号；test_package 走 appstream.pc 递归同样缺 intl。

## 修复（rec_approach）

- generate() 中对静态 glib 场景补链接参数：
  - 主体配方：`tc.extra_ldflags += ["-L<libffi>/lib", "-lffi"]`（libffi 为
    override 依赖 package_folder 可能 None → 兜底用静态 glib 包内自带
    libffi.a（glib<xxx>/p/lib/libffi.a 实测存在））
  - test_package（消费者配方）：components 补 glib 组件 libs append "intl"
    （g_libintl_gettext 与 gettext-proxy-libintl-header 草稿的链接期延伸）
- 条件：仅在静态 glib 场景补（动态 glib 无需，避免冗余链接）。

## 验证（verification_cmd）

- `conan create archives/a/appstream/1.2.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
  干净构建 → appstreamcli/asc-mediaworker 链接通过 + test_package 1/1 PASS。

## 边界（boundary）

- 适用：pango/gtk 等强制链静态 glib 且上层有可执行目标/public 消费者项目。
- 反例：glib 动态（shared=True）或纯库无可执行目标的项目无需本方案。

## 查重（七轴摘要）

- exact_duplicate：否；causal_duplicate：部分（与 gettext-proxy-libintl-header
  同族：静态 glib 消费者符号）；trigger_overlap：部分（同为 libintl/libffi 面，
  阶段不同——链接期 vs 头映射期）；solution_overlap：部分（都涉 glib 包 lib
  路径；本候选新增"按 shared 选项条件补 -lffi"）；combination_novelty：是（静态
  glib + pc-fix 剥离 + 干净构建无 conf 注入组合）；boundary_novelty：是；
  test_migration_novelty：部分。

## related

- similar_to: [DRAFT-appstream-1.2.0-ohos-gettext-proxy-libintl-header]
- caused_by: []
- prerequisite_of: []
- conflicts_with: []
- 完整七轴与决定见 reports/knowledge-candidate-ledger.md 候选 13（R04 段）。