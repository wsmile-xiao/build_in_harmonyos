# DRAFT — libsoup2（libsoup-2.4）静态内嵌 glib2 导致双 GObject

- **来源**: libsoup 2.74.3-r1（GNOME libsoup soup2 API，Meson，OHOS aarch64），2026-10-03
- **触发**: librest 0.10.2.1 soup2 变体（PR 14366），CI 上 7/10 上游测试 SIGABRT
- **同 stem 草稿**: `DRAFT-libsoup-2.74.3-r1-soup2-static-glib-double-gobject.kv`

## 现象

librest 0.10.2.1（libsoup-2.4 后端）在 CI 上，需要实例化 GObject 子类的用例
一启动就 SIGABRT：

```text
not ok /proxy/continuous - GLib-GObject-FATAL-CRITICAL:
g_param_spec_pool_lookup: assertion 'pool != NULL' failed
```

崩的是 proxy / proxy-continuous / threaded / custom-serialize / oauth2 /
flickr / lastfm（7 个，全部会创建 `RestProxy` / `RestProxyCall`）；纯数据用例
xml / params / test-runner 照常通过。链接、编译全过——迷惑点是"看起来像被
适配库自己的 bug"。

## 根因

已发布的 `libsoup/2.74.3` 依赖 `glib2/2.88.0`（该 conan 包默认 `shared=False`，
ohpcd 只发布静态库），把 gobject 静态链入 `libsoup-2.4.so.1`。实测产物：

```text
DT_NEEDED: ['libxml2.so.16', 'libpsl.so.5', 'libbrotlidec.so.1', 'libc.so']
nm -D libsoup-2.4.so.1 | grep -cE " T (g_|_g_value)"  →  4113
```

NEEDED 里**没有** `libglib-2.0.so.0` / `libgobject-2.0.so.0`，却导出 4113 个
`g_*` 定义符号——gobject 被静态内嵌。

librest 自己（及 `json-glib`）链的是**共享** `glib/2.84.0.1.1`
（`NEEDED libgobject-2.0.so.0`）。于是同一进程里：

- loader 加载共享 `libgobject-2.0.so.0`（GObject 类型系统 #1）
- `libsoup-2.4.so.1` 内嵌的静态 gobject 也参与全局符号解析（#2）

两份各自执行类型注册 → 池化类型查找失败 → `g_param_spec_pool_lookup:
assertion 'pool != NULL' failed` → SIGABRT。

同类缺陷见 `DRAFT-E5xx-libsoup-static-gobject-double-copy`
（libsoup3/3.6.5-r1/-r2，用 `cannot register existing type 'gchar'` 表现）
及其修复条目 `DRAFT-libsoup3-r3-glib-shared-recipe-fix`。

## 修复（已用于 libsoup/2.74.3-r1）

配方级（非补丁级），与 `libsoup3/3.6.5-r3` 同法：

1. `requirements()` 由 `glib2/2.88.0` 换为 `glib/2.84.0.1.1`，
   `options={"shared": True}`，`transitive_headers/transitive_libs=True`；
   使 `libsoup-2.4.so.1` 链接共享 `libgobject-2.0.so.0`。
2. `generate()` 用官方 `glib-2.0.pc`（prefix 修正、删 `Requires.private`）覆盖
   PkgConfigDeps 生成的简化版，补回 `-lintl`（否则
   `g_libintl_bindtextdomain` undefined）；glib 工具 pin 到 meson `[binaries]`。
3. `package_info()` 暴露 glib 的 include/libdirs 与
   glib-2.0/gobject-2.0/gio-2.0/gmodule-2.0/gthread-2.0。
4. **独立版本号**：cnb.cool 制品仓不允许同一 `name/version` 并存两个 recipe
   revision（R37），已发布的 `2.74.3` 不能原地改，故重发为 `2.74.3-r1`
   （命名法同平台 `libsoup3/3.6.5-r1..r3`）。

## 验证

```bash
# 修复版：g_* 定义符号数应为 0，且 NEEDED 含 libglib-2.0.so.0 / libgobject-2.0.so.0
nm -D <libsoup-2.74.3-r1-pkg>/lib/libsoup-2.4.so.1 | grep -cE " T (g_|_g_value)"   # → 0
readelf -d <...>/lib/libsoup-2.4.so.1 | grep -E 'libglib-2\.0|libgobject-2\.0'
```

消费侧（librest 0.10.2.1 soup2）改依赖 `libsoup/2.74.3-r1` 后，RestProxy 等
GObject 子类实例化不再 SIGABRT，上游 10/10 用例可实跑。

## 适用边界与反例

- **适用**：任何"共享 glib/2.84 链 + `libsoup-2.4` 消费者"的图（librest soup2
  变体、libgfbgraph 0.2.5 等）。
- **不适用**：全静态图（整链都用静态 glib2）——那种情况下只有一个静态 GObject
  副本，不触发；但要让 json-glib/librest 也用静态 gelib 不可行，故不是可选路径。
- **反向陷阱**：不要把这个 SIGABRT 当作被适配库（librest）自己的测试/代码 bug
  去改；根因在 libsoup2 的发布形态。也不要原地改已发布的 `libsoup/2.74.3`
  （R37 判 FAIL）。

## 查重表（四范围）

| 范围 | 结果 |
|---|---|
| 正式知识 knowledge/graph | 未命中（"libsoup-2.4 / soup2 静态 gobject" 无条目） |
| 图谱 index.tsv | 未命中 |
| 草稿 knowledge/drafts/ | 最近邻 `DRAFT-E5xx-libsoup-static-gobject-double-copy`（同一类，但为 libsoup3 包）、`DRAFT-libsoup3-r3-glib-shared-recipe-fix`（libsoup3 配方级修复）；本条为 **libsoup（soup2/lib-2.4）包** 的具体实例，包名与消费者不同 |
| recipes catalog | `libsoup3/3.6.5-r3` 有同类**修法**但无该**知识条目** |
