# 上游发行包漏打包被引用的既有头文件：仅非 x86 平台分支命中，arm64 必现 file not found

- **草稿 ID**: DRAFT-11327-upstream-dist-drops-referenced-header-non-x86-path
- **来源**: rnnoise 0.2 HarmonyOS PC（aarch64-linux-ohos）适配（上游 `Makefile.am` 的 `noinst_HEADERS` 漏列 `src/os_support.h`）
- **分类**: autotools / upstream-packaging / platform-branch / header-completeness
- **状态**: 本地草稿（已挂 PR #11327，路径 B 知识库扩展申请中）

## 问题 / 错误签名

- **错误**：`src/vec_neon.h:35:10: fatal error: 'os_support.h' file not found`，随后 `make` 以 `Error 2` 退出（CI build #52162 实测）。
- **平台相关性（关键）**：该头文件只在**非 x86 分支**被引用——
  `src/vec.h` 的 `#if defined(__AVX__) || defined(__SSE2__)` 走 `vec_avx.h`（不引用它）；
  `#elif (defined(__ARM_NEON__) || defined(__ARM_NEON)) && !defined(DISABLE_NEON)` 走 `src/vec_neon.h`（**第 35 行 `#include "os_support.h"`**）；
  最后的 `#else` 通用回退分支同样 `#include "os_support.h"`。
  因此 **x86 上构建全绿、aarch64 必现失败**；如果只在 x86 上跑过上游 CI，上游不会发现。
- **不是"生成文件缺失"**：`os_support.h` 不是构建期生成物，而是**上游 git 里就不存在**的文件——`https://raw.githubusercontent.com/xiph/rnnoise/{v0.2,main}/src/os_support.h` 均 404，codeload 的 tag 快照与 GitHub release dist tarball 里都没有。

## 根因

1. **打包清单漏项**：`Makefile.am` 的 `noinst_HEADERS` 逐条列出随发行包分发的头文件，`os_support.h` 未列入；`make dist` 只收集清单内文件（也收集 `_SOURCES`/`_HEADERS` 列出的项），于是它**既不进 release tarball，也与 `.c` 源无关而不被自动带上**。
2. **引用方按平台分支 include**：引用发生在 `vec.h`/`vec_neon.h` 内部而非顶层，所以"编译通过与否"取决于目标架构走哪条分支——这正是"仅 arm64/OHOS 失败、x86 无事"的成因。
3. **上游自测盲区**：上游发布流水线与用户群以 x86 SSE/AVX 路径为主，NEON/通用分支的 include 缺失不会在上游 CI 暴露。

## 判定方法（可复用扫描）

对源码树做"**引用头文件 vs 实际存在文件**"的完整性扫描，并人工剔除系统头与条件分支：

```bash
# 在解包后的源码根目录执行
python3 - <<'EOF'
import os, re
root="."; present=set()
for dp,_,fn in os.walk(root):
    for f in fn:
        present.add(os.path.relpath(os.path.join(dp,f),root).replace("\\","/"))
        present.add(f)
missing={}
for dp,_,fn in os.walk(root):
    for f in fn:
        if not f.endswith((".c",".h",".am",".in")): continue
        p=os.path.join(dp,f)
        txt=open(p,encoding="utf-8",errors="ignore").read()
        for m in re.finditer(r'#\s*include\s+"([^"]+)"', txt):
            inc=m.group(1)
            if inc not in present and os.path.basename(inc) not in present:
                missing.setdefault(inc,[]).append(os.path.relpath(p,root))
for k,v in sorted(missing.items()):
    print("MISSING:",k,"<-",sorted(set(v))[:5])
EOF
```

- **筛除规则**：系统头（`math.h`/`stdlib.h`/`string.h`）、`config.h`（configure 生成）、`FIXED_POINT`/`FIXED_DEBUG`/x86-asm/mips 等**未启用分支**的 include 全部忽略；只保留**目标分支会命中**的缺失项。
- **判定要点**：`noinst_HEADERS`（或 `EXTRA_DIST`）里是否列了该文件；`git ls-tree` 与 release 资产里是否都不存在；引用点是否在平台分支内。

## 最小修复方案

在配方内以 **header patch** 补回该头文件（本例取自同源同许可证的 Opus `celt/os_support.h`，BSD-3-Clause，与 rnnoise 同属 Xiph）：

```yaml
# conandata.yml
patches:
  - patch_file: "patches/0001-add-missing-os_support-header.patch"
    patch_description: "Add src/os_support.h referenced by src/vec.h/src/vec_neon.h but absent from git and the release tarball (not listed in Makefile.am noinst_HEADERS)"
    patch_type: "portability"
```

补丁内容只提供被引用的符号（本例 `OPUS_COPY`/`OPUS_MOVE`/`OPUS_CLEAR`），并把上游头名 `opus_defines.h` 改为本库已有的 `common.h`（提供 `OPUS_INLINE`）——**不引入新依赖、不改上游行为**。

## 陷阱：跳过 autoreconf 时改 Makefile.am 是无效的

本适配为避免受限 worker 上的自举开销，**不跑 `autoreconf`**（dist tarball 自带 `configure`/`Makefile.in`）。此时：
- `Makefile` 由 `Makefile.in` 生成，而 `Makefile.in` 是发行包内的**预生成物**；
- 只改 `Makefile.am`（例如把 `os_support.h` 补进 `noinst_HEADERS`）**不会被重生成**，对本次构建零效果；
- 因此正确做法是**只补头文件本体**；若确要修正打包清单，须改 `Makefile.in`（或跑 autoreconf），并在 notes 说明。

## 适用范围

- 任何用 Autotools（`make dist`）发布、且**被 include 的头文件未列入 `noinst_HEADERS`/`EXTRA_DIST`** 的库；
- 更一般地：**仅在特定平台/架构分支（NEON/汇编/私有后端）引用的文件**——上游 x86 CI 全绿、移植到 aarch64 才暴雷；
- 不限于 Autotools：CMake 的 `install(FILES ...)` / 分发 tarball 漏带被 include 的私有头也同型。

## 边界 / 反例

- 若缺失的是**构建期生成物**（版本串、模型权重、表、`configure` 本身），处理路径不同（选择含生成物的官方 release 分发物，或按规则重建并校验产物）——本条目不覆盖。
- 若缺失头文件属于**可选特性**（如 `ENABLE_OSCE` 分支的 `osce.h`），应先确认目标构建分支是否真的需要；本例 `osce.h` 在 `#ifdef ENABLE_OSCE` 下，未启用则无需补。

## 实证

| 项目 | 内容 |
| --- | --- |
| 源包 | GitHub release dist tarball `rnnoise-0.2.tar.gz`（sha256 `90fce4b0…`），含 `configure`/`package_version`/`src/rnnoise_data.{c,h}`，**不含** `src/os_support.h` |
| 交叉核对 | `git archive` 快照（codeload v0.2 / v0.1.1）同样无 `os_support.h`；raw.githubusercontent 404（v0.2 与 main） |
| 失败现场 | CI build #52162（PR #11327，OHOS aarch64，clang 15）：`vec_neon.h:35 fatal error` |
| 修复 | `patches/0001-add-missing-os_support-header.patch`（`patch -p1` 本地 dry-run + 实打通过） |
| 修复后 | CI build #52746：L0 结构门禁、L1 测试执行门禁、`conan create` + test_package（5 断言）全部通过 |

## 关联

- PR：#11327（`feat/rnnoise-0.2`）
- 同批草稿：`DRAFT-11327-ohos-cannot-fork-heavy-bootstrap-intermittent`（受限 worker 自举失败的间歇性特征）
- 相邻既有条目（区分点见上）：`x86-simd-sort-aarch64-scalar-dispatch`（x86 运行时分派缺失）、`monocypher-release-vs-tag-archive`（生成文件/版本串）、`gmime-release-tarball-native-run-probe`（免自举）