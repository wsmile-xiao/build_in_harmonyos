# DRAFT-viewnior-1.8-glib-force-shared-mime-info-binary-missing

force 提升 glib 版本使 ohpcd 已发布 shared-mime-info 二进制 package_id 失效 → 依赖包源码构建撞 tree-magic 链接缺陷

## 现象

PR #15134（viewnior 1.8）构建 #85597（Worker OpenHarmonyPCDeveloper-CI-018）在 `conan-build-test` 步骤失败，CI 侧分类"未知"，本地归类网络问题，但真实失败链如下：

```
o[step] Pre-download: 提取 conandata.yml source URLs...
o  [fail] [Errno 2] No such file or directory: 'curl'      ← worker 无 curl（良性噪音，非根因）
o[WARN] Failed to pre-download ... will rely on conan's download
o
o======== Computing dependency graph ========
o...
oshared-mime-info/2.5.1: Main binary package '0079104f556b0700637a99e9200f442bcbd6869a' missing
oshared-mime-info/2.5.1: Checking 11 compatible configurations
oshared-mime-info/2.5.1: No compatible configuration found     ← ohpcd 无匹配二进制
o...
o[97/106] Linking target tree-magic
oFAILED: [code=1] tree-magic
old.lld: error: undefined symbol: g_file_new_for_commandline_arg_and_cwd   ← GIO
o>>> referenced by test-tree-magic.c
old.lld: error: undefined symbol: g_object_ref                            ← GObject
o...
oshared-mime-info/2.5.1: ERROR: Package '0079104f...' build failed
oERROR: shared-mime-info/2.5.1: Error in build() method, line 74
o[fail] viewnior/1.8 — conan create failed
```

## 根因

**链条**：viewnior 依赖图同时含 gtk2 链（pin `glib/2.84.0.1`）与 `shared-mime-info/2.5.1`（pin `glib/2.84.0`）→ 配方以 `self.requires("glib/2.84.0.1", force=True, ...)` 收敛 → conan 的 **package_id 含直接依赖版本**，shared-mime-info 的 glib 依赖被 force 到 2.84.0.1 后 package_id 从 ohpcd 已发布的 `2b6465ed`（requires `glib/2.84.0#f67d9941…`）变为 `0079104f` → CI 查 `No compatible configuration found` → **被迫源码构建** → ohpcd 官方 shared-mime-info 配方（`build-tests=true`）在 `build()` 中往根 meson.build 注入：

```python
test_tree_magic = executable('tree-magic', 'src/test-tree-magic.c',
                             dependencies: [dependency('glib-2.0')], install: false)
```

而 `test-tree-magic.c` 实际引用 **GIO（`g_file_*`）与 GObject（`g_object_ref`）** 符号，链接命令只带 `-lglib-2.0`，缺 `gio-2.0`/`gobject-2.0` → `ld.lld undefined symbol` → ninja 失败 → conan create 失败。

**本地通过的假象**：本地 conan 缓存 `e73f7b6a` 配方是 **LOCAL ONLY 修改版**（glib 改 2.84.0.1 + `-Dbuild-tests=false` + 跳过 tree-magic 注入），本地 viewnior 构建复用了它的产物；CI 用 ohpcd 官方配方（glib/2.84.0 + build-tests=true + tree-magic 注入）必然失败。这是"本地过、CI 挂"的典型来源。

## 关键洞察

- viewnior 对 shared-mime-info **无链接需求**：meson.build 只做 `dependency('shared-mime-info', version: '>= 0.20')` 版本探测，且 `generate()` 中 `_synthesize_shared_mime_info_pc` 已合成 `shared-mime-info.pc`（Version 2.5.1，nothing is linked）。
- GTK+2 消费者先例（xsane/ant-phone）**均不 requires shared-mime-info**。

## 修复（rec_approach: drop-pkgconfig-probe-only-requires）

1. 从 viewnior `requirements()` **删除** `self.requires("shared-mime-info/2.5.1")` 一行；
2. 保留 `generate()` 中 `_synthesize_shared_mime_info_pc`（合成 .pc 满足 meson 版本探测）；
3. 依赖图不再包含 shared-mime-info → 不触发其二进制解析/源码构建 → 绕过 tree-magic 链接缺陷。

## 验证

- 本地用 **CI 同款 profile**（`ci/conan/profiles/ohos-aarch64`）跑 `conan create archives/v/viewnior/1.8 --build=missing`，确认依赖图无 shared-mime-info、构建与 test_package 通过；
- 与 CI 构建命令完全一致：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`。

## 教训

- **force 提升共享依赖版本会失效已发布下游二进制的 package_id**（E538 同族），修复前先 `conan list '<pkg>:*' -r ohpcd` 核对已发布二进制的 requires 版本；
- application 对某包仅需 pkg-config 版本探测时，合成 .pc 即可，不要引入 conan requires（避免拖入整棵依赖树与源码构建风险）；
- 本地验证必须与 CI 用同一配方/同一 profile，禁止用本地临时修改版配方（LOCAL ONLY）充当通过证据。
