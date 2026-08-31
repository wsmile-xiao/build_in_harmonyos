# graphene 1.10.8.1 HarmonyOS PC adaptation notes

Issue: 无独立 Issue（HarmonyOS PC 三方库「依赖项」修复提交）
Branch: fix/graphene-1.10.8.1
Target path: archives/g/graphene/1.10.8.1

> **状态：1.10.8.1 已通过鸿蒙设备端 Conan/上游测试与消费者 PkgConfigDeps 验证。**
> 本文只记录已核实的事实；设备验证命令与结果见下文。

## Summary

graphene 1.10.8.1 是 **1.10.8 的适配修复版**，上游 tarball 与 1.10.8 完全一致
（sha256 `a37bb0e78a419dcbeaa9c7027bcff52f5ec2367c25ec859da31dfde2928f279a`，未变）。
`.1` 后缀按 R37/§1.2 用于区分同版本 recipe 修订，不代表上游新版本，因此**上游测试集合
与 1.10.8 相同**（meson + mutest，21 个测试目标）。

本轮不改构建参数、不加补丁，只修 graphene **作为依赖被消费时**的三处缺陷。

## Why 1.10.8 作为依赖项有缺陷

三处均有代码级证据，非推断：

**1. glib 提供方选择污染消费者依赖图**

`archives/g/glib2/2.88.0/conanfile.py:43` 声明 `zlib/1.3.1`，而 cairo/libpng/pango 链走
`zlib/1.3.1.1`（后者才是带 `-fPIC` 的修复版）。结果是**每一个** graphene 消费者都要自己
兜这个冲突：

- `archives/g/gtk4/4.22.4/conanfile.py:96` — `self.requires("zlib/1.3.1.1", override=True)`，
  注释原文："graphene/1.10.8 requires zlib/1.3.1 … forces the whole graph onto zlib/1.3.1.1"
- `archives/a/awf-gtk/4.2.0/conanfile.py:67` — 同样记录 "依赖图中 glib2/2.88.0 声明
  zlib/1.3.1（--static 无 -fPIC 旧版，E005）"

冲突源在 graphene 的依赖选择上，修复应当落在 graphene，而不是每个下游各抄一份。

**2. 缺 gobject component，下游重复手写 .pc overlay**

1.10.8 的 `package_info()` 只声明了根 `cpp_info` 与 `pkg_config_name=graphene-1.0`，
没有 components。graphene 上游另有 `graphene-gobject-1.0` 这个 pkg-config 名，于是
PkgConfigDeps 不产 `graphene-gobject-1.0.pc`，两个下游各自手写：

- `archives/g/gtk4/4.22.4/conanfile.py` 的 `_forward_pc("graphene-1.0",
  "graphene-gobject-1.0", …)`，并硬编码 `graphene_has_sse2=0 / gcc=0 / neon=1 / scalar=1`
- `archives/a/awf-gtk/4.2.0/conanfile.py:574` 起 — 直接从 `dependencies["graphene"]
  .package_folder` 手搓 `graphene-1.0.pc` 与 `graphene-gobject-1.0.pc`，连 include 布局
  `-I${includedir}/graphene-1.0 -I${libdir}/graphene-1.0/include` 都重新编码了一遍

这些本可由 graphene 自己的 `cpp_info` 一次声明、下游零成本获得。

**3. 配方自写转发型 gobject-2.0.pc**

1.10.8 的 `_forward_gobject_pc()` 存在，只是因为 `glib2/2.88.0` 只声明了 `glib-2.0`
一个 pkg-config 名。而 `archives/g/glib/2.84.0.1.1/conanfile.py:239` 已把 `gobject-2.0`
声明为带 `pkg_config_name=gobject-2.0` 的正式 component。换提供方后该 hack 失去存在理由。

## What changed

| 项 | 1.10.8 | 1.10.8.1 |
|----|--------|----------|
| glib 提供方 | `glib2/2.88.0` | `glib/2.84.0.1.1` |
| 其传递 zlib | `zlib/1.3.1`（无 fPIC） | `zlib/1.3.1.1` |
| `gobject-2.0.pc` 来源 | 配方 `_forward_gobject_pc()` 手写 | glib 的 component，PkgConfigDeps 直出 |
| `cpp_info.requires` | `["glib2::glib2"]` | `["glib::gobject-2.0"]` |
| 留证函数 | `_log_glib_pc_version()` 打印 glib-2.0.pc | `_log_pc_version("gobject-2.0.pc")`，缺失即 `ConanException` |

构建参数（`wrap_mode=nodownload`、`introspection=disabled`、`tests=true` 等）、
`_inject_meson_archiver()` 的 OHOS 归档器注入、`test_package` 测试逻辑、补丁列表均未动。

移除自写 .pc 后，`gobject-2.0.pc` 缺失会在 `generate()` 阶段快速失败并指明是依赖侧回归；
否则错误会推迟到 meson 的 `dependency('gobject-2.0')` 才暴露，日志更难定位。

**未改动下游**：按 W2/PF1 单包闸，本 PR 只动 `archives/g/graphene/`。gtk4 与 awf-gtk 仍
pin `graphene/1.10.8`，其 overlay 不受影响；新消费者用 1.10.8.1 即可免掉这些 hack。

## 设备实测记录

以下记录区分旧版产物普查与 1.10.8.1 修复版验证；两者都完成后才可标记 `built` 和创建 PR。

### 1. 已完成：W0 依赖发布检查

   `conan download glib/2.84.0.1.1 -r=ohpcd --only-recipe` 与
   `conan download graphene/1.10.8 -r=ohpcd --only-recipe`。
   两者均返回 0 且命中设备 Conan cache；后者确认 1.10.8 已被制品仓占用，故必须递增版本号。

### 2. 已完成：1.10.8 产物普查与岔路裁决

   2026-08-31 在设备 `upstream/main` 的 `218e4d6300` detached worktree 中运行
   `CI_PACKAGES="archives/g/graphene/1.10.8" /usr/bin/zsh ci/conan/build_and_test.sh`，
   Conan create 与上游 Meson 测试均成功（21/21，Fail=0）；配置摘要为 `GObject types: YES`
   与 `ARM NEON: YES`。

   包路径 `/storage/Users/currentUser/.conan2/p/b/graph132977fdae68d/p` 中只有：
   `lib/libgraphene-1.0.a`，没有 `libgraphene-gobject-1.0.a/.so`；但同时原生安装了
   `lib/pkgconfig/graphene-1.0.pc` 和 `lib/pkgconfig/graphene-gobject-1.0.pc`。
   因此交接文档原先的 A/B 二分需要修正：**没有独立 gobject 库不等于 GObject 类型未构建**。
   `graphene-gobject.c` 已编入唯一的 `libgraphene-1.0.a`，上游 gobject `.pc` 只是通过
   `Requires: graphene-1.0, gobject-2.0` 暴露该接口。

   两个上游 `.pc` 都原生带有 `graphene_has_sse2=0`、`graphene_has_gcc=0`、
   `graphene_has_neon=1`、`graphene_has_scalar=1`；gtk4 的 Meson 消费逻辑确实读取这些变量。
   1.10.8.1 因此采用两个 components 共用一个实际归档：核心 component 持有
   `graphene-1.0`，gobject component 不持有库而 requires 核心与 GLib，并由
   `pkg_config_custom_content` 还原这些已实测变量。

### 3. 已完成：1.10.8.1 真机构建与修复效果验证

   在远端分支 `fix/graphene-1.10.8.1`、配方提交 SHA
   `7fe124ad0a457d15171a7a96c49be0131dcb0756` 的独立 worktree 中运行
   `CI_PACKAGES="archives/g/graphene/1.10.8.1" /usr/bin/zsh ci/conan/build_and_test.sh`：
   Conan create、上游 Meson 测试和 test_package 全部通过；summary 为 1/1 成功，
   Meson `Ok: 21`、`Fail: 0`，无 skipped；配置证据为
   `pkg-config evidence: gobject-2.0.pc Version: 2.84.0.1.1`。
   CMakeDeps 同时声明了 `graphene::graphene` 与 `graphene::graphene-gobject`。

   消费者验证命令为：
   `conan install --requires=graphene/1.10.8.1 -pr:h=ci/conan/profiles/ohos-aarch64
   --build=missing -g PkgConfigDeps`。结果返回 0，Conan graph 只解析
   `zlib/1.3.1.1`，没有 `zlib/1.3.1`；生成目录自动包含
   `graphene-1.0.pc` 与 `graphene-gobject-1.0.pc`。两者均可由 `pkg-config --exists`
   找到、版本为 `1.10.8.1`，并保留 `graphene_has_neon=1`；对 gobject component
   执行 `pkg-config --cflags --libs graphene-gobject-1.0` 可递归得到核心库和 GLib 链接参数。

   随后对包含本验证记录的最新提交 `fb95aa93d4c7c67371ff82e9ec17657e9416c4b9` 在
   `$HOME/ws/graphene-1.10.8.1-latest` detached worktree 中复跑同一命令；结果仍为
   `build_rc=0`、上游 `Ok: 21`、`Fail: 0`，test_package 通过。


## 版本号与任务分支冲突（已用 CI 代码证实）

`ci/conan/build_and_test.sh:754` 的 `EXPECTED_TAG="${pkg_name}-${pkg_ver}"` 中 `pkg_ver`
取自**版本目录名**。故 `archives/g/graphene/1.10.8.1/` 无法通过看板给定的
`feat/graphene-1.10.8` 分支（L0n 判为"完全不包含包名-版本"→ 硬失败）。
本分支按 L0n 提示语的正名取 `fix/graphene-1.10.8.1`（fix=修复）；代价是该 PR
不会自动关联看板「依赖项」任务，需在看板侧单独处理。

## Device validation

`ssh hm` 设备端验证通过。主 worktree 因其他任务存在未提交改动，未被使用；验证使用
`$HOME/ws/graphene-1.10.8.1` 独立分支 worktree。设备端工作区在构建脚本执行后留下
`conandata.yml` 的 `file://` 预下载副作用和 `.build-cache/`，以及原有 `libXext` 伪改动；
这些均未回流到本地提交。

## Test results

`CI_PACKAGES="archives/g/graphene/1.10.8.1" /usr/bin/zsh ci/conan/build_and_test.sh`：
L0/KC/JC 通过，L1 上游测试 + test_package 通过，L2 因无 `bin/` 按规则跳过，L4 无补丁，
L5 `lib/` 有内容，最终 `build_rc=0`。消费者 PkgConfigDeps 与 pkg-config 验证通过。

---
**编译结束**: 2026-08-31 13:39
**最终状态**: built
