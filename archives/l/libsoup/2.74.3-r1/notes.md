# libsoup 2.74.3-r1 适配笔记（shared-glib 发布形态修复）

## 为什么是独立版本号

`libsoup/2.74.3` 已发布，其产物把 `glib2/2.88.0`（shared=False，仅静态库）
静态链入 `libsoup-2.4.so.1`。cnb.cool 制品仓不允许同一 `name/version` 并存两个
recipe revision（规则 R37），因此 shared-glib 修复版必须以独立版本号发布——
与平台既有惯例一致（`libsoup3/3.6.5-r1..r3`、`glib/2.84.0.1.1`）。

## 根因：双 GObject 类型系统

已发布的 `libsoup/2.74.3` 二进制实测：

```text
DT_NEEDED: ['libxml2.so.16', 'libpsl.so.5', 'libbrotlidec.so.1', 'libc.so']
```

无 `libglib-2.0.so.0` / `libgobject-2.0.so.0`，且 `nm -D` 导出 **4113** 个
`g_*` 定义符号——即 gobject 被静态内嵌进 `libsoup-2.4.so.1`。

当依赖图里同时存在共享 `glib/2.84.0.1.1`（`librest` / `json-glib` 链，
`NEEDED libgobject-2.0.so.0`）时：loader 加载共享 `libgobject-2.0.so.0`
（第一份类型系统），`libsoup-2.4.so.1` 内嵌的静态 gobject 也参与全局符号解析
（第二份类型系统）→ 两份各自执行类型注册 → `g_param_spec_pool_lookup:
assertion 'pool != NULL' failed` → SIGABRT。

实测：librest 0.10.2.1（soup2 变体）在 CI 上 7/10 上游测试因此全崩
（proxy / proxy-continuous / threaded / custom-serialize / oauth2 / flickr /
lastfm），而纯数据用例 xml / params / test-runner 通过。

同类缺陷见已沉淀知识 `DRAFT-E5xx-libsoup-static-gobject-double-copy`
（libsoup3/3.6.5-r1/-r2，修复版 -r3）。

## 修复

`requirements()` 用 `glib/2.84.0.1.1`（`options={"shared": True}`，
`transitive_headers/transitive_libs=True`）替代 `glib2/2.88.0`，使
`libsoup-2.4.so.1` 链接共享 `libgobject-2.0.so.0`，与 rest/json-glib 链共用
同一份共享 glib（单 GObject 副本）。机制与 `libsoup3/3.6.5-r3` 完全一致。

验证方法：`nm -D libsoup-2.4.so.1 | grep -cE " T (g_|_g_value)"`
（旧 2.74.3 = 4113；本版 -r1 应 = 0，且 NEEDED 含 libglib-2.0.so.0）。

## 其余与 2.74.3 配方一致的机制（复用其已被 CI 验证的实现）

- `tc.strip = None`：OHOS loader 校验 `.codesign` 段哈希与 `.so` 内容一致，
  strip 改写内容 → 哈希失配 → dlopen `Permission denied`。
- `package()` 复制 build 目录原始 `libsoup-2.4.so.1.11.2`：meson install 会清理
  `DT_RUNPATH`，改写 `.so` 内容导致同样的 `.codesign` 失配。
- lld/ninja 的 `LD_LIBRARY_PATH` 修复（clang 同目录 llvm/lib + `/system/lib64`）。
- PkgConfigDeps 简化版 .pc 的 prefix 修正 + glib 工具 pin 到 meson `[binaries]`。

## 依赖版本

- glib/2.84.0.1.1（shared——本次关键变更）
- libpsl/0.21.5.1
- libxml2/2.15.3
- sqlite3/3.49.1
- brotli/1.2.0
- libnghttp2/1.70.0

## 用途

供仍依赖 libsoup-2.4 API 的消费者（librest 0.10.2.1 soup2 变体、
libgfbgraph 0.2.5 等）使用。这些消费者链上带共享 glib/2.84，必须与
libsoup-2.4 的 glib 形态一致（共享），否则双 GObject SIGABRT。

## 上游测试

`-Dtests=true` 构建上游测试二进制；`libsoup-2.4` 库本身的上游测试入口由
消费者（librest 等）实跑，本包 test_package 提供 L1 API 冒烟（SoupURI +
SoupMessage + SoupSession 真实创建，验证单 GObject 下 GObject 实例化不崩）。
