# DRAFT-2047：DRAFT-2047

> Status: **Draft**（待审核 promote）| severity: `2` | category: `build-system|patch-pipeline` | Updated: 2026-09-18
> 对应: `knowledge/drafts/DRAFT-2047.kv`

---

## 触发面

- trigger_tool: `conan|patch_ng|apply_conandata_patches`
- phase: `patch-apply`

**匹配关键词**：failed to apply patch,hunk doesn't match,source file is different,conanexception,expected actual,patch context

## 错误签名（error_signature）

```text
ConanException: Failed to apply patch|hunk no\.\d+ doesn't match source file|source file is different|expected: b'.*' actual: b'.*'
```

## 根因（root_cause）

配方（含补丁）从 conan 缓存的 source 目录恢复时，缓存目录里已含历史手工编辑； 补丁是在被预编辑过的源码树（或另一版本源码）上 diff 生成的，hunk 上下文行与官方纯净 tarball 不一致。本地 conan-verify 复用该缓存 source 目录跑 conan create 时补丁"恰好" 能套上（或根本未重新应用），得到假通过；干净环境的 CI 重新解压官方源码后一跑即失败。 典型证据：qtbase 5.15.15 patch 0011 hunk3 期望 `i < 20`，纯净 tst_qthreadpool.cpp:807 实为 `4*QThread::idealThreadCount()`（首循环与次循环写法不同，补丁作者凭记忆写成一样）。

## 影响范围（affected_scope）

所有"从 conan 缓存恢复配方"的场景（工作区丢失/re-clone 后恢复）、 以及任何在手工修改过的源码树上生成补丁的工作流

## 推荐方案（rec_approach: `① 定位失败 hunk 的 expected/actual 差异行，与官方 tarball 中对应文件逐行比对； ② 修正补丁上下文行使其与纯净源码一致（保持补丁语义不变，仅对齐上下文）； ③ 用 patch_ng（conan 同款补丁器）对全新解压的官方 tarball 按序重放全部补丁验证； ④ 重新 conan create 前先 conan cache clean 或删除对应 p/<pkg> 缓存目录，避免缓存污染。`）


## 补充关键词

patch, hunk, doesn't match source file, Failed to apply patch, conan cache, 恢复, qtbase

---

*本文件由 `knowledge/drafts/DRAFT-2047.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
