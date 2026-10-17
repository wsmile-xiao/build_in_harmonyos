# DRAFT：本地 predl 缓存把 conandata.yml 官方 URL 改写为 file:// 并进入 commit

> Contributor: oh-executor (pc1-38) | Status: Draft | Updated: 2026-09-16
> Source: libnbd 1.9.6 R02 返工（PR #10445 远端 CI conan create source() FileNotFoundError）

## 背景

libnbd 1.9.6 R01 提交的 `conandata.yml` 中，官方 HTTPS 源码 URL 被本地 conan
预下载机制改写为 `file://` 前缀的本机绝对缓存路径（`.build-cache/predl_cache/`），
该污染随 commit/PR 一起交付：

```yaml
sources:
  url:
    - "file:///storage/Users/currentUser/junshi_liu/worktrees/pc1-38-libnbd-1.9.6/.build-cache/predl_cache/40d66413_v1.9.6.tar.gz"
    - "file:///storage/Users/currentUser/junshi_liu/worktrees/pc1-38-libnbd-1.9.6/.build-cache/predl_cache/04d6855f_v1.9.6.tar.gz"
```

远端 CI 构建机不存在该本地路径，`conan create` 在 source() 阶段失败：

```text
libnbd/1.9.6: Error in source() method, line 77
FileNotFoundError: .../.build-cache/predl_cache/04d6855f_v1.9.6.tar.gz
```

该现象命中赛事禁止的 `local_file_url` 标记（prohibited_markers），属当前库
来源/交付契约缺陷，不是外部阻塞。

## 根因

本地 conan 预下载（predl_cache：`.build-cache/predl_cache/`）把 conandata.yml
官方 HTTPS URL 原地改写为 `file://<worktree 绝对路径>/...`（含 `currentUser`、
`.build-cache`、`predl_cache` 关键字），且该改动进入了 commit/PR。

## 方案

1. 恢复 `conandata.yml sources` 为官方 HTTPS tag archive URL：
   `https://github.com/libguestfs/libnbd/archive/refs/tags/v1.9.6.tar.gz`
2. 重新下载官方 tarball，核验 SHA-256 与 conandata.yml 一致
   （`9622385f223cd9a92a0e1d48bded30daebf64a343bd5f7fb79ba61fd91ef7407`）
3. 删除残留：`.build-cache/`（predl_cache）与 `conandata.yml.orig`
4. 复扫确认无 `file://`/`.build-cache`/`predl_cache`/`currentUser`/绝对路径命中

## 验证

- `grep -rn "file://\|.build-cache\|predl_cache\|currentUser" <conandata.yml>` → 无命中
- R02 `conan create`（OHOS aarch64 profile）：EXIT 0，官方 URL 下载并构建成功，
  test_package 2/2 通过（test_libnbd + ohos_spec_test）

## 适用边界

- 适用：所有在本地执行 conan create 预下载后直接 commit/PR 的配方
- 反例：纯本地单机构建（本地有缓存文件）不触发；CI/clean 环境必现；未启用 predl 预下载的流程不触发

## 查重

- E333（PyPI sdist 正则截断 → predl file:// 改写，属远程 CI 场景，`similar_to`）
- E415（CI mirror-fallback 改写 conandata.yml 需恢复，属远程 CI/gh-proxy 场景，`similar_to`）
- 无"本地执行端 predl 改写 + 进入 commit + local_file_url 供交付前扫描"条目 → 部分覆盖，新增差异
- 关系：`similar_to: E333, E415`；无 caused_by/prerequisite_of/conflicts_with 冲突条目