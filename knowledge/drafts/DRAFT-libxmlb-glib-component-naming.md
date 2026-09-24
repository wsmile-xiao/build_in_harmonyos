# DRAFT-libxmlb-glib-component-naming：glib/2.88.3 declares conan components named glib/gobject/gio (pkg_config_name maps them to glib-2.0/gio-2.0), so cross-package component requires must be "glib::glib" — "glib::glib-2.0" aborts PkgConfigDeps generation

> Status: **Draft**（待审核 promote）| severity: `2` | category: `conan, gnome, packaging` | Updated: ?
> 对应: `knowledge/drafts/DRAFT-libxmlb-glib-component-naming.kv`

---

## 触发面

- trigger_tool: `conan|PkgConfigDeps|package_info`
- phase: `packaging`

**匹配关键词**：glib, glib-2.0, component, requires, PkgConfigDeps, pkg_config_name, not found, package requirement, gio-2.0, gobject-2.0

## 错误签名（error_signature）

```text
Component 'glib::glib-2.0' not found in 'glib' package requirement|The direct dependency .* is not used by any
```

## 根因（root_cause）

The glib/2.88.3 recipe (archives/g/glib/2.88.3) registers cpp_info.components["glib"|"gobject"|"gio"|...] and maps each to its pkg-config name via set_property("pkg_config_name", "glib-2.0"|"gio-2.0"|...). The earlier glib/2.84.0.1 recipe instead named the components "glib-2.0"/"gobject-2.0"/"gio-2.0" directly. Recipes written against the old naming list requires = ["glib::glib-2.0", ...]; with glib/2.88.3 the PkgConfigDeps generator (or conan's dependency validation) raises "Component 'glib::glib-2.0' not found in 'glib' package requirement" at generate()/package_info() time. Related: every direct requirement must be consumed by some component's requires, otherwise "The direct dependency 'liblzma' is not used by any '(cpp_info/components).requires'".

## 影响范围（affected_scope）

Any recipe requiring the shared glib/2.88.3 package with component-style package_info (GNOME ecosystem: libxmlb, libsoup3-style consumers, gtk-era migrations). Verified instance: libxmlb 0.3.19.

## 推荐方案（rec_approach: `component-name-not-pc-name`）

Reference the conan component NAME, not the pkg-config name: requires = ["glib::glib", "glib::gobject", "glib::gio"]; the pkg_config_name properties on glib's components still emit glib-2.0.pc/gio-2.0.pc for pkg-config consumers. List EVERY direct requirement (flat packages referenced as pkg::pkg, e.g. "liblzma::liblzma", "zstd::zstd") in the component requires or conan fails with "direct dependency not used by any components".

## 修复命令（rec_command）

```text
lib.requires = ["glib::glib", "glib::gobject", "glib::gio", "liblzma::liblzma", "zstd::zstd"]
```

## 兜底方案（fallback_approach: `no-component-flat-cppinfo`）

Drop components entirely and set flat cpp_info.libs with pkg_config_name (json-glib style). Works but loses per- component dependency propagation for CMakeDeps consumers.

## 验证方式（verification_cmd）

```text
conan create archives/l/libxmlb/0.3.19 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 关联

- **相似**：E537

---

*本文件由 `knowledge/drafts/DRAFT-libxmlb-glib-component-naming.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
