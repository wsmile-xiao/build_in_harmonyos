# DRAFT-staticlib-transitive-libs：Rust/meson+cargo-c 静态库传递依赖链接收集

> Contributor: librsvg-2.62.3 适配 | Status: Draft | Updated: 2026-08-14
> Source: archives/l/librsvg/2.62.3（round-2→round-3→round-4 CI，交付 commit 1639c2650d）

## 现象

Rust 项目经 meson+cargo-c 产出的静态库（如 `librsvg-2.a`）在链接期报大量
undefined symbol。第一次失败（round-2）链接命令只含 `-lrsvg-2`，报 glib/cairo
共 20 个 undefined symbol（`g_error_free`、`cairo_create` 等）；补全 glib 系后
（round-3）又报 20 个 `cairo_gobject_*` undefined symbol（`cairo_gobject_surface_get_type`
等），因为：

1. 静态库**不内嵌依赖符号**——消费者必须显式链接全部传递依赖。
2. glib 把库放在 `cpp_info.components[*].libs` 而非顶层 `cpp_info.libs`，只收集
   `cpp_info.libs` 会漏掉 glib 系。
3. cairo/1.18.4 配方显式 `project_options["glib"]="disabled"`（不产
   `libcairo-gobject.so`），但 librsvg 配方 `_forward("cairo-gobject","cairo")`
   生成转发 .pc 别名，使 meson 检出 `Run-time dependency cairo-gobject found:
   YES 1.18.4`（**假阳性**），链接期真实制品缺失才暴露。

## 与现有知识的关系

- knowledge/graph 共 323 条，grep `librsvg` / `cairo-gobject` / `cargo cbuild` /
  `staticlib` 于 knowledge/docs/references 均无结果——本主题无覆盖。
- 既有 E180 仅覆盖 Rust 工具链可用性（本轮 Rust 工具链无新问题，不冲突）。
- 本草稿为"一类问题"（跨库可复用）：任意 meson+cargo-c 静态库 + 依赖图含
  .pc 别名转发的 Conan 适配都可能命中。

## 方案

1. 主配方 `requirements()` 中把被 Rust 绑定引用的 GNOME 族制品显式声明为独立
   Conan 依赖（如 `self.requires("cairo-gobject/1.18.4")`），其 `package_info()`
   设置 `cpp_info.libs = ["cairo-gobject", "cairo"]`。
2. test_package / 消费方 `build()` 遍历所有依赖，收集 `cpp_info.libs` +
   `cpp_info.components[*].libs` + `system_libs`，按"被测库在前、依赖在后、
   系统库最后"构造完整 `-l` 链接命令。
3. 禁止仅依赖 alias .pc 转发来"通过" meson 检测——别名只掩盖制品缺失，
   不提供真实符号。

## 验证证据

librsvg 2.62.3 在 HarmonyOS aarch64 真机单包 CI：

- round-2 FAIL：链接命令仅 `-lrsvg-2`，20 个 glib/cairo undefined symbol
  （`logs/build-round-02.log`）。
- round-3 FAIL：补全传递库后仍 20 个 `cairo_gobject_*` undefined symbol
  （`logs/build-round-03.log`）；根因确认为 cairo-gobject 独立制品缺失 +
  alias .pc 假阳性。
- round-4 PASS：主配方增加 `self.requires("cairo-gobject/1.18.4")` 后，
  test_package 链接命令自动含 `-lcairo-gobject -lcairo`，符号解析成功；
  CI exit 0，1/1 100%，`rsvg_handle_new_from_data: ok`。

## 禁止做法

- 不要在静态库消费方只链接被测包自身 `-l<lib>`——静态库不内嵌依赖符号。
- 不要仅依赖 .pc 别名转发让 meson 检测通过——那会掩盖制品缺失、延迟到链接期暴露。
