# libgexiv2 0.14.6 适配笔记

## 编译环境

- 构建系统：Meson（上游 `meson_version >= 0.56`）+ Ninja；`cpp_std=c++17`
- 目标平台：OpenHarmony / HarmonyOS PC（aarch64，`os=OHOS os.version=6.0`，clang 15.0.4）
- 编译器：`/data/service/hnp/bin/clang` / `clang++`（host 与 target 同架构，非交叉）
- 编译日期：2026-09-21
- 状态：**built**（`conan create` 本地全绿）

## 源码与版本核验

| 项 | 值 | 证据 |
|---|---|---|
| 上游仓库 | https://gitlab.gnome.org/GNOME/gexiv2 | `git ls-remote --tags` |
| tag | `gexiv2-0.14.6` → commit `0da21adecba9b74d5fe7469373d7e360d3f34e3d`（2025-07-06） | 上同 |
| 官方源码包 | `https://download.gnome.org/sources/gexiv2/0.14/gexiv2-0.14.6.tar.xz` | 391436 B |
| SHA256 | `606c28aaae7b1f3ef5c8eabe5e7dffd7c5a1c866d25b7671fb847fe287a72b8b` | 本机 `sha256sum`；与 Debian `gexiv2_0.14.6-2.dsc` 的 `Checksums-Sha256` 完全一致 |
| 语言预检 | `detected=cpp`（主体 C++，C/C++ 同族不迁移） | `ohc-run.py lang-preflight` |

## 编译步骤（真实执行）

```bash
cd <worktree>
conan create archives/l/libgexiv2/0.14.6 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    -r=ohpcd
# EXIT=0
```

配方内实际执行的 Meson 流程（`build()`）：

```
meson setup --native-file <generators>/conan_meson_native.ini <build> <src> --prefix=/
meson compile -C <build> -j20
meson test -v -C <build>              # 上游 C 回归套件
meson install -C <build> --destdir <pkg>
binary-sign-tool sign -selfSign 1     # OHOS：包内 .so 签名（3 个 ELF）
```

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|---------------------|------|----------|
| 1 | `ERROR: Error loading conanfile: Wrong 'tool_requires' definition, did you mean 'build_requirements()'?` | 方法名写错，Conan 2 的工具依赖钩子叫 `build_requirements()` | 把 `def tool_requires()` 改名为 `def build_requirements()`，内部仍用 `self.tool_requires(...)` |
| 2 | `gexiv2/meson.build:36: ERROR: Could not get pkg-config variable and no default provided for <PkgConfigDependency glib-2.0>` | `gnome.mkenums()` 需要 `glib-2.0.pc` 的自定义变量 `glib_mkenums` 来定位 `glib-mkenums`；Conan `PkgConfigDeps` 生成的 `.pc` 只有 `prefix/libdir/includedir*/bindir`（`pkg-config --print-variables glib-2.0` 无该变量），而生成目录排在 `PKG_CONFIG_PATH` 首位，遮蔽了 glib 包自带的同名 `.pc` | 新增 `_augment_glib_pkg_config()`：把 `glib_mkenums` / `glib_genmarshal` 以包内绝对路径补进 generators 目录的 `glib-2.0.pc`（`gupnp-av/0.14.5`、`atk/2.38.0.1.1` 同款） |
| 3 | test_package 运行时报 `Error loading shared library libgexiv2.so.2: (needed by ./test_gexiv2)`，随后全部符号 `symbol not found` | **OHOS 动态加载器拒载未正确签名的共享库**。`meson install` 会让 ninja 重链接以剥离 build rpath，落地后的 `libgexiv2.so.2.14.6` 与构建目录内那份**唯一差异就是 `.codesign`**：构建目录那份可加载，安装那份 `dlopen` 直接 `Permission denied`。用 `binary-sign-tool` 签名后即可加载（对照实验：同一文件换内容即复现/消失；用字节补丁把 RUNPATH 清空同样复现） | `package()` 内新增 `_sign_installed_elfs()`（对所有 `lib/`、`bin/` 下 ELF 执行 `binary-sign-tool sign -selfSign 1`）+ `_create_shared_lib_aliases()`（soname 链接落为真实文件副本）。与 `gdk-pixbuf/2.44.6` 的 OHOS 处理同款 |
| 4 | test_package 二进制执行即 `Signal 5 (core dumped)` / `Error 133` | 测试二进制本身未签名，OHOS 内核 exec 门禁直接抛 SIGTRAP | test_package `build()` 里对构建出的 `test_gexiv2` 同样调用 `binary-sign-tool` 自签名 |
| 5 | 测试运行到 `gexiv2_metadata_free(md)` 处 `Segmentation fault (139)` | **测试自身缺陷**：`gexiv2_metadata_get_mime_type()` 是 `(transfer none)`，返回 `self->priv->mime_type` 内部指针，我误做了 `g_free(mime)` → 堆损坏，延迟到下一次 free 崩溃 | 删除对 `mime` 的 `g_free`，并在测试源码注释标明该 API 的所有权语义（`get_tag_string` 则是 `transfer full`，需 free）。用最小探针二分确认（`new`/`open`/`set` + free 全部正常，只有多出 `g_free(mime)` 才崩） |

> 无源码级补丁（`patches/` 为空）：本库在 OHOS 上无需改动上游源码，全部问题都在
> 配方/测试接线层解决。

## 上游特性裁剪说明（重要）

上游 `meson_options.txt` 默认开启 `introspection=true / vapi=true / python3=true /
tools=true`，而这四个特性都由 `find_program('g-ir-scanner')` 驱动。本环境提供
`g-ir-scanner` 的唯一包是 `gobject-introspection/1.78.1.1`，其强制版本闭包不完整：

```bash
$ conan install --requires=gobject-introspection/1.78.1.1 -r=ohpcd --build=never \
      -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
ERROR: Missing binary: glib/2.84.0.1:be24c1125ebcc1f92ede14d3fdc3b29a1a594315
ERROR: Missing binary: python/3.12.9:188eb7110fccbc046acba807bfd46c0223b4530b
ERROR: Missing prebuilt package for 'glib/2.84.0.1', 'python/3.12.9'.
# EXIT=1

$ conan download "glib/2.84.0.1:be24c1125ebcc1f92ede14d3fdc3b29a1a594315" -r=ohpcd
ERROR: error:not found. [Remote: ohpcd]        # EXIT=1
$ conan download "python/3.12.9:188eb7110fccbc046acba807bfd46c0223b4530b" -r=ohpcd
ERROR: error:not found. [Remote: ohpcd]        # EXIT=1
```

即：`gobject-introspection/1.78.1.1` 自身二进制可下载，但 `force=True` 的
`zlib/1.3.1.1.1.1` + `libffi/3.5.2` 把 `glib/2.84.0.1`、`python/3.12.9` 的
`package_id` 改成了制品仓不存在的组合。按 R36（依赖必须先发布再构建下游）与
任务前置约束，**不使用 `--build=missing`、不使用本地缓存绕过**，因此
`introspection` / `vapi` / `python3` / `tools` 一律关闭——这直接导致上游 2 个
python3 测试入口无法执行（详见 `reports/test-report.md`）。

同仓先例：`gupnp-av/0.14.5`、`gdk-pixbuf/2.44.6` 同样因为构建机没有可用的
`g-ir-scanner` 而关闭 `introspection`。

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|---|---|---|---|
| exiv2 | 0.28.7 | 直接（`dependency('exiv2')`） | ohpcd 唯一版本，满足 `>= 0.26`；已随 main 归档 |
| glib | 2.84.0.1 | 直接（`gobject-2.0` / `gio-2.0`） | 必须 2.84.0.1：与 exiv2 共享 `zlib/1.3.1.1` |
| meson | 1.11.0 | tool_requires | `meson_version >= 0.56` |
| ninja | 1.12.1 | tool_requires | Meson 后端 |
| pkgconf | 3.0.5 | tool_requires | `dependency()` 解析 |
| （传递） | expat/2.8.2.1、zlib/1.3.1.1、pcre2/10.45、libffi/3.4.4、proxy-libintl/0.5、libintl/0.26.1 | | 由 exiv2/glib 的 Conan 依赖链自动拉取 |

## 验证结果

```bash
$ conan create archives/l/libgexiv2/0.14.6 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd
...
1/1 gexiv2:regression OK              0.08s
Ok:                1
Fail:              0
libgexiv2/0.14.6: libgexiv2: signed 3 ELF file(s) for OHOS
======== Testing the package: Executing test ========
gexiv2 consumer test (test_package)
  case 1: version triple            → 2 PASS
  case 2: initialize + metadata     → 8 PASS
  case 3: HarmonyOS dlopen          → 3 PASS
  summary: 13 checks, 0 failed
ALL CHECKS PASSED
# EXIT=0
```

日志：`reports/` 同级见工作区 `.ohc-evidence/logs/06-conan-create.log`。

## 注意事项

- 本包**不提供 GIR/typelib 与 vapi**，也没有 `gexiv2-tool` 命令行工具（因
  introspection/tools 关闭），因此**不需要** `commands.json`（R38 只针对产出可执行
  文件的软件）。
- 消费者若要 `import gi` 式的 Python 绑定，需要先解决
  `gobject-introspection/1.78.1.1` 的二进制发布缺口（见上文），再以
  `introspection=true` 重建本包。
- `libgexiv2.so.2` / `libgexiv2.so` 是**真实文件副本**（非符号链接），与
  `libgexiv2.so.2.14.6` 内容相同；这是 OHOS 侧的既有约定。

## 对话记录

### 对话 #1 [2026-09-21]

- 问题: `conan create` 首次导出配方即失败 —— `Wrong 'tool_requires' definition, did you mean 'build_requirements()'?`
- 操作: 把 `def tool_requires()` 改名为 `def build_requirements()`（内部仍 `self.tool_requires(...)`）
- 结果: 配方可解析，进入 meson configure

### 对话 #2 [2026-09-21]

- 问题: `gexiv2/meson.build:36: ERROR: Could not get pkg-config variable and no default provided for <PkgConfigDependency glib-2.0>`
- 操作: `pkg-config --print-variables glib-2.0` 实证 Conan 生成的 `.pc` 缺 `glib_mkenums`；新增 `_augment_glib_pkg_config()` 按包内绝对路径补回该变量（gupnp-av/atk 同款）
- 结果: meson configure 通过，`gexiv2-enums` 正常生成

### 对话 #3 [2026-09-21]

- 问题: 库本体编译通过、上游 `meson test` 16/16 通过，但 test_package 运行报 `Error loading shared library libgexiv2.so.2: Permission denied`
- 操作: 逐层隔离 —— 构建目录件可 dlopen、install 件不可；`cmp` 显示两者仅 ~230 字节差异（`.dynamic` 的 RUNPATH/签名）；字节补丁清空 RUNPATH 复现 EACCES；`binary-sign-tool -selfSign 1` 后即可加载。据此在 `package()` 增加 `_sign_installed_elfs()` 与 `_create_shared_lib_aliases()`
- 结果: 库可被加载；根因为「OHOS 加载器拒载未签名共享库」，已沉淀为知识草稿 `DRAFT-E5xx-ohos-unsigned-shared-lib-permission-denied`

### 对话 #4 [2026-09-21]

- 问题: 签名后测试二进制执行抛 `Signal 5 (core dumped)` / exit 133；再加打印后定位为 `gexiv2_metadata_free` 处 SIGSEGV
- 操作: test_package 对自编译二进制同样签名；用最小探针二分（`new`/`open`/`set`+free 全正常）定位到测试自身 `g_free(gexiv2_metadata_get_mime_type(...))` —— 该 API 是 `(transfer none)` 返回内部指针，误 free 导致堆损坏
- 结果: 删除误 free 并注明所有权语义，test_package 13 项检查全过

### 对话 #5 [2026-09-21]

- 问题: W3 本地 CI 模拟 JC1/JC5 拦截，但命中文件是 `archives/c/cloog/0.21.1/.build-closed`、`archives/k/kics/2.1.20/.staging-verified` 等**其他软件**在 main 上已提交的遗留文件（junk_check 因未 commit 回退 full 模式整仓扫描）
- 操作: 按 CI 实际口径（prdiff 模式）提供 PR 文件清单；清理本包目录内 test_package 构建残留；还原被预下载逻辑改写的 `conandata.yml`（镜像列表 → 官方源）
- 结果: JC/KC/L0/L1/L4/L5 全 pass，Pass rate 100% (1/1)

### 对话 #6 [2026-09-21]

- 问题: W4 独立审计第 1 轮判 fail（P1/R51）—— `test_package/MANIFEST.yml` 仍是模板骨架（`make check`、`upstream_test_in_build: false`、多处 `<TODO:>`）
- 操作: 按真实证据回填（Meson 口径、3 入口、被阻塞 2 项注明 R36 原因、`assertion_count: 29 = 16 + 13`）
- 结果: 复审 verdict=pass（P0=0 P1=0）

### 对话 #7 [2026-09-21]

- 问题: 包名与官方分支不一致（本地 `gexiv2` vs 官方 `feat/libgexiv2-0.14.6`）
- 操作: 分支改名 `feat/libgexiv2-0.14.6`；归档迁移 `archives/g/gexiv2` → `archives/l/libgexiv2`，`name = "libgexiv2"`（`cpp_info.libs` 仍为真实库名 `gexiv2`、`pkg_config_name` 仍为上游 `gexiv2`，同 `libexif`/`libgcab` 先例）
- 结果: 改名后 `conan create` / `conan-verify` / `finish built` 全部重跑通过；新增知识草稿随本 PR 以【知识库扩展】提交
---

**编译结束**: 2026-09-21 03:09
**最终状态**: built
