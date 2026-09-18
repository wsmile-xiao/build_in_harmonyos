# Draft: autotools 源码相对包含头文件需 in-source 构建

- **编号**: DRAFT-irrtoolset-5.1.3-relative-include-in-source（待 promote 分配正式 E 编号）
- **来源库**: irrtoolset 5.1.3（本任务实测验证）；先例配方 adjtimex 1.29、argp-standalone 1.4.1 等 ≥8 个
- **验证门禁**: conan-verify G2 通过（修复前 G2 FAIL, 修复后 G2 PASS）、W3 本地 CI 100% 通过
- **分类**: build-system / autotools / conan / include-path

## 问题

Conan 配方对 autotools 库默认使用 `basic_layout()`（out-of-source 构建，
构建目录为 `build-release/`）。当源码树内部使用**引号相对包含**引用同级/子
目录头文件时，例如 irrtoolset 的：

```cpp
// src/dataset/CacheKey.CacheValue.Map.h
#include "dataset/Pix.h"
```

编译报错：

```
fatal error: 'dataset/Pix.h' file not found
```

## 根因

预处理器对引号包含的查找顺序：当前文件所在目录 → `-I` 路径。
out-of-source 构建时 make 的 `-I` 只有 `$builddir/src`、`$srcdir` 顶层等，
构建树中**没有镜像源码树的 dataset/ 同级目录结构**，于是 `dataset/Pix.h`
在前两级查找均失败。这不同于只通过 `-I<lib>/include` 前缀引用的库
（out-of-source 正常），也不同于自研无 VPATH 的构建系统（audacious 场景，
报 "No targets specified"）。

## 方案

layout() 强制 in-source 构建，保持源码树目录拓扑：

```python
def layout(self):
    basic_layout(self, src_folder=".")
    self.folders.build = "."
```

## 验证

| 阶段 | 布局 | 结果 |
|------|------|------|
| 修复前 | basic_layout() 默认 (out-of-source) | G2 FAIL: `fatal error: 'dataset/Pix.h' file not found` |
| 修复后 | basic_layout(src_folder=".") + folders.build="." | G2 PASS; W3 本地 CI Success 1/1 (100%) |

## 适用边界

- **适用**: 源码树内部使用 `#include "subdir/foo.h"` 相对包含的 autotools /
  VPATH 兼容构建系统库
- **不适用**: 仅 `-I` 前缀引用的库（out-of-source 可行，无需 in-source）；
  自研无 VPATH 构建系统（audacious，见另一草稿）
- **反例**: 若库依赖绝对安装前缀或 CMake `-I` 生成路径，in-source 布局需
  评估对 staging/package 的影响（本库 package() 用 autotools.install() 不受影响）

## 查重

- 正式知识: E434 (vpath-build, copystamp 场景)、E519 (install-data-am
  EXTRA_DIST) — 非本场景
- 草稿: DRAFT-audacious-buildsys-in-source-static-chain（自研 buildsys.mk,
  机制不同）
- 图谱: 无覆盖"相对包含 → in-source 构建"正式条目
- 关系: similar_to DRAFT-audacious-buildsys-in-source-static-chain（同为
  in-source 方案, 触发机制不同）；caused_by 无

## 待 promote

```bash
python3 scripts/ohc-run.py graph promote DRAFT-irrtoolset-5.1.3-relative-include-in-source
```
