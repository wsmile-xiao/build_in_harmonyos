# DRAFT-ohos-conandata-patch-file-present-but-unregistered — 补丁文件放在 patches/ 但未登记进 conandata.yml，等于从未应用

> Contributor: AtomCode/oh-executor | Status: **DRAFT** / Updated: 2026-09-30 / Severity: 2 (medium)
> Source: qatlib 26.02.0 HarmonyOS PC adaptation（PR 分支 `feat/qatlib-26.02.0`）
> 对应：`knowledge/drafts/DRAFT-ohos-conandata-patch-file-present-but-unregistered.kv`

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-8543-refresh-patch-rename-conandata-desync` | 已在 main（draft） | 工具**改名**补丁后 conandata.yml 仍指旧名 → conan 在 `export_sources()` **大声报错**（`Patch file does not exist`），G2/W3 门禁同时失败 | **方向相反**：那条是「登记了但文件没了」→ 报错；本条是「文件在但没登记」→ conan **完全不报错**，失败推迟到构建后期、并以**补丁本来要修的那个问题**的面貌出现。两者的通用自检相同（patches/ 与 conandata.yml 双向比对），但症状与排查路径完全不同 |
| `DRAFT-celero-2.10.0-conandata-patches-export-sources-hook` | 已在 main（draft） | 补丁导出的**钩子选错**（`exports` / `export` / `export_sources` 之争） | 本条假定钩子已正确，问题只在「**没被列出**」 |
| `DRAFT-13619-mklibs-0.1.46-conandata-patch-strip-default-zero` | 已在 main（draft） | 补丁前缀与 strip 层级不匹配 | 与「是否登记」无关 |

**全库查证**：对「补丁文件存在于 patches/ 但未登记 conandata.yml / 未登记即不应用」这一情形，在
`knowledge/graph/`、`knowledge/doc/`、`knowledge/drafts/` 中 grep —— 未命中同名条目。

## Scope（何时用）

配方里带有 `patches/` 目录且用 `apply_conandata_patches` 时，**任何时候**都值得做一次双向核对；
以下场景风险最高：

| 场景 | 为什么危险 |
|---|---|
| 手工新增补丁文件，忘了同步 YAML | 补丁默默失效 |
| 用 `git format-patch` / 补丁刷新工具产出补丁 | 文件生成了，YAML 没跟着改 |
| 把一个补丁拆成多个 | 新拆出的文件容易漏登记 |
| 从别的配方拷补丁过来 | 只拷了文件，没拷 YAML 条目 |

## ⭐ 核心结论：`patches/` 目录里放着文件 **不等于** 补丁会被应用

conan 应用补丁的唯一依据是 **conandata.yml 的 `patches:` 列表**
（`source()` 里的 `apply_conandata_patches(self)` 按该列表查找）：

```yaml
# conandata.yml —— 这里列了才会被应用
patches:
  - patch_file: "patches/01-....patch"
    patch_description: "..."
    patch_type: "portability"
```

**未登记的文件不会被应用，而且 conan 不会给出任何提示**——它没有「需要查找」的对象，自然不会报错。
于是失败被推迟到构建后期，并呈现为**补丁本来要修的那个问题**。

### 实测（qatlib 26.02.0）

磁盘上有 4 个补丁，YAML 只登记了 3 个：

```console
$ ls patches/
01-adf_platform_common-h.patch      02-OsalServices-c.patch
03-qat_mgr-c.patch                  04-add-ax_pthread-m4.patch   ← 未登记
$ grep -c patch_file conandata.yml
3
```

`04-add-ax_pthread-m4.patch` 随源码交付了 autoconf-archive 的 `AX_PTHREAD` 宏，
但因未登记而**从未被应用**，构建最终死在：

```console
configure.ac:29: error: AX_PTHREAD not found. Please install autoconf-archive or place ax_pthread.m4 in m4/
configure.ac:29: the top level
autom4te: error: m4 failed with exit status: 1
```

> ⚠️ 这条报错的措辞（「Please install autoconf-archive or place ax_pthread.m4 in m4/」）
> 有两个误导方向：它暗示①**宿主缺包**、②**m4 目录里没这个宏**。
> 而事实是——宏**已经在配方里**，只是没登记。若照字面去 `apt install autoconf-archive`
> 或去改 configure.ac，都会偏离根因。

**修法**：把补丁登记进 YAML，并给 `autoreconf` 显式加 `-I m4`
（不依赖上游 configure.ac 是否声明 `AC_CONFIG_MACRO_DIR`）：

```yaml
  - patch_file: "patches/04-add-ax_pthread-m4.patch"
    patch_description: "Vendor m4/ax_pthread.m4 (AX_PTHREAD from autoconf-archive): \
                        configure.ac requires it, but autoconf-archive is not present \
                        in the CI build environment"
    patch_type: "portability"
```

```python
r, out = run(["autoreconf", "-fi", "-I", "m4"], timeout=1800)
```

## ★ 双向自检（推荐固化为习惯）

两个方向都要查——只查一个方向会漏掉另一类缺陷：

```sh
PKG=archives/q/qatlib/26.02.0

# 方向一：YAML 里登记的，磁盘上是否真有？（对应 DRAFT-8543 的「登记了但文件没了」）
for f in $(grep -oE 'patches/[^"]+' $PKG/conandata.yml); do
  [ -f "$PKG/$f" ] || echo "登记但缺失: $f"
done

# 方向二：磁盘上的，是否都登记了？（对应本条「文件在但没登记」）
for f in $PKG/patches/*.patch; do
  grep -q "$(basename "$f")" $PKG/conandata.yml || echo "存在但未登记: $f"
done
```

## 反例（禁止）

- ❌ **假设 worker 上装了相应系统包**（如 `autoconf-archive`）来「解决」宏找不到——
  CI worker 是一次性的、不做额外系统安装，本地绿而 CI 红，且会被归因到错误的方向。
- ❌ **只写补丁文件就当作已完成**——未登记的补丁是「死补丁」：占着目录、看得到、
  却不生效，后来者极易被它误导。
- ❌ **删掉 configure.ac 里的宏检查**去绕过（如删 `AX_PTHREAD`）——该宏做的是真实的
  线程编译/链接能力探测，正确做法是让宏**可得**，不是删掉检查。

## 实测记录

| 包 | 现象 | 未登记的文件 | 报错 | 处置 |
|---|---|---|---|---|
| qatlib 26.02.0 | YAML 登记 3 个、磁盘 4 个 | `04-add-ax_pthread-m4.patch` | `configure.ac:29: error: AX_PTHREAD not found...` | 登记该补丁 + `autoreconf -fi -I m4` |

> 补充：该失败的排查链之所以长，是因为上游**sdist 不含 configure**，必须 `autoreconf`
> 自举，而自举期的 m4 宏解析错误与被登记的补丁之间没有直接可见的因果线索。
> 记住判据：**凡是「配方里明明带了补丁/宏，构建却报它不存在」，先查 conandata.yml 登记情况。**
