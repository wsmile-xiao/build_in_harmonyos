# DRAFT-ohos-github-tarball-sources-differ — GitHub 同 tag 三种 tarball 内容与校验和不同

> Contributor: 5C41 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-github-tarball-sources-differ`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E276` | 图谱 | codeload URL 尾部无扩展名 → conan `get()` 误判为 zip → `BadZipFile` | 那是**解压格式误判**（E392/E483 同）；本条是**三种源内容与校验和不同**——即使格式判断正确，选错源仍会 `checksum mismatch` |
| `E392` | 图谱 | `BadZipFile` + raw makefile 配方模式 | 同 E276，格式/解压层 |
| `E483` | 图谱 | `BadZipFile` → `get()` 需显式 `filename=` | 同 E276，格式/解压层 |

**全库查证**：对 `release 资产` / `codeload` / `api.*tarball` / `三种 tarball` /
`不同 sha256.*tarball` 等关键词 grep —— 命中仅限 E276/E392/E483（BadZipFile
解压问题）与 E169（curl 取 tag 归档示例），**无一条讲"三种源内容与校验和不同"**。

## Scope（何时用）

从 GitHub 取源码的 conan 配方，且项目有 release 资产。同 tag 有三种不同归档：

| 源 | URL 形态 | 生成机制 | 内容特征 |
|---|---|---|---|
| **release 资产** | `github.com/<o>/<r>/releases/download/<t>/...tar.gz` | 发布流水线产物（可上传生成文件）| 通常最完整 |
| **codeload git-archive** | `codeload.github.com/<o>/<r>/tar.gz/refs/tags/<t>` | git 树快照 | 不含发布时单独生成/添加的文件；URL 尾部无 `.tar.gz` |
| **api tarball** | `api.github.com/repos/<o>/<r>/tarball/<t>` | git 树快照 | 目录名 `<repo>-<sha>`，字节与 codeload 不同 |

三者对**同一 tag** 的 sha256 各不相同。实测 eudev 3.2.14：

| 源 | 大小 |
|---|---|
| release 资产 | 2,188,254 B |
| codeload git-archive | 2,323,748 B |
| api tarball | 2,323,865 B |

## Symptom

```console
ERROR: cif-tools/2.0.0: Error in source() method
BadZipFile: File is not a zip file        # ← 这是 E276 层（codeload URL 无扩展名）
ERROR: eudev/3.2.14: ... checksum mismatch  # ← 本条层（源选错/hash 不配）
```

两者可叠加：用 codeload URL（触发 E276 的格式误判），或 URL 选对但 sha256
取自另一源（本条）。

## Root Cause

GitHub 三种归档由不同机制生成，内容天然不同。写 conandata 时若 sha256
与实际所选 URL 的产物不一一对应，`get()` 校验即失败；若只按官方 release 页
的"大小"粗判，也可能因偶合相等而误用不完整源。

## Recommended Solution

### 主方案（priority 1）— pick-source-then-hash

1. **确定官方源**：R39 优先 release 资产；无 release 才用 git-archive；
2. **下载实际所选 URL，逐字节算 sha256**，写入 conandata；
3. 与官方声明核对（Release 页资产大小 / manifest `source` 段）；
4. 项目同时记录 codeload/api 的 hash 时，在 manifest 注明三种源差异与各自
   大小，防后人混用。

### 回退方案（priority 2）— cross-verify-manifest

若项目强依赖发布时生成的文件（eudev 的 keyboard-keys、monocypher 的测试
向量），git-archive 内容不全 → 改用 release 资产，并在 manifest 明确记录
"该源不含 X，需构建期生成/下载"。

### 禁止做法

- ❌ 用 release 的 sha256 配 codeload/api 的 URL（或反之）—— 必然 mismatch；
- ❌ 只按大小/md5 判断源一致 —— 应以 sha256 逐字节核对实际所选 URL。

## 实测证据（2026-09-16，eudev 3.2.14）

| 项 | 结果 |
|---|---|
| 三源大小 | release 2,188,254 / codeload 2,323,748 / api 2,323,865 B，均不同 |
| 处置 | manifest `source.sha256` 锁定 **release 资产**（`8da4319102…`），并注明三者不可混用 |
| 相关 | codeload URL 会同时触发 E276 的 BadZipFile（cif-tools 2.0.0 同踩）|

## 测试覆盖边界

本条只处理"**同 tag 多源、内容与校验和不同**"。区分相邻情形：

- codeload URL 无扩展名 → `E276` / `E392` / `E483`（格式误判）；
- 官方 release 内容含生成文件、git-archive 缺 → 回退方案。

## 关联条目

- 相似：`E276` / `E392` / `E483`（BadZipFile 解压层）
- 差异：见上方差异化定位表
