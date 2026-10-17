# patch 文件 --/+++ 行带本机绝对路径导致 git apply 拒绝（absolute paths are not allowed）

> Draft: DRAFT-PATCH-ABSOLUTE-PATH-GIT-APPLY-REJECTED
> Stem: `DRAFT-patch-absolute-path-git-apply-rejected` — pairs with the same-stem `.kv`
> 来源：cloog 0.21.1（PR #9045）+ dfu 0.11（PR #9176）适配，2026-09-09

## 基本信息

- **ID**: DRAFT-PATCH-ABSOLUTE-PATH-GIT-APPLY-REJECTED
- **严重度**: 3
- **类别**: patch, git-apply, portability, conan-recipe, autotools
- **触发工具**: git|git-apply|patch|conan|diff
- **阶段**: apply_patches|build

## 错误特征

```
patch: error: absolute paths are not allowed - file no.1
stripping absolute path from source name 'b'/storage/Users/currentUser/.tmp/xxx-fresh/...''
stripping absolute path from target name 'b'/storage/Users/currentUser/.tmp/xxx-build/...''
source/target file does not exist:
  --- b'Users/currentUser/.tmp/xxx-fresh/...'
  +++ b'Users/currentUser/.tmp/xxx-build/...'
ConanException: Failed to apply patch: .../patches/0001-xxx.patch
```

## 可复现问题

在 /tmp 下解压新旧两份源码做对比生成 patch（如
`diff -ruN /tmp/xxx-fresh /tmp/xxx-build > patch` 或 vimdiff/脚本产出），
patch 的 `---/+++` 行带着**本机绝对路径**：
```
--- /storage/Users/currentUser/.tmp/xxx-fresh/autoconf/config.guess
+++ /storage/Users/currentUser/.tmp/xxx-build/autoconf/config.guess
```
git apply 拒绝绝对路径（`absolute paths are not allowed`），剥离前缀后
路径变成 `b'Users/currentUser/...`（引号残留 + 截断），apply 必然失败。

cloog 0.21.1（PR #9045）3 个 patch 全部中招，CI 构建直接失败
（`apply_conandata_patches` 抛 ConanException）；dfu 0.11（PR #9176）
同模式生成 patch 有同样风险。

## 根因分析

patch 工具/git apply 对 `---/+++` 行的路径有安全限制：**不接受绝对路径**
（防路径穿越），只接受相对路径（`a/`、`b/` 前缀的 git 标准格式，或
`new/`、`old/` 等）。从 /tmp 绝对路径对比生成 patch 时，diff 默认把
绝对路径写进 `---/+++` 行——这是 diff 的默认行为（不带 `--label` 或
在正确目录结构下运行就会如此），导致 patch 在本机可能能 apply（某些
实现剥离后侥幸匹配），但在 CI/其他机器上（路径不同）必然失败。

关键：**patch 的路径行是 patch 元数据的一部分，必须与仓库相对路径匹配**，
不能用生成它的机器路径。

## 推荐方案

**方法**: git-relative-patch-paths

**说明**: >
  (1) **用 git diff 生成**：在 git 仓库内改完源码后 `git diff` 产出
      `--- a/<rel>` / `+++ b/<rel>` 标准格式（推荐）；
  (2) **用 diff 生成时保证相对路径**：把新旧源码分别放 `a/`、`b/` 子目录后
      `diff -ruN a b`，或在源码根内 `diff -ruN old-dir new-dir` 使路径行
      为相对路径；
  (3) **生成后自检**：`grep -E '^--- |^\+\+\+ ' *.patch`——必须全部是
      `a/<rel>` / `b/<rel>`，出现 `/storage/`、`/tmp/` 等绝对路径即不合格；
  (4) **conan 配方验证**：本地 `conan create` 确认 apply 通过，且 patch
      文件在 CI 上同样可 apply（绝对路径 patch 本地侥幸通过、CI 必失败的
      陷阱——本地验证通过不代表 CI 通过）。

**验证/命令**:
```
grep -E '^--- |^\+\+\+ ' patches/*.patch   # 必须全为 a/ b/ 相对路径
conan create archives/c/cloog/0.21.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 预期：3 个 patch Apply 成功，EXIT=0
```

## 关键词

patch, git apply, absolute paths are not allowed, diff -ruN, ---/+++ 行,
relative path, a/b prefix, conan, apply_conandata_patches, ConanException,
cloog, dfu, OHOS, portability
