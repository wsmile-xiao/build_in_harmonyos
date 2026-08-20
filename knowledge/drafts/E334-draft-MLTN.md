# E334 — Conan apply_conandata_patches 默认 strip=0，pre-CI 校验须镜像该语义而非 -p1

## 错误特征

pre-CI / 本地用系统 `patch -p1` 语义 dry-run git 格式补丁时出现误判，典型日志如下：

```
patch: can't find file to patch
Apply failed
```

MLton 0001/0002/0003 补丁均为 git format-patch 格式（`diff --git a/... b/...`、`--- a/... +++ b/...`）。

## 触发条件

- 使用 Conan 2.x 配方 + `conandata.yml` 注册 git format-patch 风格补丁（a/b 前缀）；
- pre-CI checklist、patch dry-run 校验、评审脚本用系统 `patch -p1` 语义校验；
- 校验语义（-p1 强剥）与 Conan 实际应用语义（strip=0 + patch_ng 自动剥 a/b）不一致时触发。

## 根因分析

Conan 2.x 的 `apply_conandata_patches` 读取 `conandata.yml` 的 patches 条目，经 patch_ng 库应用补丁，默认 strip=0：patch_ng 会自动剥离 git format-patch 风格 diff 头里的 `a/` 与 `b/` 前缀，无需 `-p1` 强剥。

若 pre-CI/本地/评审校验用系统 `patch` 命令按 `-p1` 语义 dry-run，与 Conan 实际应用语义不一致：要么对 `--- a/xxx` 头多剥一层误判目标文件缺失（假失败），要么在 strip 层级上未覆盖真实应用路径（假通过），使 patch 校验结论失真。MLton 0001/0002/0003 补丁均为 git format-patch 格式，应用与校验必须同一语义。

## 解决方案

### 推荐方案

pre-CI/本地校验与 `apply_conandata_patches` 使用同一 patch 语义：以 strip=0 + patch_ng 对 a/b 前缀的自动剥离为准，不用 `-p1` 强剥；最稳妥是直接在干净源码树调用 `apply_conandata_patches` 验证（应用后 diff 确认目标行已改），再对应用结果做 hash 比对，保证校验即应用。

```bash
# 校验脚本在干净源码树执行 apply_conandata_patches 后核对 hash/差异
# 若需 dry-run，按 strip=0 语义（patch_ng 自动剥 a/b 前缀）模拟，
# 禁止 patch -p1 直接 dry-run git 格式补丁
```

### 回退方案

若校验工具强制要求显式 strip 层级，在 `conandata.yml` 每条 patch 显式声明与 strip=0 等价的层级并让校验命令读取同一配置，保证校验与应用同源同语义。

### 禁止做法 ❌

- 禁止 `patch -p1 --dry-run` / `patch -p1` 校验——用 -p1 语义校验 strip=0 的应用，二者不一致导致假失败或假通过，patch 校验与 CI 结论失真：pre-CI 误拦合法补丁，或放行实际无法应用的补丁，评审与 CI 结果失真。
- 禁止改写补丁头去掉 `a/`/`b/`、手工改写 diff 头——为迎合错误校验而改写 diff 头会破坏 git format-patch 的可追溯性与上游一致性，补丁不可复现，向上游提交受阻。

## 验证

```bash
# 干净 source_folder 上跑 apply_conandata_patches(self) 后
diff -r source_folder expected   # 确认目标文件已改
# 或对应用结果做 hash 比对
# 对比 patch --dry-run -p1 与 strip=0 两种校验在同一补丁上的结论差异，
# 确认必须按 strip=0 语义校验
```

MLton 20241230 Round 10 patch 生成期 `apply-conandata-verify` / `conan-apply-verify` 全程按 `apply_conandata_patches` 实际语义核对（APPLY_CONANDATA_PATCHES_PASS / CONAN_PATCH_APPLY_PASS）；0001/0002/0003 均 git format-patch 格式（`--- a/... +++ b/...`），确认 pre-CI 校验须镜像 strip=0 语义而非 -p1。

## 关联条目

- 原则：P014
- 状态：draft
- 正式文档：doc/E334.md
- 相似条目：E216-draft-C113（多源码 base_path 路由）、E258-draft-ENCH01（patch 致 mtime 倒挂）——同属 Conan 补丁管线语义坑
- 事件源：MLton 20241230 Round 10 patch 生成期 apply-conandata-verify / conan-apply-verify 全程按 apply_conandata_patches 实际语义核对（APPLY_CONANDATA_PATCHES_PASS / CONAN_PATCH_APPLY_PASS）；0001/0002/0003 均 git format-patch 格式（--- a/... +++ b/...），确认 pre-CI 校验须镜像 strip=0 语义而非 -p1

---
*draft/E334-draft-MLTN.md · knowledge graph draft · MLTN*
